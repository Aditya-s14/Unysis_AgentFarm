"""Delta SMS/voice dispatch after breakdown re-plan approval."""

from __future__ import annotations

import logging

from agents.metrics import _routed_farm_to_dp
from config import get_settings
from memory.state import AgentFarmState
from models.schemas import BreakdownIncident, DemandPoint, Farm, Truck
from tools.notifications.alert_builder import (
    FarmAlert,
    _at_risk_lookup,
    _cumulative_km_to_stop,
    _format_pickup_time,
    _weather_context,
)
from tools.notifications.demo_contacts import enrich_state_contacts
from tools.notifications.dispatcher import _log_notification
from tools.notifications.providers import get_provider
from tools.notifications.templates import (
    render_breakdown_cancel_sms,
    render_breakdown_farm_reassign_sms,
    render_breakdown_fpo_digest,
    render_breakdown_spare_driver_sms,
)

logger = logging.getLogger(__name__)


def _farm_to_truck(state: AgentFarmState) -> dict[str, str]:
    mapping: dict[str, str] = {}
    route_plan = state.get("route_plan")
    if not route_plan:
        return mapping
    for route in route_plan.routes:
        for stop in route.stops:
            if stop.demand_point_id is None and stop.label:
                mapping[stop.label] = route.truck_id
    return mapping


def _build_reassign_alert(
    state: AgentFarmState,
    farm_id: str,
    truck_id: str,
) -> FarmAlert | None:
    state = enrich_state_contacts(state)
    farms: dict[str, Farm] = {f.id: f for f in (state.get("farms") or [])}
    dps: dict[str, DemandPoint] = {d.id: d for d in (state.get("demand_points") or [])}
    trucks: dict[str, Truck] = {t.id: t for t in (state.get("trucks") or [])}
    farm = farms.get(farm_id)
    truck = trucks.get(truck_id)
    if farm is None or truck is None or not farm.phone or not farm.notify_opt_in:
        return None

    route_plan = state.get("route_plan")
    if not route_plan:
        return None

    target_stop = None
    ordered_stops = []
    for route in route_plan.routes:
        if route.truck_id != truck_id:
            continue
        ordered_stops = sorted(route.stops, key=lambda s: s.sequence)
        for stop in ordered_stops:
            if stop.label == farm_id:
                target_stop = stop
                break
        break
    if target_stop is None:
        return None

    at_risk = _at_risk_lookup(state)
    stock = at_risk.get(farm_id)
    farm_to_dp = _routed_farm_to_dp(state, list(farms.values()), list(dps.values()))
    dp_id = farm_to_dp.get(farm_id)
    mandi = dps.get(dp_id) if dp_id else None
    weather_note, weather_disclaimer = _weather_context(state, farm_id)
    cumul_km = _cumulative_km_to_stop(ordered_stops, target_stop)

    return FarmAlert(
        farm_id=farm_id,
        farm_name=farm.name,
        phone=farm.phone,
        language=farm.preferred_language or "en",
        channel="sms",
        priority="urgent",
        pickup_time=_format_pickup_time(truck, cumul_km),
        truck_id=truck_id,
        mandi_name=mandi.name if mandi else (dp_id or "nearest mandi"),
        crop_type=stock.crop_type if stock else farm.crop_type,
        kg=float(stock.kg_at_risk if stock else farm.typical_yield_kg),
        hours_until_spoilage=stock.hours_until_spoilage if stock else None,
        weather_note=weather_note,
        weather_disclaimer=weather_disclaimer,
    )


