"""Unit tests for breakdown partial re-plan."""

from __future__ import annotations

from datetime import date, time as dt_time

import pytest

from models.schemas import (
    AtRiskStock,
    DemandPoint,
    Farm,
    Route,
    RoutePlan,
    RouteStop,
    Truck,
)
from tools.breakdown.replan import (
    merge_route_plans,
    pending_farm_ids,
    select_spare_truck,
)


def _farm(fid: str = "farm-a") -> Farm:
    return Farm(
        id=fid,
        name="Farm A",
        lat=13.08,
        lng=77.54,
        crop_type="tomato",
        acreage=5.0,
        typical_yield_kg=400.0,
        harvest_window_start=date(2026, 1, 1),
        harvest_window_end=date(2026, 12, 31),
    )


def _truck(tid: str, cap: float = 3000.0) -> Truck:
    return Truck(
        id=tid,
        capacity_kg=cap,
        cost_per_km=20.0,
        availability_start=dt_time(5, 30),
        availability_end=dt_time(20, 0),
    )


def _broken_route() -> Route:
    farm = _farm("farm-a")
    dp = DemandPoint(
        id="dp-1",
        name="Mandi",
        lat=13.02,
        lng=77.53,
        type="apmc",
        base_demand_per_day=800.0,
    )
    return Route(
        truck_id="tr-broken",
        stops=[
            RouteStop(sequence=0, lat=farm.lat, lng=farm.lng, label=farm.id),
            RouteStop(sequence=1, lat=dp.lat, lng=dp.lng, demand_point_id=dp.id),
        ],
        distance_km=15.0,
    )


def test_pending_farm_ids_excludes_completed() -> None:
    route = _broken_route()
    pending = pending_farm_ids(route, ["farm-a"])
    assert pending == []


def test_select_spare_truck_prefers_idle() -> None:
    trucks = [_truck("tr-broken"), _truck("tr-spare", 2500.0)]
    routes = [_broken_route()]
    spare = select_spare_truck(
        trucks,
        routes,
        broken_truck_id="tr-broken",
        spare_truck_id=None,
    )
    assert spare is not None
    assert spare.id == "tr-spare"


def test_select_spare_truck_explicit_id() -> None:
    trucks = [_truck("tr-broken"), _truck("tr-spare")]
    routes = [_broken_route()]
    spare = select_spare_truck(
        trucks,
        routes,
        broken_truck_id="tr-broken",
        spare_truck_id="tr-spare",
    )
    assert spare is not None
    assert spare.id == "tr-spare"


def test_select_spare_truck_none_when_all_assigned() -> None:
    trucks = [_truck("tr-broken"), _truck("tr-other")]
    routes = [
        _broken_route(),
        Route(truck_id="tr-other", stops=[RouteStop(sequence=0, lat=1, lng=1, label="x")]),
    ]
    spare = select_spare_truck(
        trucks,
        routes,
        broken_truck_id="tr-broken",
        spare_truck_id=None,
    )
    assert spare is None


def test_merge_route_plans_drops_broken() -> None:
    current = RoutePlan(routes=[_broken_route()])
    new_route = Route(
        truck_id="tr-spare",
        stops=[RouteStop(sequence=0, lat=13.0, lng=77.5, label="farm-a")],
        distance_km=10.0,
    )
    merged = merge_route_plans(
        current,
        broken_truck_id="tr-broken",
        spare_truck_id="tr-spare",
        new_routes=[new_route],
    )
    ids = {r.truck_id for r in merged.routes}
    assert "tr-broken" not in ids
    assert "tr-spare" in ids


@pytest.mark.asyncio
async def test_execute_partial_replan_assigns_pending() -> None:
    from memory.state import AgentFarmState
    from tools.breakdown.replan import execute_partial_replan

    farm = _farm("farm-a")
    dp = DemandPoint(
        id="dp-1",
        name="Mandi",
        lat=13.02,
        lng=77.53,
        type="apmc",
        base_demand_per_day=800.0,
    )
    broken = _truck("tr-broken")
    spare = _truck("tr-spare")
    state: AgentFarmState = {
        "run_id": "run-1",
        "scenario_type": "normal_day",
        "farms": [farm],
        "demand_points": [dp],
        "trucks": [broken, spare],
        "at_risk_stock": [
            AtRiskStock(
                farm_id=farm.id,
                crop_type="tomato",
                kg_at_risk=200.0,
                hours_until_spoilage=10.0,
            ),
        ],
        "route_plan": RoutePlan(routes=[_broken_route()]),
    }

    merged, validation, meta = await execute_partial_replan(
        state,
        broken_truck_id="tr-broken",
        completed_farm_ids=[],
        spare_truck_id=None,
    )
    assert meta["spare_truck_id"] == "tr-spare"
    assert "farm-a" in meta["pending_farm_ids"]
    spare_routes = [r for r in merged.routes if r.truck_id == "tr-spare"]
    assert spare_routes
    assert any(
        s.label == "farm-a"
        for r in spare_routes
        for s in r.stops
    )
