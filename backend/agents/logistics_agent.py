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

import logging
from datetime import datetime, timezone

from memory.outcome_store import get_route_history
from memory.state import AgentFarmState, AgentTrace
from models.schemas import Route, RoutePlan
from tools.maps_api import get_distance_matrix
from tools.scenario_effects import (
    HEAT,
    MONSOON,
    apply_heat_wave_morning_bias,
    apply_monsoon_distance_matrix,
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


def _geo_regions(
    farms: list,
    demand_points: list,
) -> list[tuple[list, list]]:
    """Split wide-area fixtures into local clusters so VRP stays day-trip feasible."""
    if len(farms) <= 6:
        return [(farms, demand_points)]

    bands = ((12.0, 14.5), (14.5, 16.5), (16.5, 22.0))
    regions: list[tuple[list, list]] = []
    for lo, hi in bands:
        region_farms = [f for f in farms if lo <= f.lat < hi]
        if not region_farms:
            continue
        cen_lat = sum(f.lat for f in region_farms) / len(region_farms)
        cen_lng = sum(f.lng for f in region_farms) / len(region_farms)
        nearest_dps = sorted(
            demand_points,
            key=lambda d: (d.lat - cen_lat) ** 2 + (d.lng - cen_lng) ** 2,
        )
        cap = max(2, min(len(demand_points), len(demand_points) // 2 + 1))
        regions.append((region_farms, nearest_dps[:cap]))

    return regions or [(farms, demand_points)]


async def _solve_region(
    region_farms: list,
    region_dps: list,
    trucks: list,
    at_risk_stock: list,
    demand_scale: float,
    time_factor: float,
    scenario_type: str,
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

    st = normalize_scenario_type(scenario_type)
    if st == MONSOON:
        matrix = apply_monsoon_distance_matrix(matrix, region_farms)
    elif st == HEAT:
        risk_hours = {
            s.farm_id: s.hours_until_spoilage or 120.0 for s in at_risk_stock
        }
        matrix = apply_heat_wave_morning_bias(matrix, region_farms, risk_hours)

    return solve_vrp(
        region_farms,
        region_dps,
        trucks,
        at_risk_stock,
        matrix,
        demand_scale=demand_scale,
    )


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
    regions = _geo_regions(farms, demand_points)
    farm_counts = [len(rf) for rf, _ in regions]
    total_farms = sum(farm_counts) or 1

    merged_routes: list[Route] = []
    objective_total = 0.0
    truck_offset = 0
    notes_parts: list[str] = []

    for region_farms, region_dps in regions:
        share = max(1, round(len(trucks) * len(region_farms) / total_farms))
        regional_trucks = trucks[truck_offset : truck_offset + share]
        truck_offset += share
        if not regional_trucks:
            regional_trucks = trucks[-1:]

        region_plan = await _solve_region(
            region_farms,
            region_dps,
            regional_trucks,
            at_risk_stock,
            demand_scale,
            time_factor,
            scenario_type,
        )
        merged_routes.extend(region_plan.routes)
        if region_plan.objective_value:
            objective_total += region_plan.objective_value
        notes_parts.append(f"{len(region_farms)}f/{len(region_dps)}dp→{len(region_plan.routes)}r")

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
