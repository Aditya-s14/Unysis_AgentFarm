"""Dispatcher tests with mock provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from models.schemas import ValidationResult
from tests.test_notifications.test_alert_builder import _state
from tools.notifications.alert_builder import build_truck_alerts
from tools.notifications.dispatcher import dispatch_farm_alerts


@pytest.mark.asyncio
async def test_dispatch_sends_sms_and_voice_for_urgent_farm() -> None:
    state = _state()
    with (
        patch("tools.notifications.dispatcher.get_settings") as mock_settings,
        patch(
            "tools.notifications.dispatcher.create_notification_log",
            new=AsyncMock(),
        ) as mock_log,
        patch(
            "tools.notifications.dispatcher.get_provider",
        ) as mock_get_provider,
    ):
        settings = mock_settings.return_value
        settings.NOTIFY_ENABLED = True
        settings.NOTIFY_PROVIDER = "mock"
        settings.NOTIFY_REQUIRE_APPROVAL = False
        settings.MSG91_TEMPLATE_ID = ""

        provider = AsyncMock()
        provider.name = "mock"
        provider.send_sms = AsyncMock(return_value="mock-sms-1")
        provider.send_voice = AsyncMock(return_value="mock-voice-1")
        mock_get_provider.return_value = provider

        await dispatch_farm_alerts(
            run_id="run-test",
            state=state,
            plan_id="00000000-0000-0000-0000-000000000001",
            fpo_approved=True,
        )

    provider.send_sms.assert_awaited()
    provider.send_voice.assert_awaited_once()


def test_build_truck_alerts_uses_demo_driver_phone() -> None:
    state = _state()
    state["trucks"][0] = state["trucks"][0].model_copy(
        update={"id": "tr-004", "capacity_kg": 3000.0, "driver_phone": None},
    )
    state["route_plan"].routes[0].truck_id = "tr-004"
    alerts = build_truck_alerts(state)
    assert len(alerts) == 1
    assert alerts[0].phone == "+919910000004"


@pytest.mark.asyncio
async def test_dispatch_officer_digest_when_plan_invalid() -> None:
    state = _state(
        validation_result=ValidationResult(valid=False, errors=["capacity"]),
        retry_count=2,
    )
    with (
        patch("tools.notifications.dispatcher.get_settings") as mock_settings,
        patch(
            "tools.notifications.dispatcher.create_notification_log",
            new=AsyncMock(),
        ),
        patch(
            "tools.notifications.dispatcher.get_provider",
        ) as mock_get_provider,
    ):
        settings = mock_settings.return_value
        settings.NOTIFY_ENABLED = True
        settings.NOTIFY_PROVIDER = "mock"
        settings.NOTIFY_REQUIRE_APPROVAL = True
        settings.MSG91_TEMPLATE_ID = ""
        settings.FIELD_OFFICER_PHONE = "+919911111111"

        provider = AsyncMock()
        provider.name = "mock"
        provider.send_sms = AsyncMock(return_value="mock-sms-officer")
        mock_get_provider.return_value = provider

        await dispatch_farm_alerts(
            run_id="run-test",
            state=state,
            plan_id=None,
        )

    provider.send_sms.assert_awaited_once()
    body = provider.send_sms.await_args.args[1]
    assert "needs review" in body.lower()
