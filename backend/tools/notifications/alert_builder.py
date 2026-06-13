"""Build per-farm SMS/voice alerts from a completed pipeline state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agents.metrics import _routed_farm_to_dp
from agents.review_flags import needs_human_review
from config import get_settings
from memory.state import AgentFarmState
from models.schemas import AtRiskStock, DemandPoint, Farm, RouteStop, Truck
from tools.maps_api import haversine_km
from tools.notifications.demo_contacts import enrich_state_contacts

AlertChannel = Literal["sms", "voice", "both"]
AlertPriority = Literal["urgent", "normal"]

_AVG_SPEED_KMH = 50.0


@dataclass(frozen=True)
class FarmAlert:
    farm_id: str
    farm_name: str
    phone: str
    language: str
    channel: AlertChannel
    priority: AlertPriority
    pickup_time: str
    truck_id: str
    mandi_name: str
    crop_type: str
    kg: float
    hours_until_spoilage: float | None
    weather_note: str | None
    weather_disclaimer: str | None


@dataclass(frozen=True)
class TruckAlert:
    truck_id: str
    phone: str
    start_time: str
    farm_summary: str
    mandi_summary: str
    stop_count: int


def should_skip_farmer_notifications(
    state: AgentFarmState,
    *,
    fpo_approved: bool = False,
) -> bool:
    """Skip auto-alerts when the plan is blocked, empty, or awaiting FPO approval."""
    if state.get("pipeline_blocked"):
        return True
    route_plan = state.get("route_plan")
    if not route_plan or not route_plan.routes:
        return True
    if fpo_approved:
        return False
    if needs_human_review(state):
        return True
    vr = state.get("validation_result")
    if vr is not None and not vr.valid:
        return True
    return False


def _format_pickup_time(truck: Truck, cumulative_km: float) -> str:
    base_minutes = truck.availability_start.hour * 60 + truck.availability_start.minute
    travel_minutes = int((cumulative_km / _AVG_SPEED_KMH) * 60)
    total_minutes = base_minutes + travel_minutes
    hour, minute = divmod(total_minutes, 60)
    hour = hour % 24
    period = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {period}"


def _cumulative_km_to_stop(stops: list[RouteStop], target: RouteStop) -> float:
    ordered = sorted(stops, key=lambda s: s.sequence)
    total = 0.0
    prev = (ordered[0].lat, ordered[0].lng) if ordered else (0.0, 0.0)
    for stop in ordered:
        cur = (stop.lat, stop.lng)
        total += haversine_km(prev, cur)
        prev = cur
        if stop is target:
            break
    return total


def _at_risk_lookup(state: AgentFarmState) -> dict[str, AtRiskStock]:
    lookup: dict[str, AtRiskStock] = {}
    for item in state.get("at_risk_stock") or []:
        if isinstance(item, AtRiskStock):
            lookup[item.farm_id] = item
        elif isinstance(item, dict) and item.get("farm_id"):
            lookup[str(item["farm_id"])] = AtRiskStock.model_validate(item)
    return lookup


def _weather_context(state: AgentFarmState, farm_id: str) -> tuple[str | None, str | None]:
    meta = dict(state.get("weather_fetch_meta") or {})
    risk = dict(state.get("weather_risk_summary") or {})
    note: str | None = None
    disclaimer: str | None = None

    severity = risk.get(farm_id)
    if severity == "severe":
        note = "Severe weather — protect harvest and cover crates."
    elif severity == "warning":
        note = "Weather warning — plan pickup early."

    source = meta.get("weather_source")
    if source in ("synthetic_fallback", "stale_cache", "mixed"):
        disclaimer = str(meta.get("weather_disclaimer") or "Weather estimate; confirm locally.")

    return note, disclaimer


def _resolve_channel(farm: Farm, hours: float | None) -> AlertChannel | None:
    settings = get_settings()
    pref = farm.notify_channel
    if pref == "none":
        return None

    voice_cutoff = settings.NOTIFY_VOICE_SPOILAGE_HOURS
    sms_cutoff = settings.NOTIFY_SPOILAGE_HOURS
    h = hours if hours is not None else 9999.0

    if h >= sms_cutoff and not settings.NOTIFY_ALL_ROUTED:
        return None

    if h < voice_cutoff:
        if pref in ("voice", "both"):
            return "both" if pref == "both" else "voice"
        return "sms"

    if pref == "voice":
        return "voice"
    if pref in ("sms", "both"):
        return "sms"
    return None


def _resolve_priority(hours: float | None) -> AlertPriority:
    settings = get_settings()
    if hours is not None and hours < settings.NOTIFY_VOICE_SPOILAGE_HOURS:
        return "urgent"
    if hours is not None and hours < settings.NOTIFY_SPOILAGE_HOURS:
        return "urgent"
    return "normal"


def build_farm_alerts(
    state: AgentFarmState,
    *,
    fpo_approved: bool = False,
) -> list[FarmAlert]:
    """Return SMS/voice alerts for routed farms with phone + opt-in."""
    state = enrich_state_contacts(state)
    if should_skip_farmer_notifications(state, fpo_approved=fpo_approved):
        return []

    farms_list = state.get("farms") or []
    dps_list = state.get("demand_points") or []
    farms: dict[str, Farm] = {f.id: f for f in farms_list}
    dps: dict[str, DemandPoint] = {d.id: d for d in dps_list}
    trucks: dict[str, Truck] = {t.id: t for t in (state.get("trucks") or [])}
    at_risk = _at_risk_lookup(state)
    farm_to_dp = _routed_farm_to_dp(state, farms_list, dps_list)
    route_plan = state.get("route_plan")
    if not route_plan:
        return []

    alerts: list[FarmAlert] = []
    seen: set[str] = set()

    for route in route_plan.routes:
        truck = trucks.get(route.truck_id)
        if truck is None:
            continue
        ordered_stops = sorted(route.stops, key=lambda s: s.sequence)
        for stop in ordered_stops:
            if stop.demand_point_id or not stop.label:
                continue
            farm_id = stop.label
            if farm_id in seen:
                continue
            farm = farms.get(farm_id)
            if farm is None or not farm.phone or not farm.notify_opt_in:
                continue

            stock = at_risk.get(farm_id)
            hours = stock.hours_until_spoilage if stock else None
            channel = _resolve_channel(farm, hours)
            if channel is None:
                continue

            dp_id = farm_to_dp.get(farm_id)
            mandi = dps.get(dp_id) if dp_id else None
            mandi_name = mandi.name if mandi else (dp_id or "nearest mandi")
            kg = stock.kg_at_risk if stock else farm.typical_yield_kg
            cumul_km = _cumulative_km_to_stop(ordered_stops, stop)
            weather_note, weather_disclaimer = _weather_context(state, farm_id)

            alerts.append(
                FarmAlert(
                    farm_id=farm_id,
                    farm_name=farm.name,
                    phone=farm.phone,
                    language=farm.preferred_language or "en",
                    channel=channel,
                    priority=_resolve_priority(hours),
                    pickup_time=_format_pickup_time(truck, cumul_km),
                    truck_id=route.truck_id,
                    mandi_name=mandi_name,
                    crop_type=stock.crop_type if stock else farm.crop_type,
                    kg=float(kg),
                    hours_until_spoilage=hours,
                    weather_note=weather_note,
                    weather_disclaimer=weather_disclaimer,
                ),
            )
            seen.add(farm_id)

    return alerts


def build_truck_alerts(
    state: AgentFarmState,
    *,
    fpo_approved: bool = False,
) -> list[TruckAlert]:
    """Return SMS alerts for truck drivers assigned to routes."""
    state = enrich_state_contacts(state)
    if should_skip_farmer_notifications(state, fpo_approved=fpo_approved):
        return []

    farms: dict[str, Farm] = {f.id: f for f in (state.get("farms") or [])}
    dps: dict[str, DemandPoint] = {d.id: d for d in (state.get("demand_points") or [])}
    trucks: dict[str, Truck] = {t.id: t for t in (state.get("trucks") or [])}
    route_plan = state.get("route_plan")
    if not route_plan:
        return []

    alerts: list[TruckAlert] = []
    for route in route_plan.routes:
        truck = trucks.get(route.truck_id)
        if truck is None or not truck.driver_phone:
            continue
        ordered = sorted(route.stops, key=lambda s: s.sequence)
        farm_names: list[str] = []
        mandi_names: list[str] = []
        for stop in ordered:
            if stop.demand_point_id:
                dp = dps.get(stop.demand_point_id)
                name = dp.name if dp else stop.demand_point_id
                if name and name not in mandi_names:
                    mandi_names.append(name)
            elif stop.label:
                farm = farms.get(stop.label)
                name = farm.name if farm else stop.label
                if name not in farm_names:
                    farm_names.append(name)

        if not farm_names and not mandi_names:
            continue

        alerts.append(
            TruckAlert(
                truck_id=route.truck_id,
                phone=truck.driver_phone,
                start_time=_format_pickup_time(truck, 0.0),
                farm_summary=", ".join(farm_names[:3]) or "assigned farms",
                mandi_summary=", ".join(mandi_names[:2]) or "assigned mandis",
                stop_count=len(ordered),
            ),
        )
    return alerts


def count_urgent_farms(state: AgentFarmState) -> int:
    settings = get_settings()
    at_risk = _at_risk_lookup(state)
    return sum(
        1
        for stock in at_risk.values()
        if (stock.hours_until_spoilage or 9999.0) < settings.NOTIFY_SPOILAGE_HOURS
    )
