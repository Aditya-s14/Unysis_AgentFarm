"""Dispatch farmer SMS/voice alerts after a plan is persisted."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from config import get_settings
from memory.state import AgentFarmState
from tools.db import create_notification_log
from tools.notifications.alert_builder import (
    build_farm_alerts,
    build_truck_alerts,
    count_urgent_farms,
    should_skip_farmer_notifications,
)
from tools.notifications.demo_contacts import enrich_state_contacts
from tools.notifications.providers import get_provider
from tools.notifications.templates import (
    render_officer_digest,
    render_sms,
    render_truck_sms,
    render_voice,
)

logger = logging.getLogger(__name__)


async def _log_notification(
    *,
    run_id: str,
    plan_id: str | None,
    farm_id: str | None,
    channel: str,
    phone: str,
    body: str,
    priority: str,
    provider: str,
    provider_message_id: str | None,
    status: str,
    error: str | None = None,
) -> None:
    plan_uuid = uuid.UUID(plan_id) if plan_id else None
    try:
        await create_notification_log(
            run_id=run_id,
            plan_id=plan_uuid,
            farm_id=farm_id,
            channel=channel,
            phone=phone,
            message_body=body,
            priority=priority,
            provider=provider,
            provider_message_id=provider_message_id,
            status=status,
            error=error,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("notification log persist failed run_id=%s: %s", run_id, exc)


async def _dispatch_officer_digest(
    *,
    run_id: str,
    plan_id: str | None,
    state: AgentFarmState,
    provider_name: str,
    provider: Any,
) -> None:
    settings = get_settings()
    phone = (settings.FIELD_OFFICER_PHONE or "").strip()
    if not phone:
        return

    vr = state.get("validation_result")
    error_count = len(vr.errors) if vr and vr.errors else 0
    body = render_officer_digest(
        run_id=run_id,
        urgent_count=count_urgent_farms(state),
        error_count=error_count,
    )
    try:
        msg_id = await provider.send_sms(
            phone,
            body,
            template_id=settings.MSG91_TEMPLATE_ID or None,
        )
        await _log_notification(
            run_id=run_id,
            plan_id=plan_id,
            farm_id=None,
            channel="sms",
            phone=phone,
            body=body,
            priority="urgent",
            provider=provider_name,
            provider_message_id=msg_id,
            status="sent",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("officer digest failed run_id=%s: %s", run_id, exc)
        await _log_notification(
            run_id=run_id,
            plan_id=plan_id,
            farm_id=None,
            channel="sms",
            phone=phone,
            body=body,
            priority="urgent",
            provider=provider_name,
            provider_message_id=None,
            status="failed",
            error=str(exc),
        )


async def dispatch_farm_alerts(
    *,
    run_id: str,
    state: AgentFarmState,
    plan_id: str | None,
    fpo_approved: bool = False,
) -> dict[str, int]:
    """Send farmer/truck alerts asynchronously; never raises to the caller."""
    settings = get_settings()
    if not settings.NOTIFY_ENABLED:
        logger.debug("NOTIFY_ENABLED=false; skipping alerts run_id=%s", run_id)
        return {"sent": 0, "failed": 0, "skipped": 0}

    provider_name = settings.NOTIFY_PROVIDER.strip().lower() or "mock"
    try:
        provider = get_provider(provider_name)
    except ValueError as exc:
        logger.error("notification provider unavailable: %s", exc)
        return {"sent": 0, "failed": 0, "skipped": 0}

    sent = 0
    failed = 0

    if settings.NOTIFY_REQUIRE_APPROVAL and not fpo_approved:
        if should_skip_farmer_notifications(state, fpo_approved=False):
            await _dispatch_officer_digest(
                run_id=run_id,
                plan_id=plan_id,
                state=enrich_state_contacts(state),
                provider_name=provider.name,
                provider=provider,
            )
        logger.info("notifications held pending FPO approval run_id=%s", run_id)
        return {"sent": 0, "failed": 0, "skipped": 1}

    enriched = enrich_state_contacts(state)
    farm_alerts = build_farm_alerts(enriched, fpo_approved=fpo_approved)
    truck_alerts = build_truck_alerts(enriched, fpo_approved=fpo_approved)

    if not farm_alerts and not truck_alerts:
        logger.info("no farmer/truck alerts to send run_id=%s", run_id)
        return {"sent": 0, "failed": 0, "skipped": 0}

    logger.info(
        "dispatching %d farmer + %d truck alert(s) run_id=%s fpo_approved=%s",
        len(farm_alerts),
        len(truck_alerts),
        run_id,
        fpo_approved,
    )
    template_id = settings.MSG91_TEMPLATE_ID or None

    for alert in farm_alerts:
        if alert.channel in ("sms", "both"):
            body = render_sms(alert)
            try:
                msg_id = await provider.send_sms(
                    alert.phone,
                    body,
                    template_id=template_id,
                )
                await _log_notification(
                    run_id=run_id,
                    plan_id=plan_id,
                    farm_id=alert.farm_id,
                    channel="sms",
                    phone=alert.phone,
                    body=body,
                    priority=alert.priority,
                    provider=provider.name,
                    provider_message_id=msg_id,
                    status="sent",
                )
                sent += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "SMS failed farm=%s run_id=%s: %s",
                    alert.farm_id,
                    run_id,
                    exc,
                )
                await _log_notification(
                    run_id=run_id,
                    plan_id=plan_id,
                    farm_id=alert.farm_id,
                    channel="sms",
                    phone=alert.phone,
                    body=body,
                    priority=alert.priority,
                    provider=provider.name,
                    provider_message_id=None,
                    status="failed",
                    error=str(exc),
                )
                failed += 1

        if alert.channel in ("voice", "both") and alert.priority == "urgent":
            script = render_voice(alert)
            try:
                call_id = await provider.send_voice(
                    alert.phone,
                    script,
                    language=alert.language,
                )
                await _log_notification(
                    run_id=run_id,
                    plan_id=plan_id,
                    farm_id=alert.farm_id,
                    channel="voice",
                    phone=alert.phone,
                    body=script,
                    priority=alert.priority,
                    provider=provider.name,
                    provider_message_id=call_id,
                    status="sent",
                )
                sent += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "voice failed farm=%s run_id=%s: %s",
                    alert.farm_id,
                    run_id,
                    exc,
                )
                await _log_notification(
                    run_id=run_id,
                    plan_id=plan_id,
                    farm_id=alert.farm_id,
                    channel="voice",
                    phone=alert.phone,
                    body=script,
                    priority=alert.priority,
                    provider=provider.name,
                    provider_message_id=None,
                    status="failed",
                    error=str(exc),
                )
                failed += 1

    for alert in truck_alerts:
        body = render_truck_sms(alert)
        try:
            msg_id = await provider.send_sms(
                alert.phone,
                body,
                template_id=template_id,
            )
            await _log_notification(
                run_id=run_id,
                plan_id=plan_id,
                farm_id=alert.truck_id,
                channel="sms",
                phone=alert.phone,
                body=body,
                priority="normal",
                provider=provider.name,
                provider_message_id=msg_id,
                status="sent",
            )
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "truck SMS failed truck=%s run_id=%s: %s",
                alert.truck_id,
                run_id,
                exc,
            )
            await _log_notification(
                run_id=run_id,
                plan_id=plan_id,
                farm_id=alert.truck_id,
                channel="sms",
                phone=alert.phone,
                body=body,
                priority="normal",
                provider=provider.name,
                provider_message_id=None,
                status="failed",
                error=str(exc),
            )
            failed += 1

    return {"sent": sent, "failed": failed, "skipped": 0}
