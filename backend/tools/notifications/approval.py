"""FPO approval gateway — dispatch notifications only after explicit sign-off."""

from __future__ import annotations

import logging

from tools.db import (
    get_plan_by_run_id,
    get_plan_run_detail,
    mark_notifications_dispatched,
    mark_plan_approved,
)
from tools.notifications.dispatcher import dispatch_farm_alerts
from tools.notifications.run_state import (
    approval_status_for_plan,
    rebuild_state_from_snapshot,
)

logger = logging.getLogger(__name__)


class ApprovalError(Exception):
    """Base error for approval gateway failures."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


async def approve_run_and_notify(
    run_id: str,
    *,
    approved_by: str = "fpo",
) -> dict:
    """Mark plan approved and send farmer + driver notifications."""
    plan = await get_plan_by_run_id(run_id)
    if plan is None:
        raise ApprovalError(f"Run {run_id!r} not found", status_code=404)

    if plan.notifications_dispatched_at is not None:
        raise ApprovalError(
            "Notifications were already dispatched for this run",
            status_code=409,
        )

    detail = await get_plan_run_detail(run_id)
    if detail is None:
        raise ApprovalError(
            "Run detail not found; cannot rebuild notification context",
            status_code=404,
        )

    try:
        state = rebuild_state_from_snapshot(run_id=run_id, plan=plan, detail=detail)
    except ValueError as exc:
        raise ApprovalError(str(exc), status_code=422) from exc

    await mark_plan_approved(plan.id, approved_by=approved_by)
    stats = await dispatch_farm_alerts(
        run_id=run_id,
        state=state,
        plan_id=str(plan.id),
        fpo_approved=True,
    )
    updated = await mark_notifications_dispatched(plan.id)
    if updated is None:
        raise ApprovalError("Failed to mark notifications dispatched", status_code=500)

    logger.info(
        "FPO approved run_id=%s sent=%d failed=%d",
        run_id,
        stats.get("sent", 0),
        stats.get("failed", 0),
    )
    return {
        "run_id": run_id,
        "plan_id": str(plan.id),
        "approval_status": approval_status_for_plan(updated),
        "approved_at": updated.approved_at.isoformat() if updated.approved_at else None,
        "approved_by": updated.approved_by,
        "notifications_dispatched_at": (
            updated.notifications_dispatched_at.isoformat()
            if updated.notifications_dispatched_at
            else None
        ),
        "notifications": stats,
    }


def plan_approval_payload(plan) -> dict:  # noqa: ANN001
    """Serialize approval fields for GET /api/run/{run_id}."""
    if plan is None:
        return {
            "approval_status": "pending",
            "approved_at": None,
            "approved_by": None,
            "notifications_dispatched_at": None,
        }
    return {
        "approval_status": approval_status_for_plan(plan),
        "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        "approved_by": plan.approved_by,
        "notifications_dispatched_at": (
            plan.notifications_dispatched_at.isoformat()
            if plan.notifications_dispatched_at
            else None
        ),
    }
