"""FPO SMS alerts for crop-calendar truck gap warnings."""

from __future__ import annotations

import logging

import redis.asyncio as redis

from config import get_settings
from tools.crop_calendar import TruckGapAnalysis
from tools.notifications.dispatcher import _log_notification
from tools.notifications.providers import get_provider
from tools.notifications.templates import render_calendar_truck_gap_fpo

logger = logging.getLogger(__name__)

_REDIS: redis.Redis | None = None
_DEDUP_PREFIX = "calendar_alert:"
_DEDUP_TTL_S = 15 * 24 * 3600


async def _redis_client() -> redis.Redis:
    global _REDIS
    if _REDIS is None:
        _REDIS = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _REDIS


async def _already_sent(peak_date_iso: str) -> bool:
    try:
        r = await _redis_client()
        return bool(await r.exists(f"{_DEDUP_PREFIX}{peak_date_iso}"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("calendar dedup check failed: %s", exc)
        return False


async def _mark_sent(peak_date_iso: str) -> None:
    try:
        r = await _redis_client()
        await r.set(f"{_DEDUP_PREFIX}{peak_date_iso}", "1", ex=_DEDUP_TTL_S)
    except Exception as exc:  # noqa: BLE001
        logger.warning("calendar dedup mark failed: %s", exc)


async def dispatch_truck_gap_alert(
    analysis: TruckGapAnalysis,
    *,
    run_id: str | None = None,
) -> dict[str, int | bool]:
    """Send one FPO SMS per peak date (Redis dedup). Returns dispatch stats."""
    if not analysis.alert_due:
        return {"sent": 0, "failed": 0, "skipped": 0, "dispatched": False}

    peak_iso = analysis.peak_date.isoformat()
    if await _already_sent(peak_iso):
        logger.info("calendar alert dedup skip peak_date=%s", peak_iso)
        return {"sent": 0, "failed": 0, "skipped": 1, "dispatched": False}

    settings = get_settings()
    if not settings.NOTIFY_ENABLED:
        logger.debug("NOTIFY_ENABLED=false; skipping calendar alert peak=%s", peak_iso)
        return {"sent": 0, "failed": 0, "skipped": 1, "dispatched": False}

    officer_phone = (settings.FIELD_OFFICER_PHONE or "").strip()
    if not officer_phone:
        logger.debug("FIELD_OFFICER_PHONE unset; skipping calendar alert")
        return {"sent": 0, "failed": 0, "skipped": 1, "dispatched": False}

    provider_name = settings.NOTIFY_PROVIDER.strip().lower() or "mock"
    try:
        provider = get_provider(provider_name)
    except ValueError as exc:
        logger.error("calendar alert provider unavailable: %s", exc)
        return {"sent": 0, "failed": 0, "skipped": 0, "dispatched": False}

    body = render_calendar_truck_gap_fpo(analysis)
    template_id = settings.MSG91_TEMPLATE_ID or None
    rid = run_id or "calendar"

    try:
        msg_id = await provider.send_sms(officer_phone, body, template_id=template_id)
        await _log_notification(
            run_id=rid,
            plan_id=None,
            farm_id=None,
            channel="sms",
            phone=officer_phone,
            body=body,
            priority="urgent",
            provider=provider.name,
            provider_message_id=msg_id,
            status="sent",
        )
        await _mark_sent(peak_iso)
        logger.info(
            "calendar truck gap alert sent peak=%s gap=%d",
            peak_iso,
            analysis.truck_gap,
        )
        return {"sent": 1, "failed": 0, "skipped": 0, "dispatched": True}
    except Exception as exc:  # noqa: BLE001
        logger.warning("calendar FPO SMS failed: %s", exc)
        return {"sent": 0, "failed": 1, "skipped": 0, "dispatched": False}
