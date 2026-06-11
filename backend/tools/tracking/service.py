"""GPS ingest orchestration and tracking queries."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from config import get_settings
from models.schemas import (
    PositionIngestResponse,
    PositionReport,
    Route,
    RouteDeviationAlert,
    RoutePlan,
    Truck,
    TruckPosition,
)
from tools.breakdown.incident import broken_truck_ids, list_incidents
from tools.db import create_run_log, get_plan_by_run_id
from tools.tracking.alerts import dispatch_deviation_alerts
from tools.tracking.deviation import (
    distance_to_route_km,
    evaluate_deviation,
    position_status,
    validate_demo_coords,
)
from tools.tracking.incident import DEVIATION_LOG_MESSAGE, TrackingError
from tools.tracking.position_store import (
    get_deviation_state_with_fallback,
    get_position_with_fallback,
    list_positions as redis_list_positions,
    save_deviation_state_with_fallback,
    save_position_with_fallback,
)

logger = logging.getLogger(__name__)


def _ensure_enabled() -> None:
    if not get_settings().TRACKING_ENABLED:
        raise TrackingError("GPS tracking is disabled", status_code=503)


def verify_ingest_key(provided: str | None) -> None:
    expected = (get_settings().TRACKING_INGEST_KEY or "").strip()
    if not expected:
        return
    if (provided or "").strip() != expected:
        raise TrackingError("Invalid tracking ingest key", status_code=401)


def _route_for_truck(plan: RoutePlan, truck_id: str) -> Route | None:
    for route in plan.routes:
        if route.truck_id == truck_id and route.stops:
            return route
    return None


async def _require_dispatched_plan(run_id: str):
    plan = await get_plan_by_run_id(run_id)
    if plan is None:
        raise TrackingError(f"Run {run_id!r} not found", status_code=404)
    if plan.notifications_dispatched_at is None:
        raise TrackingError(
            "Notifications not yet dispatched — approve the plan before GPS tracking",
            status_code=409,
        )
    return plan


async def ingest_position(
    run_id: str,
    truck_id: str,
    report: PositionReport,
    *,
    trucks: list[Truck] | None = None,
) -> PositionIngestResponse:
    """Ingest driver GPS, evaluate deviation, optionally alert."""
    _ensure_enabled()
    plan = await _require_dispatched_plan(run_id)

    if not validate_demo_coords(report.lat, report.lng):
        raise TrackingError(
            "Coordinates outside supported demo region",
            status_code=422,
        )

    route_plan = RoutePlan.model_validate(plan.route_plan_json or {})
    route = _route_for_truck(route_plan, truck_id)
    if route is None:
        raise TrackingError(
            f"Truck {truck_id!r} has no active route in this plan",
            status_code=409,
        )

    incidents = await list_incidents(run_id)
    if truck_id in broken_truck_ids(incidents):
        raise TrackingError(
            f"Truck {truck_id!r} is marked broken down — tracking paused",
            status_code=409,
        )

    now = datetime.now(timezone.utc)
    reported_at = report.reported_at or now
    if reported_at.tzinfo is None:
        reported_at = reported_at.replace(tzinfo=timezone.utc)

    deviation_km = distance_to_route_km(report.lat, report.lng, route.stops)
    state = await get_deviation_state_with_fallback(run_id, truck_id)
    evaluation = evaluate_deviation(
        deviation_km=deviation_km,
        now=now,
        state=state,
    )
    await save_deviation_state_with_fallback(run_id, truck_id, evaluation.new_state)

    status = position_status(
        on_route=evaluation.on_route,
        reported_at=reported_at,
        now=now,
    )
    position = TruckPosition(
        run_id=run_id,
        truck_id=truck_id,
        lat=report.lat,
        lng=report.lng,
        reported_at=reported_at.astimezone(timezone.utc).isoformat(),
        on_route=evaluation.on_route,
        deviation_km=deviation_km,
        status=status,  # type: ignore[arg-type]
    )
    await save_position_with_fallback(position)

    alert: RouteDeviationAlert | None = None
    alert_triggered = False

    if evaluation.should_alert:
        settings = get_settings()
        truck_obj: Truck | None = None
        if trucks:
            truck_obj = next((t for t in trucks if t.id == truck_id), None)

        alert_id = str(uuid4())
        now_iso = now.isoformat()
        alert = RouteDeviationAlert(
            alert_id=alert_id,
            run_id=run_id,
            truck_id=truck_id,
            deviation_km=deviation_km,
            threshold_km=settings.DEVIATION_THRESHOLD_KM,
            lat=report.lat,
            lng=report.lng,
            status="open",
            created_at=now_iso,
        )
        stats = await dispatch_deviation_alerts(
            run_id=run_id,
            plan_id=str(plan.id),
            alert=alert,
            truck=truck_obj,
        )
        alert = alert.model_copy(
            update={
                "notified_at": now_iso,
                "notifications": stats,
            },
        )
        await create_run_log(
            run_id=run_id,
            message=DEVIATION_LOG_MESSAGE,
            level="warning",
            plan_id=plan.id,
            detail=alert.model_dump(mode="json"),
        )
        alert_triggered = True
        logger.info(
            "route deviation alert run_id=%s truck=%s km=%.2f sent=%d",
            run_id,
            truck_id,
            deviation_km,
            stats.get("sent", 0),
        )

    return PositionIngestResponse(
        position=position,
        alert_triggered=alert_triggered,
        alert=alert,
    )


async def list_positions(run_id: str) -> list[TruckPosition]:
    """Return all known positions for trucks on the active plan."""
    _ensure_enabled()
    plan = await _require_dispatched_plan(run_id)
    route_plan = RoutePlan.model_validate(plan.route_plan_json or {})
    truck_ids = [r.truck_id for r in route_plan.routes if r.stops]
    positions = await redis_list_positions(run_id, truck_ids)

    now = datetime.now(timezone.utc)
    settings = get_settings()
    refreshed: list[TruckPosition] = []
    for tid in truck_ids:
        pos = next((p for p in positions if p.truck_id == tid), None)
        if pos is None:
            pos = await get_position_with_fallback(run_id, tid)
        if pos is None:
            continue
        reported = datetime.fromisoformat(pos.reported_at.replace("Z", "+00:00"))
        status = position_status(
            on_route=pos.on_route,
            reported_at=reported,
            now=now,
            stale_minutes=settings.TRACKING_STALE_MINUTES,
        )
        refreshed.append(pos.model_copy(update={"status": status}))  # type: ignore[arg-type]
    return refreshed
