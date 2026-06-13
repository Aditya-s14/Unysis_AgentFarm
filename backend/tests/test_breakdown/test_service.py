"""Integration tests for breakdown report guards."""

from __future__ import annotations

from datetime import date, time as dt_time
from unittest.mock import AsyncMock, patch

import pytest

from models.schemas import BreakdownReport, Route, RoutePlan, RouteStop, Truck
from tools.breakdown.incident import BreakdownError
from tools.breakdown.service import report_breakdown


def _mini_detail() -> dict:
    from tests.test_notifications.test_alert_builder import _state

    state = _state()
    farms = [f.model_dump(mode="json") for f in state["farms"]]
    dps = [d.model_dump(mode="json") for d in state["demand_points"]]
    trucks = [t.model_dump(mode="json") for t in state["trucks"]]
    return {
        "at_risk_stock": [s.model_dump() for s in state["at_risk_stock"]],
        "weather_risk_summary": {},
        "scenario_snapshot": {
            "farms": farms,
            "demand_points": dps,
            "trucks": trucks,
            "route_plan": state["route_plan"].model_dump(),
            "validation_result": state["validation_result"].model_dump(),
            "weather_fetch_meta": {},
            "retry_count": 0,
            "scenario_type": "normal_day",
        },
    }


def _plan(*, dispatched: bool = True):
    from datetime import datetime, timezone

    return type(
        "P",
        (),
        {
            "id": "00000000-0000-0000-0000-000000000099",
            "run_id": "run-bd-1",
            "route_plan_json": _mini_detail()["scenario_snapshot"]["route_plan"],
            "validation_json": _mini_detail()["scenario_snapshot"]["validation_result"],
            "notifications_dispatched_at": datetime.now(timezone.utc) if dispatched else None,
        },
    )()


@pytest.mark.asyncio
async def test_report_rejects_before_notifications_dispatched() -> None:
    plan = _plan(dispatched=False)
    with patch(
        "tools.breakdown.service.get_plan_by_run_id",
        new=AsyncMock(return_value=plan),
    ):
        with pytest.raises(BreakdownError) as exc:
            await report_breakdown(
                "run-bd-1",
                BreakdownReport(truck_id="tr-r1"),
            )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_report_rejects_unknown_truck() -> None:
    plan = _plan()
    detail = _mini_detail()
    with (
        patch("tools.breakdown.service.get_plan_by_run_id", new=AsyncMock(return_value=plan)),
        patch("tools.breakdown.service.get_plan_run_detail", new=AsyncMock(return_value=detail)),
        patch("tools.breakdown.service.list_incidents", new=AsyncMock(return_value=[])),
    ):
        with pytest.raises(BreakdownError) as exc:
            await report_breakdown(
                "run-bd-1",
                BreakdownReport(truck_id="tr-unknown"),
            )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_report_with_spare_truck_replans() -> None:
    from datetime import time as dt_time

    plan = _plan()
    detail = _mini_detail()
    spare = Truck(
        id="tr-spare",
        capacity_kg=5000.0,
        cost_per_km=15.0,
        availability_start=dt_time(5, 0),
        availability_end=dt_time(22, 0),
        driver_phone="+919910000099",
    )
    detail["scenario_snapshot"]["trucks"].append(spare.model_dump(mode="json"))

    with (
        patch("tools.breakdown.service.get_plan_by_run_id", new=AsyncMock(return_value=plan)),
        patch("tools.breakdown.service.get_plan_run_detail", new=AsyncMock(return_value=detail)),
        patch("tools.breakdown.service.list_incidents", new=AsyncMock(return_value=[])),
        patch("tools.breakdown.service.update_plan_routes", new=AsyncMock(return_value=plan)),
        patch("tools.breakdown.service.create_run_log", new=AsyncMock()),
    ):
        preview = await report_breakdown(
            "run-bd-1",
            BreakdownReport(truck_id="tr-r1", spare_truck_id="tr-spare"),
        )
    assert preview.incident.truck_id == "tr-r1"
    assert preview.spare_truck_id == "tr-spare"
