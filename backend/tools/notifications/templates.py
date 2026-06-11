"""SMS and voice templates for farmer pickup/spoilage alerts."""

from __future__ import annotations

from tools.notifications.alert_builder import FarmAlert, TruckAlert

SMS_TEMPLATES: dict[str, str] = {
    "en": (
        "Kisan Mitra: {farm_name} - Truck {truck_id} pickup ~{pickup_time}. "
        "Send {kg}kg {crop} to {mandi_name}. {urgency_line}{weather_line}"
    ),
    "hi": (
        "Kisan Mitra: {farm_name} - Truck {truck_id} {pickup_time} par. "
        "{kg}kg {crop} {mandi_name} bhejen. {urgency_line}{weather_line}"
    ),
}

VOICE_TEMPLATES: dict[str, str] = {
    "en": (
        "Kisan Mitra alert for {farm_name}. "
        "Truck {truck_id} pickup around {pickup_time}. "
        "Please send {kg} kilograms of {crop} to {mandi_name}. "
        "{urgency_line}{weather_line}"
    ),
    "hi": (
        "Kisan Mitra suchna {farm_name} ke liye. "
        "Truck {truck_id} {pickup_time} par aayegi. "
        "Kripya {kg} kilo {crop} {mandi_name} bhejen. "
        "{urgency_line}{weather_line}"
    ),
}

OFFICER_DIGEST_EN = (
    "AgentFarm: Plan {run_id} needs review. "
    "{urgent_count} urgent farms, {error_count} validation issues. "
    "Check dashboard before notifying farmers."
)


def _urgency_line(alert: FarmAlert, lang: str) -> str:
    hours = alert.hours_until_spoilage
    if hours is None or hours >= 12:
        return ""
    h = int(hours)
    if lang == "hi":
        return f"URGENT: {h} ghante mein kharab ho sakta hai. "
    return f"URGENT: spoilage in {h}h. "


def _weather_line(alert: FarmAlert) -> str:
    parts: list[str] = []
    if alert.weather_note:
        parts.append(alert.weather_note.strip())
    if alert.weather_disclaimer:
        parts.append(alert.weather_disclaimer.strip())
    if not parts:
        return ""
    text = " ".join(parts)
    return text if text.endswith(".") else f"{text}."


def render_sms(alert: FarmAlert) -> str:
    lang = alert.language if alert.language in SMS_TEMPLATES else "en"
    template = SMS_TEMPLATES[lang]
    body = template.format(
        farm_name=alert.farm_name[:24],
        truck_id=alert.truck_id,
        pickup_time=alert.pickup_time,
        kg=int(alert.kg),
        crop=alert.crop_type,
        mandi_name=alert.mandi_name[:28],
        urgency_line=_urgency_line(alert, lang),
        weather_line=_weather_line(alert),
    )
    return body[:160]


def render_voice(alert: FarmAlert) -> str:
    lang = alert.language if alert.language in VOICE_TEMPLATES else "en"
    template = VOICE_TEMPLATES[lang]
    return template.format(
        farm_name=alert.farm_name[:40],
        truck_id=alert.truck_id,
        pickup_time=alert.pickup_time,
        kg=int(alert.kg),
        crop=alert.crop_type,
        mandi_name=alert.mandi_name[:40],
        urgency_line=_urgency_line(alert, lang),
        weather_line=_weather_line(alert),
    )


def render_officer_digest(*, run_id: str, urgent_count: int, error_count: int) -> str:
    return OFFICER_DIGEST_EN.format(
        run_id=run_id[:8],
        urgent_count=urgent_count,
        error_count=error_count,
    )[:160]


TRUCK_SMS_EN = (
    "Kisan Mitra: {truck_id} route assigned. Start ~{start_time}. "
    "Pickups: {farm_summary}. Deliver: {mandi_summary}. {stop_count} stops."
)


def render_truck_sms(alert: TruckAlert) -> str:
    body = TRUCK_SMS_EN.format(
        truck_id=alert.truck_id,
        start_time=alert.start_time,
        farm_summary=alert.farm_summary[:40],
        mandi_summary=alert.mandi_summary[:35],
        stop_count=alert.stop_count,
    )
    return body[:160]


BREAKDOWN_FARM_REASSIGN_EN = (
    "UPDATE: Kisan Mitra — Truck {broken_truck_id} broke down. "
    "New pickup: Truck {truck_id} ~{pickup_time}. "
    "{kg}kg {crop} to {mandi_name}."
)

BREAKDOWN_FARM_REASSIGN_HI = (
    "UPDATE: Kisan Mitra — Truck {broken_truck_id} kharab. "
    "Nayi truck {truck_id} ~{pickup_time}. "
    "{kg}kg {crop} {mandi_name} bhejen."
)

BREAKDOWN_DRIVER_CANCEL_EN = (
    "UPDATE: Kisan Mitra — {truck_id} route cancelled ({reason}). "
    "Stand down; FPO will contact you."
)

BREAKDOWN_SPARE_DRIVER_EN = (
    "UPDATE: Kisan Mitra — Urgent reassignment from {broken_truck_id}. "
    "Truck {truck_id} start ~{start_time}. Pickups: {farm_summary}. "
    "Deliver: {mandi_summary}."
)

BREAKDOWN_FPO_DIGEST_EN = (
    "AgentFarm breakdown: run {run_id}. {broken_truck_id} down → "
    "spare {spare_truck_id}. {farm_count} farms reassigned."
)


def render_breakdown_farm_reassign_sms(
    alert: FarmAlert,
    *,
    broken_truck_id: str,
) -> str:
    lang = alert.language if alert.language in ("en", "hi") else "en"
    template = BREAKDOWN_FARM_REASSIGN_HI if lang == "hi" else BREAKDOWN_FARM_REASSIGN_EN
    body = template.format(
        broken_truck_id=broken_truck_id,
        truck_id=alert.truck_id,
        pickup_time=alert.pickup_time,
        kg=int(alert.kg),
        crop=alert.crop_type,
        mandi_name=alert.mandi_name[:28],
    )
    return body[:160]


def render_breakdown_cancel_sms(*, truck_id: str, reason: str) -> str:
    return BREAKDOWN_DRIVER_CANCEL_EN.format(
        truck_id=truck_id,
        reason=reason.replace("_", " "),
    )[:160]


def render_breakdown_spare_driver_sms(
    alert: TruckAlert,
    *,
    broken_truck_id: str,
) -> str:
    body = BREAKDOWN_SPARE_DRIVER_EN.format(
        broken_truck_id=broken_truck_id,
        truck_id=alert.truck_id,
        start_time=alert.start_time,
        farm_summary=alert.farm_summary[:40],
        mandi_summary=alert.mandi_summary[:35],
    )
    return body[:160]


def render_breakdown_fpo_digest(
    *,
    run_id: str,
    broken_truck_id: str,
    spare_truck_id: str,
    farm_count: int,
) -> str:
    return BREAKDOWN_FPO_DIGEST_EN.format(
        run_id=run_id[:8],
        broken_truck_id=broken_truck_id,
        spare_truck_id=spare_truck_id,
        farm_count=farm_count,
    )[:160]
