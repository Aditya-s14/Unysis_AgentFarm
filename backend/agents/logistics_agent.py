"""Logistics Agent — builds an optimized route plan via OR-Tools CVRP.

Memory tiers used:
  Tier 1 (state): reads farms, demand_points, trucks, at_risk_stock, retry_count;
                  writes route_plan.
  Tier 2 (outcome_store): get_route_history() for travel-time adjustment factor.

No LLM. Pure combinatorial optimization via vrp_solver.solve_vrp().

demand_scale:
  Reduced by 0.15 per retry (1.0 → 0.85 → 0.70) so OR-Tools fits loads within
  real truck capacity.  Passed through state["retry_count"].

Travel-time adjustment:
  Queries outcome_store for road segments present in seed data.  If historical
  delivery_time_actual > predicted on average, the distance matrix is scaled up
  so the solver avoids those routes.  Falls back to factor=1.0 silently.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timezone

from config import get_settings
from memory.outcome_store import get_route_history
from memory.state import AgentFarmState, AgentTrace
from models.schemas import Route, RoutePlan
from tools.maps_api import get_distance_matrix, get_route_geometry
from models.schemas import WeatherEvent
from tools.scenario_effects import (
    HEAT,
    LIVE,
    MONSOON,
    apply_heat_wave_morning_bias,
    apply_live_weather_matrix,
    apply_monsoon_distance_matrix,
    coerce_weather_events,
    normalize_scenario_type,
    scenario_adjustment_details,
)
from tools.vrp_solver import solve_vrp

logger = logging.getLogger(__name__)

# Known road segments from seed data (empty strings are skipped automatically)
_SEED_SEGMENTS = ["NH-48", "NH-4", "NH-7", "NH-9", "SH-17", "SH-35"]
_AVG_SPEED_KMH = 50.0


async def _route_history_factor() -> float:
    """Return mean(actual / predicted) travel time ratio from Tier-2 outcomes.

    If ratio > 1.0, roads are historically slower than predicted — scale the
    distance matrix up to nudge the solver toward shorter routes.
    Gracefully returns 1.0 when DB is unavailable or no history exists.
    """
    outcomes = []
    for seg in _SEED_SEGMENTS:
        try:
            rows = await get_route_history(seg)
            outcomes.extend(rows)
        except Exception as exc:  # noqa: BLE001
            logger.debug("route history unavailable for segment %s: %s", seg, exc)

    ratios = [
        o.delivery_time_actual_hours / o.delivery_time_predicted_hours
        for o in outcomes
        if o.delivery_time_predicted_hours and o.delivery_time_predicted_hours > 0
    ]
    if not ratios:
        return 1.0
    factor = sum(ratios) / len(ratios)
    logger.info("route_history_factor=%.3f from %d outcomes", factor, len(ratios))
    return factor


def _straight_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    lat1, lon1 = math.radians(a_lat), math.radians(a_lng)
    lat2, lon2 = math.radians(b_lat), math.radians(b_lng)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def _cluster_farms(farms: list, max_diameter_km: float) -> list[list]:
    """Greedy single-link clustering bounded by max_diameter_km.

    Farms are processed in (lat, lng) order; each farm joins the first
    existing cluster where ALL members are within ``max_diameter_km``
    straight-line, otherwise starts a new cluster. Caps cluster diameter
    so VRP routes within a cluster stay day-trip feasible.
    """
    clusters: list[list] = []
    for f in sorted(farms, key=lambda x: (x.lat, x.lng)):
        joined = False
        for c in clusters:
            if all(_straight_km(f.lat, f.lng, m.lat, m.lng) <= max_diameter_km for m in c):
                c.append(f)
                joined = True
                break
        if not joined:
            clusters.append([f])
    return clusters


def _allocate_trucks_by_demand(
    regions: list[tuple[list, list]],
    trucks: list,
    at_risk_stock: list,
) -> list[list]:
    """Assign trucks to regions matching capacity to at-risk demand.

    Highest-demand region gets the largest truck first; pulls additional
    trucks until cluster demand is covered or pool is exhausted. Every
    region gets at least one truck (smallest available) so it can be
    planned even if it has low at-risk stock.
    """
    region_demands: list[tuple[int, float]] = []
    for i, (region_farms, _) in enumerate(regions):
        farm_ids = {f.id for f in region_farms}
        demand = sum(s.kg_at_risk for s in at_risk_stock if s.farm_id in farm_ids)
        region_demands.append((i, demand))

    truck_pool = sorted(trucks, key=lambda t: -t.capacity_kg)
    allocations: list[list] = [[] for _ in regions]

    for region_idx, demand in sorted(region_demands, key=lambda x: -x[1]):
        if not truck_pool:
            break
        allocations[region_idx].append(truck_pool.pop(0))
        while truck_pool and sum(t.capacity_kg for t in allocations[region_idx]) < demand:
            allocations[region_idx].append(truck_pool.pop(0))

    for i in range(len(regions)):
        if allocations[i]:
            continue
        if truck_pool:
            allocations[i].append(truck_pool.pop(0))
        else:
            donor = next((a for a in allocations if a), None)
            if donor:
                allocations[i] = [donor[0]]

    return allocations


def _merge_clusters_to_cap(clusters: list[list], max_clusters: int) -> list[list]:
    """Iteratively merge the two centroid-closest clusters until count <= max_clusters.

    Used when initial clustering yields more groups than available trucks, since
    each truck must own a region exclusively to avoid double-booking conflicts.
    """
    while len(clusters) > max_clusters:
        centroids = [
            (sum(f.lat for f in c) / len(c), sum(f.lng for f in c) / len(c))
            for c in clusters
        ]
        best_i, best_j, best_d = 0, 1, float("inf")
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                d = _straight_km(*centroids[i], *centroids[j])
                if d < best_d:
                    best_i, best_j, best_d = i, j, d
        clusters[best_i].extend(clusters[best_j])
        clusters.pop(best_j)
    return clusters


def _geo_regions(
    farms: list,
    demand_points: list,
    num_trucks: int = 0,
) -> list[tuple[list, list]]:
    """Split wide-area fixtures into local clusters so VRP stays day-trip feasible.

    Uses diameter-bounded clustering rather than hardcoded latitude bands —
    each cluster is constrained so any two farms in it are within
    ``max_farm_mandi_km`` straight-line. Mandis assigned to a cluster must
    also be within that radius of at least one farm in the cluster.

    Mirrors how India's APMC system works in practice at the farmer layer:
    produce moves to the nearest regional mandi (~tens of km), with
    cross-state movement happening at the wholesaler tier later.
    """
    max_km = get_settings().max_farm_mandi_km

    if len(farms) <= 6:
        reachable = [
            d for d in demand_points
            if any(_straight_km(f.lat, f.lng, d.lat, d.lng) <= max_km for f in farms)
        ]
        return [(farms, reachable or demand_points)]

    clusters = _cluster_farms(farms, max_diameter_km=max_km)
    if num_trucks > 0 and len(clusters) > num_trucks:
        logger.info(
            "_geo_regions: %d clusters > %d trucks; merging nearest pairs to fit",
            len(clusters), num_trucks,
        )
        clusters = _merge_clusters_to_cap(clusters, num_trucks)

    regions: list[tuple[list, list]] = []
    for cluster in clusters:
        reachable = [
            d for d in demand_points
            if any(_straight_km(f.lat, f.lng, d.lat, d.lng) <= max_km for f in cluster)
        ]
        if not reachable:
            logger.info(
                "_geo_regions: cluster of %d farms has no mandi within %.0f km",
                len(cluster), max_km,
            )
            continue
        cen_lat = sum(f.lat for f in cluster) / len(cluster)
        cen_lng = sum(f.lng for f in cluster) / len(cluster)
        nearest_dps = sorted(
            reachable,
            key=lambda d: (d.lat - cen_lat) ** 2 + (d.lng - cen_lng) ** 2,
        )
        cap = max(2, min(len(nearest_dps), len(nearest_dps) // 2 + 1))
        regions.append((cluster, nearest_dps[:cap]))

    return regions or [(farms, demand_points)]


_BLOCK_MATCH_EPS = 1e-4  # ~11 m — stop coords round-trip JSON exactly, this is slack
_DEFAULT_BLOCK_PENALTY = 5.0


def _apply_blocked_segments(
    matrix: list[list[float]],
    coords: list[tuple[float, float]],
    blocked_segments: list[dict],
) -> int:
    """Inflate matrix cells for reported-blocked legs (R4). Returns cells hit.

    A segment matches a (from, to) coordinate pair within _BLOCK_MATCH_EPS;
    both directions are penalized so the solver routes around the leg
    rather than reversing it.
    """

    def _near(p: tuple[float, float], q) -> bool:
        return abs(p[0] - float(q[0])) <= _BLOCK_MATCH_EPS and abs(p[1] - float(q[1])) <= _BLOCK_MATCH_EPS

    hits = 0
    for seg in blocked_segments:
        frm, to = seg.get("from"), seg.get("to")
        if not frm or not to:
            continue
        penalty = float(seg.get("penalty") or _DEFAULT_BLOCK_PENALTY)
        from_idx = [i for i, c in enumerate(coords) if _near(c, frm)]
        to_idx = [j for j, c in enumerate(coords) if _near(c, to)]
        for i in from_idx:
            for j in to_idx:
                if i == j:
                    continue
                matrix[i][j] *= penalty
                matrix[j][i] *= penalty
                hits += 2
    return hits


async def _solve_region(
    region_farms: list,
    region_dps: list,
    trucks: list,
    at_risk_stock: list,
    demand_scale: float,
    time_factor: float,
    scenario_type: str,
    event_by_farm: dict[str, WeatherEvent] | None = None,
    blocked_segments: list[dict] | None = None,
) -> RoutePlan:
    dep_lat = sum(f.lat for f in region_farms) / len(region_farms)
    dep_lng = sum(f.lng for f in region_farms) / len(region_farms)
    coords = (
        [(dep_lat, dep_lng)]
        + [(f.lat, f.lng) for f in region_farms]
        + [(d.lat, d.lng) for d in region_dps]
    )
    matrix = await get_distance_matrix(coords, coords)
    if abs(time_factor - 1.0) > 0.01:
        matrix = [[cell * time_factor for cell in row] for row in matrix]

    if blocked_segments:
        hit = _apply_blocked_segments(matrix, coords, blocked_segments)
        if hit:
            logger.info(
                "logistics_agent: penalized %d matrix cells for %d blocked segment(s)",
                hit, len(blocked_segments),
            )

    st = normalize_scenario_type(scenario_type)
    if st == LIVE and event_by_farm:
        region_events = [
            event_by_farm[f.id] for f in region_farms if f.id in event_by_farm
        ]
        if region_events:
            matrix = apply_live_weather_matrix(matrix, region_farms, region_events)
    elif st == MONSOON:
        matrix = apply_monsoon_distance_matrix(matrix, region_farms)
    elif st == HEAT:
        risk_hours = {
            s.farm_id: s.hours_until_spoilage or 120.0 for s in at_risk_stock
        }
        matrix = apply_heat_wave_morning_bias(matrix, region_farms, risk_hours)

    return await asyncio.to_thread(
        solve_vrp,
        region_farms,
        region_dps,
        trucks,
        at_risk_stock,
        matrix,
        demand_scale=demand_scale,
    )


async def _attach_geometry(routes: list[Route]) -> None:
    """Fill route.geometry with the road-snapped polyline (T7).

    One directions call per non-empty route, run concurrently. Any failure
    leaves geometry=None so the map falls back to straight stop-to-stop
    lines — geometry is presentation, never a reason to fail a plan.
    """

    async def _one(route: Route) -> None:
        if len(route.stops) < 2:
            return
        points = [(s.lat, s.lng) for s in route.stops]
        try:
            route.geometry = await get_route_geometry(points)
        except Exception as exc:  # noqa: BLE001
            logger.debug("route geometry unavailable for %s: %s", route.truck_id, exc)

    await asyncio.gather(*(_one(r) for r in routes))


async def run(state: AgentFarmState) -> AgentFarmState:
    """Build a RoutePlan for the current state using OR-Tools CVRP."""
    t0 = datetime.now(timezone.utc)

    farms = state.get("farms") or []
    demand_points = state.get("demand_points") or []
    trucks = state.get("trucks") or []
    at_risk_stock = state.get("at_risk_stock") or []
    retry_count = state.get("retry_count") or 0
    raw_scenario = state.get("scenario_type_raw") or state.get("scenario_type", "")
    scenario_type = normalize_scenario_type(raw_scenario)
    state["scenario_type"] = scenario_type

    # Shrink per-stop demand on retry so plans pass real capacity checks.
    demand_scale = round(max(0.65, 1.0 - retry_count * 0.15), 2)

    if not farms or not demand_points or not trucks:
        logger.warning(
            "logistics_agent: insufficient inputs (farms=%d dp=%d trucks=%d); returning empty plan",
            len(farms), len(demand_points), len(trucks),
        )
        state["route_plan"] = RoutePlan(routes=[], notes="skipped: missing inputs")
        _append_trace(
            state,
            t0,
            routes=0,
            total_stops=0,
            objective="none",
            time_factor=1.0,
            relaxation_factor=demand_scale,
            retry_count=retry_count,
        )
        return state

    time_factor = await _route_history_factor()
    weather_events = coerce_weather_events(state.get("weather_events") or [])
    event_by_farm: dict[str, WeatherEvent] = {
        farm.id: event for farm, event in zip(farms, weather_events)
    }
    blocked_segments = state.get("blocked_segments") or []
    regions = _geo_regions(farms, demand_points, num_trucks=len(trucks))
    truck_allocations = _allocate_trucks_by_demand(regions, trucks, at_risk_stock)

    fallback_last = trucks[-1:]
    tasks = []
    for (region_farms, region_dps), regional_trucks in zip(regions, truck_allocations):
        rts = regional_trucks if regional_trucks else fallback_last
        tasks.append(
            _solve_region(
                region_farms, region_dps, rts, at_risk_stock,
                demand_scale, time_factor, scenario_type, event_by_farm,
                blocked_segments=blocked_segments,
            )
        )
    region_plans = await asyncio.gather(*tasks)

    merged_routes: list[Route] = []
    objective_total = 0.0
    notes_parts: list[str] = []
    for (region_farms, region_dps), region_plan in zip(regions, region_plans):
        merged_routes.extend(region_plan.routes)
        if region_plan.objective_value:
            objective_total += region_plan.objective_value
        notes_parts.append(f"{len(region_farms)}f/{len(region_dps)}dp→{len(region_plan.routes)}r")

    await _attach_geometry(merged_routes)

    plan = RoutePlan(
        routes=merged_routes,
        objective_value=round(objective_total, 3) if objective_total else None,
        notes=f"multi_region ({', '.join(notes_parts)})",
    )
    state["route_plan"] = plan

    route_count = len(plan.routes)
    stop_count = sum(len(r.stops) for r in plan.routes)
    objective = plan.objective_value if plan.objective_value is not None else "none"
    _append_trace(
        state,
        t0,
        routes=route_count,
        total_stops=stop_count,
        objective=objective,
        time_factor=round(time_factor, 3),
        relaxation_factor=demand_scale,
        retry_count=retry_count,
    )

    logger.info(
        "logistics_agent: routes=%d stops=%d objective=%s retry=%d demand_scale=%.2f regions=%d",
        route_count, stop_count, plan.objective_value, retry_count, demand_scale, len(regions),
    )
    return state


_LOGISTICS_TOOLS = [
    "build_distance_matrix",
    "solve_vrp_with_ortools",
    "assign_trucks_to_routes",
]


def _last_validator_trace(traces: list[AgentTrace]) -> AgentTrace | None:
    for tr in reversed(traces):
        if tr.get("agent_name") == "validator":
            return tr
    return None


def _append_trace(
    state: AgentFarmState,
    t0: datetime,
    *,
    routes: int,
    total_stops: int,
    objective: float | str,
    time_factor: float,
    relaxation_factor: float,
    retry_count: int,
) -> None:
    prior = state.get("agent_traces") or []
    prev_validator = _last_validator_trace(prior)
    is_retry_run = retry_count > 0
    attempt_number = retry_count + 1

    prev_failure: dict | None = None
    if is_retry_run and prev_validator:
        vd = prev_validator.get("details") or {}
        prev_failure = {
            "retry_count": vd.get("retry_count", retry_count),
            "reason_for_retry": vd.get("reason_for_retry") or [],
            "relaxation_factor_applied": vd.get("relaxation_factor_applied"),
            "demand_scale_next": vd.get("demand_scale_next"),
            "validator_notes": prev_validator.get("notes", ""),
        }

    note_parts = [
        f"routes={routes}",
        f"stops={total_stops}",
        f"objective={objective}",
        f"time_factor={time_factor}",
        f"demand_scale={relaxation_factor}",
        f"attempt={attempt_number}",
    ]
    if is_retry_run:
        note_parts.append(f"retry_after_validation_fail retry_count={retry_count}")

    trace: AgentTrace = {
        "agent_name": "logistics_agent",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": list(_LOGISTICS_TOOLS),
        "execution_type": "deterministic OR-Tools VRP",
        "notes": " ".join(note_parts),
        "token_count": 0,
        "details": {
            "is_retry_run": is_retry_run,
            "retry_count": retry_count,
            "attempt_number": attempt_number,
            "demand_scale": relaxation_factor,
            "previous_validator_failure": prev_failure,
            "scenario_adjustments": scenario_adjustment_details(
                scenario_type=state.get("scenario_type_raw")
                or state.get("scenario_type", ""),
                retry_count=retry_count,
                demand_scale=relaxation_factor,
            ),
        },
    }
    state["agent_traces"] = [*prior, trace]
