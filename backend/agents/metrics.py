"""KPI computation — optimized plan vs naive demand-matching baseline.

Naive baseline
--------------
Without VRP coordination, every farm independently sends its produce to its
nearest demand point (shortest haversine distance).  The market at each demand
point can only absorb ``base_demand_per_day`` kg split equally across the
farms that converge there.  Any farm whose yield exceeds its share of the
market's daily capacity is left unsold — that excess is the *naive waste*.

Optimized baseline
------------------
The VRP plan explicitly routes each farm's produce to a specific demand point.
We apply the same per-farm demand-cap formula using the actual assignments from
the route stops, so farms redistributed to less-saturated markets waste less.

Unrouted (uncovered) at-risk farms are treated as 100 % wasted in the
optimized scenario.

Usage::

    delta = compute_kpi_delta(state)
    # {
    #   "naive_waste_kg": 500.0,
    #   "optimized_waste_kg": 0.0,
    #   "waste_reduction_pct": 100.0,
    #   ...
    # }

Note on expected percentages
-----------------------------
With our clustered Bengaluru scenario (3 tomato farms, 2 APMC demand points),
total supply (~4 500 kg) is well below total demand capacity (~7 300 kg).
All three farms naively converge on the nearer APMC (Yeshwanthpur, 4 200 kg
capacity), causing ~11 % naive market-saturation waste (~500 kg).  The VRP
redistributes one farm to Kolar APMC, eliminating that excess → 100 %
reduction of the saturation waste.

To obtain a 20–30 % waste_reduction_pct (implying meaningful residual waste
even after optimisation), the seed data's per-DP demand figures would need to
be lower than the combined farm supply, e.g. 800–1 200 kg/day per APMC rather
than 3 100–4 200 kg/day.
"""

from __future__ import annotations

import math
from collections import defaultdict

