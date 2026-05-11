"""Logistics Agent — builds an optimized route plan via OR-Tools CVRP.

Memory tiers used:
  Tier 1 (state): reads farms, demand_points, trucks, at_risk_stock, retry_count;
                  writes route_plan.
  Tier 2 (outcome_store): get_route_history() for travel-time adjustment factor.

No LLM. Pure combinatorial optimization via vrp_solver.solve_vrp().

relaxation_factor:
  Increased by 0.25 per retry so OR-Tools can find a feasible solution when
  strict capacities are infeasible.  Passed through state["retry_count"].

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
from models.schemas import RoutePlan
from tools.maps_api import get_distance_matrix
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


async def run(state: AgentFarmState) -> AgentFarmState:
    """Build a RoutePlan for the current state using OR-Tools CVRP."""
    t0 = datetime.now(timezone.utc)

    farms = state.get("farms") or []
    demand_points = state.get("demand_points") or []
    trucks = state.get("trucks") or []
    at_risk_stock = state.get("at_risk_stock") or []
    retry_count = state.get("retry_count") or 0

    # relaxation_factor grows with retries: 1.0, 1.25, 1.5
    relaxation_factor = round(1.0 + retry_count * 0.25, 2)

    if not farms or not demand_points or not trucks:
        logger.warning(
            "logistics_agent: insufficient inputs (farms=%d dp=%d trucks=%d); returning empty plan",
            len(farms), len(demand_points), len(trucks),
        )
        state["route_plan"] = RoutePlan(routes=[], notes="skipped: missing inputs")
        _append(state, t0, [], relaxation_factor, retry_count, 0, "skipped: missing inputs")
        return state

    # Depot = centroid of farms
    dep_lat = sum(f.lat for f in farms) / len(farms)
    dep_lng = sum(f.lng for f in farms) / len(farms)
    coords = (
        [(dep_lat, dep_lng)]
        + [(f.lat, f.lng) for f in farms]
        + [(d.lat, d.lng) for d in demand_points]
    )

    # Tier-2: travel time adjustment from historical outcomes
    time_factor = await _route_history_factor()

    matrix = await get_distance_matrix(coords, coords)

    # Scale matrix when history shows roads are slower than expected
    if abs(time_factor - 1.0) > 0.01:
        matrix = [[cell * time_factor for cell in row] for row in matrix]

    plan: RoutePlan = solve_vrp(
        farms,
        demand_points,
        trucks,
        at_risk_stock,
        matrix,
        relaxation_factor=relaxation_factor,
    )

    state["route_plan"] = plan

    route_count = len(plan.routes)
    stop_count = sum(len(r.stops) for r in plan.routes)
    _append(state, t0, ["maps_api.get_distance_matrix", "vrp_solver.solve_vrp"],
            relaxation_factor, retry_count, route_count,
            f"objective={plan.objective_value} routes={route_count} stops={stop_count} "
            f"time_factor={time_factor:.3f} relax={relaxation_factor}")

    logger.info(
        "logistics_agent: routes=%d stops=%d objective=%s retry=%d relax=%.2f",
        route_count, stop_count, plan.objective_value, retry_count, relaxation_factor,
    )
    return state


def _append(
    state: AgentFarmState,
    t0: datetime,
    tools: list[str],
    relaxation_factor: float,
    retry_count: int,
    route_count: int,
    notes: str,
) -> None:
    trace: AgentTrace = {
        "agent_name": "logistics_agent",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": ["outcome_store.get_route_history"] + tools,
        "notes": notes,
        "token_count": None,
    }
    state["agent_traces"] = [*state.get("agent_traces", []), trace]
