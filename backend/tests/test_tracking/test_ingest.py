"""Integration tests for GPS ingest guards."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from models.schemas import PositionReport, Route, RoutePlan, RouteStop
from tools.tracking.incident import TrackingError
from tools.tracking.service import ingest_position


def _plan(*, dispatched: bool = True):
    route = Route(
        truck_id="tr-r1",
        stops=[
            RouteStop(sequence=0, lat=13.08, lng=77.54, label="farm-r1"),
            RouteStop(sequence=1, lat=13.02, lng=77.53, demand_point_id="dp-r1"),
        ],
        distance_km=12.0,
    )
    return type(
        "P",
        (),
        {
            "id": "00000000-0000-0000-0000-000000000088",
            "run_id": "run-trk-1",
            "route_plan_json": RoutePlan(routes=[route]).model_dump(),
            "notifications_dispatched_at": datetime.now(timezone.utc) if dispatched else None,
        },
    )()


@pytest.mark.asyncio
async def test_ingest_rejects_before_notifications() -> None:
    with patch(
        "tools.tracking.service.get_plan_by_run_id",
        new=AsyncMock(return_value=_plan(dispatched=False)),
    ):
        with pytest.raises(TrackingError) as exc:
            await ingest_position(
                "run-trk-1",
                "tr-r1",
                PositionReport(lat=13.08, lng=77.54),
            )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_ingest_accepts_on_route_position() -> None:
    plan = _plan()
    with (
        patch("tools.tracking.service.get_plan_by_run_id", new=AsyncMock(return_value=plan)),
        patch("tools.tracking.service.list_incidents", new=AsyncMock(return_value=[])),
        patch("tools.tracking.service.save_position_with_fallback", new=AsyncMock()),
        patch("tools.tracking.service.save_deviation_state_with_fallback", new=AsyncMock()),
        patch(
            "tools.tracking.service.get_deviation_state_with_fallback",
            new=AsyncMock(return_value=__import__(
                "tools.tracking.deviation", fromlist=["DeviationState"]
            ).DeviationState()),
        ),
    ):
        result = await ingest_position(
            "run-trk-1",
            "tr-r1",
            PositionReport(lat=13.08, lng=77.54),
        )
    assert result.position.truck_id == "tr-r1"
    assert result.position.on_route
    assert not result.alert_triggered