from memory.state import AgentFarmState
from models.schemas import AtRiskStock, DemandPoint, Farm
from models.schemas import WeatherEvent
from tools.scenario_effects import (
    HEAT,
    LIVE,
    MONSOON,
    coerce_weather_events,
    live_stress_kind_from_event,
    market_absorption_factor,
    naive_coordination_penalty,
    normalize_scenario_type,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres (Haversine formula)."""
    r = 6_371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nearest_dp_id(farm: Farm, demand_points: list[DemandPoint]) -> str | None:
    """Return the id of the demand point closest to *farm* (haversine)."""
    if not demand_points:
        return None
    return min(
        demand_points,
        key=lambda dp: _haversine_km(farm.lat, farm.lng, dp.lat, dp.lng),
    ).id


def _naive_farm_to_dp(
    at_risk: list[AtRiskStock],
    farms: list[Farm],
    demand_points: list[DemandPoint],
) -> dict[str, str]:
    """Assign each at-risk farm to its nearest demand point (naive routing)."""
    farm_by_id: dict[str, Farm] = {f.id: f for f in farms}
    mapping: dict[str, str] = {}
    for stock in at_risk:
        farm = farm_by_id.get(stock.farm_id)
        if farm is None:
            continue
        dp_id = _nearest_dp_id(farm, demand_points)
        if dp_id:
            mapping[stock.farm_id] = dp_id
    return mapping


def _routed_farm_to_dp(
    state: AgentFarmState,
    farms: list[Farm],
    demand_points: list[DemandPoint],
) -> dict[str, str]:
    """Extract farm_id → demand_point_id from VRP route plan stops.

    The VRP solver treats farms and demand points as generic customers in one
    tour.  Three edge-cases must be handled gracefully:

    1. A farm stop that has **no DP anywhere in the same route** (truck picks up
       but never visits a market).  Fallback: assign to the nearest DP by
       haversine distance.

    2. A farm stop that appears **after all DPs in the route** (e.g. a collect
       leg on the way back to depot).  The farm is assigned to the last DP seen
       in sequence on that route.

    3. A farm stop that appears **before a DP** in the route.  Assigned to the
       first DP that follows it in sequence (typical pick-and-deliver leg).
    """
    mapping: dict[str, str] = {}
    route_plan = state.get("route_plan")
    if not route_plan:
        return mapping

    farm_by_id: dict[str, Farm] = {f.id: f for f in farms}

    for route in getattr(route_plan, "routes", []):
        stops = sorted(route.stops, key=lambda s: s.sequence)

        # Pre-compute: list of (sequence_index, dp_id) for delivery stops
        dp_seqs: list[tuple[int, str]] = [
            (s.sequence, s.demand_point_id)
            for s in stops
            if s.demand_point_id is not None
        ]

        for stop in stops:
            if stop.demand_point_id is not None or not stop.label:
                continue  # not a farm pickup
            farm_id = stop.label

            # Find the first DP that comes at or after this stop in sequence
            following_dp: str | None = next(
                (dp_id for seq, dp_id in dp_seqs if seq >= stop.sequence),
                None,
            )
            if following_dp is not None:
                mapping[farm_id] = following_dp
                continue

            # No following DP — use last DP seen before this stop in the route
            preceding_dp: str | None = next(
                (dp_id for seq, dp_id in reversed(dp_seqs) if seq < stop.sequence),
                None,
            )
            if preceding_dp is not None:
                mapping[farm_id] = preceding_dp
                continue

            # Route has no DP at all — fall back to nearest DP by haversine
            farm = farm_by_id.get(farm_id)
            if farm is not None and demand_points:
                nearest = _nearest_dp_id(farm, demand_points)
                if nearest:
                    mapping[farm_id] = nearest

    return mapping


def _demand_matching_waste(
    at_risk: list[AtRiskStock],
    farm_to_dp: dict[str, str],
    dp_daily_demand: dict[str, float],
) -> tuple[float, float]:
    """Compute total waste using the demand-cap formula.

    For each demand point that receives produce:
        deliverable_per_farm = dp.base_demand_per_day / N_farms_at_that_dp
        waste_per_farm       = max(farm.kg_at_risk − deliverable_per_farm, 0)

    Returns ``(waste_kg, total_kg)`` so callers can derive percentages.
    """
    # Count farms routed to each DP
    dp_farm_count: dict[str, int] = defaultdict(int)
    for stock in at_risk:
        dp_id = farm_to_dp.get(stock.farm_id)
        if dp_id:
            dp_farm_count[dp_id] += 1

    waste = 0.0
    total = 0.0
    for stock in at_risk:
        total += stock.kg_at_risk
        dp_id = farm_to_dp.get(stock.farm_id)
        if dp_id is None:
            # Unassigned → 100 % waste (no route, no market)
            waste += stock.kg_at_risk
            continue
        n = dp_farm_count[dp_id]
        daily_demand = dp_daily_demand.get(dp_id, 0.0)
        deliverable = min(stock.kg_at_risk, daily_demand / max(n, 1))
        waste += max(stock.kg_at_risk - deliverable, 0.0)

    return waste, total


def _additional_spoilage_waste(
    at_risk: list[AtRiskStock],
    farm_to_dp: dict[str, str],
    scenario_type: str,
    event_by_farm: dict[str, WeatherEvent] | None = None,
) -> float:
    """Extra optimized waste from scenario-driven spoilage on unrouted urgent stock."""
    st = normalize_scenario_type(scenario_type)
    extra = 0.0
    for stock in at_risk:
        if stock.farm_id in farm_to_dp:
            continue
        hours = stock.hours_until_spoilage or 999.0
        stress = st
        if st == LIVE and event_by_farm:
            stress = live_stress_kind_from_event(event_by_farm.get(stock.farm_id))
        if stress == HEAT and hours < 36.0:
            urgency = max(0.0, (36.0 - hours) / 36.0)
            extra += stock.kg_at_risk * urgency * 0.08
        elif stress == MONSOON and hours < 48.0:
            extra += stock.kg_at_risk * 0.05
    return extra


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_kpi_delta(state: AgentFarmState) -> dict[str, float]:
    """Return KPI metrics comparing VRP-optimized plan to naive demand baseline.

    Keys returned
    ~~~~~~~~~~~~~
    naive_waste_kg          kg wasted under naive (nearest-DP) market routing.
    optimized_waste_kg      kg wasted under VRP-optimized routing.
    waste_reduction_pct     Percentage improvement (0-100).
    naive_waste_pct         Naive waste as % of total at-risk produce.
    optimized_waste_pct     Optimized waste as % of total at-risk produce.
    coverage_pct            % of at-risk farms that have at least one VRP route.
    at_risk_count           Total at-risk stock items.
    covered_count           At-risk items whose farm appears in the VRP plan.
    uncovered_urgent_count  Items with <12 h remaining that are NOT in a route.
    route_count             Number of routes in the plan.
    objective_km            Solver objective (total distance km).
    retry_count             Number of validator retries consumed.
    """
    at_risk: list[AtRiskStock] = state.get("at_risk_stock") or []
    farms: list[Farm] = state.get("farms") or []
    demand_points: list[DemandPoint] = state.get("demand_points") or []
    route_plan = state.get("route_plan")
    retry = state.get("retry_count") or 0

    scenario_type = normalize_scenario_type(state.get("scenario_type", ""))
    weather_events = coerce_weather_events(state.get("weather_events") or [])
    w_events = list(weather_events) if weather_events else None
    absorption = market_absorption_factor(scenario_type, events=w_events)
    dp_daily_demand: dict[str, float] = {
        dp.id: dp.base_demand_per_day * absorption for dp in demand_points
    }

    # --- Naive baseline: each farm → nearest demand point ---
    naive_map = _naive_farm_to_dp(at_risk, farms, demand_points)
    naive_waste_kg, total_kg = _demand_matching_waste(at_risk, naive_map, dp_daily_demand)
    naive_waste_kg *= naive_coordination_penalty(
        scenario_type, at_risk_count=len(at_risk), events=w_events,
    )

    # --- Optimised: use actual VRP assignments ---
    opt_map = _routed_farm_to_dp(state, farms, demand_points)
    # Farms absent from VRP routes count as fully wasted (no market reached)
    opt_waste_kg, _ = _demand_matching_waste(at_risk, opt_map, dp_daily_demand)
    event_by_farm = {
        farm.id: event for farm, event in zip(farms, weather_events)
    }
    opt_waste_kg += _additional_spoilage_waste(
        at_risk, opt_map, scenario_type, event_by_farm,
    )

    # --- Route-level stats (coverage, urgency) ---
    visited = set(opt_map.keys())
    covered = [s for s in at_risk if s.farm_id in visited]
    uncovered = [s for s in at_risk if s.farm_id not in visited]

    waste_reduction_pct = 0.0
    if naive_waste_kg > 0:
        waste_reduction_pct = (naive_waste_kg - opt_waste_kg) / naive_waste_kg * 100.0

    coverage_pct = (len(covered) / len(at_risk) * 100.0) if at_risk else 0.0

    urgent_uncovered = sum(
        1 for s in uncovered if (s.hours_until_spoilage or 0.0) < 12.0
    )

    routes = getattr(route_plan, "routes", []) if route_plan else []
    objective = getattr(route_plan, "objective_value", None) if route_plan else None

    naive_waste_pct = (naive_waste_kg / total_kg * 100.0) if total_kg > 0 else 0.0
    opt_waste_pct = (opt_waste_kg / total_kg * 100.0) if total_kg > 0 else 0.0

    return {
        "naive_waste_kg": round(naive_waste_kg, 1),
        "optimized_waste_kg": round(opt_waste_kg, 1),
        "waste_reduction_pct": round(waste_reduction_pct, 2),
        "naive_waste_pct": round(naive_waste_pct, 2),
        "optimized_waste_pct": round(opt_waste_pct, 2),
        "coverage_pct": round(coverage_pct, 2),
        "at_risk_count": float(len(at_risk)),
        "covered_count": float(len(covered)),
        "uncovered_urgent_count": float(urgent_uncovered),
        "route_count": float(len(routes)),
        "objective_km": float(objective or 0.0),
        "retry_count": float(retry),
    }