async def dispatch_breakdown_delta(
    *,
    run_id: str,
    plan_id: str,
    incident: BreakdownIncident,
    state_before: AgentFarmState,
    state_after: AgentFarmState,
) -> dict[str, int]:
    """Notify only farmers/drivers affected by the breakdown replan."""
    settings = get_settings()
    if not settings.NOTIFY_ENABLED:
        logger.debug("NOTIFY_ENABLED=false; skipping breakdown delta run_id=%s", run_id)
        return {"sent": 0, "failed": 0, "skipped": 0}

    provider_name = settings.NOTIFY_PROVIDER.strip().lower() or "mock"
    try:
        provider = get_provider(provider_name)
    except ValueError as exc:
        logger.error("breakdown provider unavailable: %s", exc)
        return {"sent": 0, "failed": 0, "skipped": 0}

    sent = 0
    failed = 0
    template_id = settings.MSG91_TEMPLATE_ID or None

    before_map = _farm_to_truck(state_before)
    after_map = _farm_to_truck(state_after)
    pending = set(incident.pending_farm_ids)

    for farm_id in pending:
        old_truck = before_map.get(farm_id)
        new_truck = after_map.get(farm_id)
        if not new_truck or new_truck == old_truck:
            continue
        alert = _build_reassign_alert(state_after, farm_id, new_truck)
        if alert is None:
            continue
        body = render_breakdown_farm_reassign_sms(
            alert,
            broken_truck_id=incident.truck_id,
        )
        try:
            msg_id = await provider.send_sms(alert.phone, body, template_id=template_id)
            await _log_notification(
                run_id=run_id,
                plan_id=plan_id,
                farm_id=farm_id,
                channel="sms",
                phone=alert.phone,
                body=body,
                priority="urgent",
                provider=provider.name,
                provider_message_id=msg_id,
                status="sent",
            )
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("breakdown farm SMS failed farm=%s: %s", farm_id, exc)
            await _log_notification(
                run_id=run_id,
                plan_id=plan_id,
                farm_id=farm_id,
                channel="sms",
                phone=alert.phone,
                body=body,
                priority="urgent",
                provider=provider.name,
                provider_message_id=None,
                status="failed",
                error=str(exc),
            )
            failed += 1

    trucks = {t.id: t for t in (state_after.get("trucks") or [])}
    broken = trucks.get(incident.truck_id)
    if broken and broken.driver_phone:
        body = render_breakdown_cancel_sms(
            truck_id=incident.truck_id,
            reason=incident.reason,
        )
        try:
            msg_id = await provider.send_sms(
                broken.driver_phone,
                body,
                template_id=template_id,
            )
            await _log_notification(
                run_id=run_id,
                plan_id=plan_id,
                farm_id=incident.truck_id,
                channel="sms",
                phone=broken.driver_phone,
                body=body,
                priority="urgent",
                provider=provider.name,
                provider_message_id=msg_id,
                status="sent",
            )
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("breakdown cancel SMS failed truck=%s: %s", incident.truck_id, exc)
            failed += 1

    spare_id = incident.spare_truck_id
    if spare_id:
        spare = trucks.get(spare_id)
        if spare and spare.driver_phone:
            from tools.notifications.alert_builder import build_truck_alerts

            enriched = enrich_state_contacts(state_after)
            spare_alerts = [
                a for a in build_truck_alerts(enriched, fpo_approved=True)
                if a.truck_id == spare_id
            ]
            if spare_alerts:
                alert = spare_alerts[0]
                body = render_breakdown_spare_driver_sms(
                    alert,
                    broken_truck_id=incident.truck_id,
                )
                try:
                    msg_id = await provider.send_sms(
                        spare.driver_phone,
                        body,
                        template_id=template_id,
                    )
                    await _log_notification(
                        run_id=run_id,
                        plan_id=plan_id,
                        farm_id=spare_id,
                        channel="sms",
                        phone=spare.driver_phone,
                        body=body,
                        priority="urgent",
                        provider=provider.name,
                        provider_message_id=msg_id,
                        status="sent",
                    )
                    sent += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("breakdown spare SMS failed truck=%s: %s", spare_id, exc)
                    failed += 1

    officer_phone = (settings.FIELD_OFFICER_PHONE or "").strip()
    if officer_phone:
        body = render_breakdown_fpo_digest(
            run_id=run_id,
            broken_truck_id=incident.truck_id,
            spare_truck_id=spare_id or "none",
            farm_count=len(pending),
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
            logger.warning("breakdown officer digest failed: %s", exc)
            failed += 1

    return {"sent": sent, "failed": failed, "skipped": 0}
