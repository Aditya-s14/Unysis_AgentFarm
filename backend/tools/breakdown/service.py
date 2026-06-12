"""Breakdown report and approval orchestration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from config import get_settings
from models.schemas import BreakdownIncident, BreakdownReport, ReplanPreview
from tools.breakdown.incident import (
    INCIDENT_LOG_MESSAGE,
    BreakdownError,
    broken_truck_ids,
    get_incident,
    list_incidents,
)
from tools.breakdown.replan import execute_partial_replan
from tools.db import (
    create_run_log,
    get_plan_by_run_id,
    get_plan_run_detail,
    update_plan_routes,
)
from tools.notifications.run_state import rebuild_state_from_snapshot

logger = logging.getLogger(__name__)


def _ensure_enabled() -> None:
    if not get_settings().BREAKDOWN_ENABLED:
        raise BreakdownError("Breakdown assistance is disabled", status_code=503)


async def report_breakdown(
    run_id: str,
    report: BreakdownReport,
) -> ReplanPreview:
    """Report a truck breakdown, partial re-plan, and return preview."""
    _ensure_enabled()

    plan = await get_plan_by_run_id(run_id)
    if plan is None:
        raise BreakdownError(f"Run {run_id!r} not found", status_code=404)

    if plan.notifications_dispatched_at is None:
        raise BreakdownError(
            "Notifications not yet dispatched — approve the plan before reporting breakdown",
            status_code=409,
        )

    detail = await get_plan_run_detail(run_id)
    if detail is None:
        raise BreakdownError(
            "Run detail not found; cannot rebuild replan context",
            status_code=404,
        )

    try:
        state = rebuild_state_from_snapshot(run_id=run_id, plan=plan, detail=detail)
    except ValueError as exc:
        raise BreakdownError(str(exc), status_code=422) from exc

    # Overlay current route plan (may have been updated by prior incidents)
    from models.schemas import RoutePlan, ValidationResult

    state["route_plan"] = RoutePlan.model_validate(plan.route_plan_json or {})
    if plan.validation_json:
        state["validation_result"] = ValidationResult.model_validate(plan.validation_json)

    existing = await list_incidents(run_id)
    if report.truck_id in broken_truck_ids(existing):
        raise BreakdownError(
            f"Truck {report.truck_id!r} already has an active breakdown incident",
            status_code=409,
        )

    route_plan_before = state["route_plan"].model_dump()
    try:
        merged, validation, meta = await execute_partial_replan(
            state,
            broken_truck_id=report.truck_id,
            completed_farm_ids=report.completed_farm_ids,
            spare_truck_id=report.spare_truck_id,
        )
    except ValueError as exc:
        raise BreakdownError(str(exc), status_code=422) from exc

    incident_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    route_plan_after = merged.model_dump()

    incident = BreakdownIncident(
        incident_id=incident_id,
        run_id=run_id,
        truck_id=report.truck_id,
        reported_by=report.reported_by,
        reason=report.reason,
        status="pending_approval",
        completed_farm_ids=list(report.completed_farm_ids),
        pending_farm_ids=list(meta.get("pending_farm_ids") or []),
        spare_truck_id=meta.get("spare_truck_id"),
        route_plan_before=route_plan_before,
        route_plan_after=route_plan_after,
        validation=validation,
        created_at=now,
    )

    await update_plan_routes(
        plan.id,
        route_plan_json=route_plan_after,
        validation_json=validation.model_dump(),
    )

    await create_run_log(
        run_id=run_id,
        message=INCIDENT_LOG_MESSAGE,
        level="warning" if not validation.valid else "info",
        plan_id=plan.id,
        detail=incident.model_dump(mode="json"),
    )

    preview = ReplanPreview(
        incident=incident,
        affected_farms=incident.pending_farm_ids,
        spare_truck_id=incident.spare_truck_id,
        validation_valid=validation.valid,
        validation_errors=list(validation.errors),
    )

    if get_settings().BREAKDOWN_AUTO_NOTIFY:
        return await approve_breakdown_incident(run_id, incident_id, preview=preview)

    return preview


async def approve_breakdown_incident(
    run_id: str,
    incident_id: str,
    *,
    preview: ReplanPreview | None = None,
) -> ReplanPreview:
    """FPO approves breakdown replan and dispatches delta notifications."""
    _ensure_enabled()

    incident = await get_incident(run_id, incident_id)
    if incident is None:
        raise BreakdownError(f"Incident {incident_id!r} not found", status_code=404)

    if incident.status == "approved":
        raise BreakdownError(
            "Breakdown notifications already dispatched for this incident",
            status_code=409,
        )

    plan = await get_plan_by_run_id(run_id)
    if plan is None:
        raise BreakdownError(f"Run {run_id!r} not found", status_code=404)

    detail = await get_plan_run_detail(run_id)
    if detail is None:
        raise BreakdownError("Run detail not found", status_code=404)

    from models.schemas import RoutePlan, ValidationResult

    state_before = rebuild_state_from_snapshot(run_id=run_id, plan=plan, detail=detail)
    state_before["route_plan"] = RoutePlan.model_validate(incident.route_plan_before)

    state_after = rebuild_state_from_snapshot(run_id=run_id, plan=plan, detail=detail)
    state_after["route_plan"] = RoutePlan.model_validate(incident.route_plan_after)
    if incident.validation:
        state_after["validation_result"] = incident.validation

    from tools.notifications.breakdown_delta import dispatch_breakdown_delta

    stats = await dispatch_breakdown_delta(
        run_id=run_id,
        plan_id=str(plan.id),
        incident=incident,
        state_before=state_before,
        state_after=state_after,
    )

    now = datetime.now(timezone.utc).isoformat()
    approved_incident = incident.model_copy(
        update={
            "status": "approved",
            "approved_at": now,
            "notifications": stats,
        },
    )

    await create_run_log(
        run_id=run_id,
        message=INCIDENT_LOG_MESSAGE,
        level="info",
        plan_id=plan.id,
        detail=approved_incident.model_dump(mode="json"),
    )

    logger.info(
        "breakdown approved run_id=%s incident=%s sent=%d",
        run_id,
        incident_id,
        stats.get("sent", 0),
    )

    if preview is not None:
        return preview.model_copy(
            update={
                "incident": approved_incident,
            },
        )

    return ReplanPreview(
        incident=approved_incident,
        affected_farms=approved_incident.pending_farm_ids,
        spare_truck_id=approved_incident.spare_truck_id,
        validation_valid=bool(approved_incident.validation and approved_incident.validation.valid),
        validation_errors=list(approved_incident.validation.errors) if approved_incident.validation else [],
    )
