"""Tests for deviation SMS dispatch."""

from __future__ import annotations

from datetime import time as dt_time
from unittest.mock import AsyncMock, patch

import pytest

from models.schemas import RouteDeviationAlert, Truck
from tools.tracking.alerts import dispatch_deviation_alerts


@pytest.mark.asyncio
async def test_deviation_alerts_driver_and_fpo() -> None:
    alert = RouteDeviationAlert(
        alert_id="a1",
        run_id="run-1",
        truck_id="tr-1",
        deviation_km=5.2,
        threshold_km=3.0,
        lat=14.0,
        lng=78.0,
        status="open",
    )
    truck = Truck(
        id="tr-1",
        capacity_kg=3000.0,
        cost_per_km=20.0,
        availability_start=dt_time(5, 0),
        availability_end=dt_time(20, 0),
        driver_phone="+919910000001",
    )
    mock_provider = AsyncMock()
    mock_provider.name = "mock"
    mock_provider.send_sms = AsyncMock(return_value="mock-id")

    with (
        patch("tools.tracking.alerts.get_settings") as mock_settings,
        patch("tools.tracking.alerts.get_provider", return_value=mock_provider),
        patch("tools.tracking.alerts._log_notification", new=AsyncMock()),
    ):
        mock_settings.return_value.NOTIFY_ENABLED = True
        mock_settings.return_value.NOTIFY_PROVIDER = "mock"
        mock_settings.return_value.MSG91_TEMPLATE_ID = ""
        mock_settings.return_value.FIELD_OFFICER_PHONE = "+919900000001"

        stats = await dispatch_deviation_alerts(
            run_id="run-1",
            plan_id="plan-1",
            alert=alert,
            truck=truck,
        )

    assert stats["sent"] == 2
    bodies = [c.args[1] for c in mock_provider.send_sms.call_args_list]
    assert any("ALERT:" in b for b in bodies)
