"""Broken-down trucks should not accept GPS ingest."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from models.schemas import BreakdownIncident, PositionReport, Route, RoutePlan, RouteStop
from tools.tracking.incident import TrackingError
from tools.tracking.service import ingest_position


@pytest.mark.asyncio
async def test_ingest_rejects_broken_truck() -> None:
    route = Route(
        truck_id="tr-broken",
        stops=[RouteStop(sequence=0, lat=13.0, lng=77.0, label="f1")],
    )
    plan = type(
        "P",
        (),
        {
            "id": "00000000-0000-0000-0000-000000000087",
            "run_id": "run-bd",
            "route_plan_json": RoutePlan(routes=[route]).model_dump(),
            "notifications_dispatched_at": datetime.now(timezone.utc),
        },
    )()
    incident = BreakdownIncident(
        incident_id="inc-1",
        run_id="run-bd",
        truck_id="tr-broken",
        reported_by="fpo",
        reason="engine_failure",
        status="approved",
        route_plan_before={},
        route_plan_after={},
    )
    with (
        patch("tools.tracking.service.get_plan_by_run_id", new=AsyncMock(return_value=plan)),
        patch("tools.tracking.service.list_incidents", new=AsyncMock(return_value=[incident])),
    ):
        with pytest.raises(TrackingError) as exc:
            await ingest_position(
                "run-bd",
                "tr-broken",
                PositionReport(lat=13.0, lng=77.0),
            )
    assert exc.value.status_code == 409
