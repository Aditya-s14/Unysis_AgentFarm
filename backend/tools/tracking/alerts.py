"""SMS dispatch when a truck deviates from its planned route."""

from __future__ import annotations

import logging

from config import get_settings
from models.schemas import RouteDeviationAlert, Truck
from tools.notifications.dispatcher import _log_notification
from tools.notifications.providers import get_provider
from tools.notifications.templates import (
    render_deviation_driver_sms,
    render_deviation_fpo_digest,
)

logger = logging.getLogger(__name__)


async def dispatch_deviation_alerts(
    *,
    run_id: str,
    plan_id: str,
    alert: RouteDeviationAlert,
    truck: Truck | None,
) -> dict[str, int]:
    """Notify driver and FPO when route deviation is confirmed."""
    settings = get_settings()
    if not settings.NOTIFY_ENABLED:
        logger.debug("NOTIFY_ENABLED=false; skipping deviation alerts run_id=%s", run_id)
        return {"sent": 0, "failed": 0, "skipped": 0}

    provider_name = settings.NOTIFY_PROVIDER.strip().lower() or "mock"
    try:
        provider = get_provider(provider_name)
    except ValueError as exc:
        logger.error("deviation provider unavailable: %s", exc)
        return {"sent": 0, "failed": 0, "skipped": 0}

    sent = 0
    failed = 0
    template_id = settings.MSG91_TEMPLATE_ID or None

    if truck and truck.driver_phone:
        body = render_deviation_driver_sms(
            truck_id=alert.truck_id,
            deviation_km=alert.deviation_km,
        )
        try:
            msg_id = await provider.send_sms(
                truck.driver_phone,
                body,
                template_id=template_id,
            )
            await _log_notification(
                run_id=run_id,
                plan_id=plan_id,
                farm_id=alert.truck_id,
                channel="sms",
                phone=truck.driver_phone,
                body=body,
                priority="urgent",
                provider=provider.name,
                provider_message_id=msg_id,
                status="sent",
            )
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("deviation driver SMS failed truck=%s: %s", alert.truck_id, exc)
            failed += 1

    officer_phone = (settings.FIELD_OFFICER_PHONE or "").strip()
    if officer_phone:
        body = render_deviation_fpo_digest(
            run_id=run_id,
            truck_id=alert.truck_id,
            deviation_km=alert.deviation_km,
        )
        try:
            msg_id = await provider.send_sms(officer_phone, body, template_id=template_id)
            await _log_notification(
                run_id=run_id,
                plan_id=plan_id,
                farm_id=None,
                channel="sms",
                phone=officer_phone,
                body=body,
                priority="urgent",
                provider=provider.name,
                provider_message_id=msg_id,
                status="sent",
            )
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("deviation FPO SMS failed: %s", exc)
            failed += 1

    return {"sent": sent, "failed": failed, "skipped": 0}
