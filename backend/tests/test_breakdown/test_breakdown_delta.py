"""Tests for breakdown delta notification targeting."""

from __future__ import annotations

from datetime import date, time as dt_time
from unittest.mock import AsyncMock, patch

import pytest

from models.schemas import (
    AtRiskStock,
    BreakdownIncident,
    DemandPoint,
    Farm,
    Route,
    RoutePlan,
    RouteStop,
    Truck,
    ValidationResult,
)
from tools.notifications.breakdown_delta import _farm_to_truck, dispatch_breakdown_delta


def _state_with_routes(routes: list[Route]) -> dict:
    farm = Farm(
        id="farm-r1",
        name="Test Farm",
        lat=13.08,
        lng=77.54,
        crop_type="tomato",
        acreage=5.0,
        typical_yield_kg=400.0,
        harvest_window_start=date(2026, 1, 1),
        harvest_window_end=date(2026, 12, 31),
        phone="+919900000099",
        notify_opt_in=True,
    )
    dp = DemandPoint(
        id="dp-r1",
        name="Test Mandi",
        lat=13.02,
        lng=77.53,
        type="apmc",
        base_demand_per_day=800.0,
    )
    truck_a = Truck(
        id="tr-a",
        capacity_kg=3000.0,
        cost_per_km=20.0,
        availability_start=dt_time(5, 30),
        availability_end=dt_time(20, 0),
        driver_phone="+919910000001",
    )
    truck_b = Truck(
        id="tr-b",
        capacity_kg=3000.0,
        cost_per_km=20.0,
        availability_start=dt_time(5, 30),
        availability_end=dt_time(20, 0),
        driver_phone="+919910000002",
    )
    return {
        "run_id": "run-1",
        "farms": [farm],
        "demand_points": [dp],
        "trucks": [truck_a, truck_b],
        "at_risk_stock": [
            AtRiskStock(
                farm_id=farm.id,
                crop_type="tomato",
                kg_at_risk=420.0,
                hours_until_spoilage=8.0,
            ),
        ],
        "route_plan": RoutePlan(routes=routes),
        "validation_result": ValidationResult(valid=True, errors=[]),
    }


def test_farm_to_truck_mapping() -> None:
    routes = [
        Route(
            truck_id="tr-a",
            stops=[RouteStop(sequence=0, lat=13.0, lng=77.5, label="farm-r1")],
        ),
    ]
    state = _state_with_routes(routes)
    assert _farm_to_truck(state)["farm-r1"] == "tr-a"


@pytest.mark.asyncio
async def test_delta_notify_only_reassigned_farms() -> None:
    before_routes = [
        Route(
            truck_id="tr-a",
            stops=[
                RouteStop(sequence=0, lat=13.08, lng=77.54, label="farm-r1"),
                RouteStop(sequence=1, lat=13.02, lng=77.53, demand_point_id="dp-r1"),
            ],
            distance_km=12.0,
        ),
    ]
    after_routes = [
        Route(
            truck_id="tr-b",
            stops=[
                RouteStop(sequence=0, lat=13.08, lng=77.54, label="farm-r1"),
                RouteStop(sequence=1, lat=13.02, lng=77.53, demand_point_id="dp-r1"),
            ],
            distance_km=12.0,
        ),
    ]
    state_before = _state_with_routes(before_routes)
    state_after = _state_with_routes(after_routes)
    incident = BreakdownIncident(
        incident_id="inc-1",
        run_id="run-1",
        truck_id="tr-a",
        reported_by="fpo",
        reason="engine_failure",
        status="pending_approval",
        pending_farm_ids=["farm-r1"],
        spare_truck_id="tr-b",
        route_plan_before={},
        route_plan_after={},
    )

    mock_provider = AsyncMock()
    mock_provider.name = "mock"
    mock_provider.send_sms = AsyncMock(return_value="mock-id")

    with (
        patch("tools.notifications.breakdown_delta.get_settings") as mock_settings,
        patch("tools.notifications.breakdown_delta.get_provider", return_value=mock_provider),
        patch("tools.notifications.breakdown_delta._log_notification", new=AsyncMock()),
    ):
        mock_settings.return_value.NOTIFY_ENABLED = True
        mock_settings.return_value.NOTIFY_PROVIDER = "mock"
        mock_settings.return_value.MSG91_TEMPLATE_ID = ""
        mock_settings.return_value.FIELD_OFFICER_PHONE = ""

        stats = await dispatch_breakdown_delta(
            run_id="run-1",
            plan_id="plan-1",
            incident=incident,
            state_before=state_before,
            state_after=state_after,
        )

    assert stats["sent"] >= 2
    bodies = [c.args[1] for c in mock_provider.send_sms.call_args_list]
    assert any("UPDATE:" in b for b in bodies)
