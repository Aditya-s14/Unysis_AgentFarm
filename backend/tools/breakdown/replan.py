"""Partial VRP re-plan when a truck breaks down mid-route."""

from __future__ import annotations

import logging
from typing import Any

from agents.metrics import _routed_farm_to_dp
from agents.validator import validate_plan
from memory.state import AgentFarmState
from models.schemas import (
    DemandPoint,
    Farm,
    Route,
    RoutePlan,
    Truck,
    ValidationResult,
)
from tools.maps_api import get_distance_matrix
from tools.vrp_solver import solve_vrp

logger = logging.getLogger(__name__)


def _farm_ids_on_route(route: Route) -> list[str]:
    return [
        s.label
        for s in route.stops
        if s.demand_point_id is None and s.label
    ]


def _mandi_ids_on_route(route: Route) -> list[str]:
    return [
        s.demand_point_id
        for s in route.stops
        if s.demand_point_id
    ]


def _active_truck_ids(routes: list[Route]) -> set[str]:
    return {r.truck_id for r in routes if r.stops}


def select_spare_truck(
    trucks: list[Truck],
    routes: list[Route],
    *,
    broken_truck_id: str,
    spare_truck_id: str | None,
) -> Truck | None:
    """Pick spare truck: explicit id, else smallest-capacity unassigned truck."""
    truck_by_id = {t.id: t for t in trucks}
    if spare_truck_id:
        truck = truck_by_id.get(spare_truck_id)
        if truck is None or spare_truck_id == broken_truck_id:
            return None
        return truck

    assigned = _active_truck_ids(routes)
    idle = [
        t for t in trucks
        if t.id not in assigned and t.id != broken_truck_id
    ]
    if not idle:
        return None
    return min(idle, key=lambda t: t.capacity_kg)


def pending_farm_ids(
    route: Route,
    completed_farm_ids: list[str],
) -> list[str]:
    completed = set(completed_farm_ids)
    return [fid for fid in _farm_ids_on_route(route) if fid not in completed]


async def solve_partial_routes(
    *,
    pending_farms: list[Farm],
    demand_points: list[DemandPoint],
    spare_trucks: list[Truck],
    at_risk_stock: list,
) -> RoutePlan:
    """Run a mini CVRP for pending pickups onto spare truck capacity."""
    if not pending_farms or not spare_trucks:
        return RoutePlan(routes=[], notes="no_pending_or_no_spare")

    dep_lat = sum(f.lat for f in pending_farms) / len(pending_farms)
    dep_lng = sum(f.lng for f in pending_farms) / len(pending_farms)
    coords = (
        [(dep_lat, dep_lng)]
        + [(f.lat, f.lng) for f in pending_farms]
        + [(d.lat, d.lng) for d in demand_points]
    )
    matrix = await get_distance_matrix(coords, coords)
    return solve_vrp(
        pending_farms,
        demand_points,
        spare_trucks[:1],
        at_risk_stock,
        matrix,
        demand_scale=1.0,
    )


def merge_route_plans(
    current: RoutePlan,
    *,
    broken_truck_id: str,
    spare_truck_id: str,
    new_routes: list[Route],
) -> RoutePlan:
    """Drop broken route; replace spare route if present; append reassignment."""
    kept = [
        r for r in current.routes
        if r.truck_id not in (broken_truck_id, spare_truck_id)
    ]
    merged_routes = kept + new_routes
    total_km = sum(r.distance_km or 0.0 for r in merged_routes)
    return RoutePlan(
        routes=merged_routes,
        objective_value=round(total_km, 3) if total_km else current.objective_value,
        notes="breakdown_replan",
    )


def _relevant_demand_points(
    state: AgentFarmState,
    pending_farms: list[Farm],
    broken_route: Route,
) -> list[DemandPoint]:
    all_dps = state.get("demand_points") or []
    dp_by_id = {d.id: d for d in all_dps}
    mandi_ids = _mandi_ids_on_route(broken_route)
    if mandi_ids:
        return [dp_by_id[mid] for mid in mandi_ids if mid in dp_by_id]

    hint_state: AgentFarmState = {
        "route_plan": RoutePlan(routes=[broken_route]),
    }
    farm_to_dp = _routed_farm_to_dp(hint_state, pending_farms, all_dps)
    selected: list[DemandPoint] = []
    seen: set[str] = set()
    for farm in pending_farms:
        dp_id = farm_to_dp.get(farm.id)
        if dp_id and dp_id in dp_by_id and dp_id not in seen:
            selected.append(dp_by_id[dp_id])
            seen.add(dp_id)
    return selected or list(all_dps[:3])


async def execute_partial_replan(
    state: AgentFarmState,
    *,
    broken_truck_id: str,
    completed_farm_ids: list[str],
    spare_truck_id: str | None,
) -> tuple[RoutePlan, ValidationResult, dict[str, Any]]:
    """Re-plan pending pickups from a broken truck onto spare capacity."""
    route_plan = state.get("route_plan")
    if not route_plan:
        raise ValueError("No route plan in state")

    broken_route: Route | None = None
    for route in route_plan.routes:
        if route.truck_id == broken_truck_id:
            broken_route = route
            break
    if broken_route is None:
        raise ValueError(f"Truck {broken_truck_id!r} not found in route plan")

    pending_ids = pending_farm_ids(broken_route, completed_farm_ids)
    farms = state.get("farms") or []
    farm_by_id = {f.id: f for f in farms}
    pending_farms = [farm_by_id[fid] for fid in pending_ids if fid in farm_by_id]

    trucks = state.get("trucks") or []
    spare = select_spare_truck(
        trucks,
        route_plan.routes,
        broken_truck_id=broken_truck_id,
        spare_truck_id=spare_truck_id,
    )
    if spare is None:
        raise ValueError(
            "No spare truck available — add an idle truck to the fleet or specify spare_truck_id",
        )

    if not pending_farms:
        merged = merge_route_plans(
            route_plan,
            broken_truck_id=broken_truck_id,
            spare_truck_id=spare.id,
            new_routes=[],
        )
        state_after = dict(state)
        state_after["route_plan"] = merged
        validation = validate_plan(state_after)
        return merged, validation, {
            "pending_farm_ids": [],
            "spare_truck_id": spare.id,
            "message": "All farms on route already completed; broken route removed",
        }

    dps = _relevant_demand_points(state, pending_farms, broken_route)
    partial = await solve_partial_routes(
        pending_farms=pending_farms,
        demand_points=dps,
        spare_trucks=[spare],
        at_risk_stock=state.get("at_risk_stock") or [],
    )

    new_routes = [r for r in partial.routes if r.stops]
    if not new_routes:
        raise ValueError("Partial VRP produced no routes for pending pickups")

    merged = merge_route_plans(
        route_plan,
        broken_truck_id=broken_truck_id,
        spare_truck_id=spare.id,
        new_routes=new_routes,
    )

    state_after = dict(state)
    state_after["route_plan"] = merged
    validation = validate_plan(state_after)

    logger.info(
        "breakdown_replan: truck=%s spare=%s pending_farms=%d valid=%s",
        broken_truck_id,
        spare.id,
        len(pending_farms),
        validation.valid,
    )
    return merged, validation, {
        "pending_farm_ids": pending_ids,
        "spare_truck_id": spare.id,
    }
