"""FPO approval gateway tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tools.notifications.approval import ApprovalError, approve_run_and_notify
from tools.notifications.run_state import rebuild_state_from_snapshot


def _mini_detail() -> dict:
    from datetime import date, time as dt_time

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
            "scenario_type": "heat_wave",
        },
    }


@pytest.mark.asyncio
async def test_approve_run_and_notify_dispatches_with_fpo_flag() -> None:
    plan = type(
        "P",
        (),
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "run_id": "run-approve-1",
            "route_plan_json": {},
            "validation_json": None,
            "approved_at": None,
            "approved_by": None,
            "notifications_dispatched_at": None,
        },
    )()
    detail = _mini_detail()
    state = rebuild_state_from_snapshot(run_id="run-approve-1", plan=plan, detail=detail)

    with (
        patch("tools.notifications.approval.get_plan_by_run_id", new=AsyncMock(return_value=plan)),
        patch("tools.notifications.approval.get_plan_run_detail", new=AsyncMock(return_value=detail)),
        patch("tools.notifications.approval.mark_plan_approved", new=AsyncMock(return_value=plan)),
        patch(
            "tools.notifications.approval.mark_notifications_dispatched",
            new=AsyncMock(return_value=plan),
        ),
        patch(
            "tools.notifications.approval.dispatch_farm_alerts",
            new=AsyncMock(return_value={"sent": 3, "failed": 0, "skipped": 0}),
        ) as mock_dispatch,
        patch(
            "tools.notifications.approval.approval_status_for_plan",
            return_value="dispatched",
        ),
    ):
        result = await approve_run_and_notify("run-approve-1")

    mock_dispatch.assert_awaited_once()
    assert mock_dispatch.await_args.kwargs["fpo_approved"] is True
    assert result["notifications"]["sent"] == 3


@pytest.mark.asyncio
async def test_approve_rejects_already_dispatched() -> None:
    from datetime import datetime, timezone

    plan = type(
        "P",
        (),
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "notifications_dispatched_at": datetime.now(timezone.utc),
        },
    )()
    with patch(
        "tools.notifications.approval.get_plan_by_run_id",
        new=AsyncMock(return_value=plan),
    ):
        with pytest.raises(ApprovalError) as exc:
            await approve_run_and_notify("run-dup")
    assert exc.value.status_code == 409
