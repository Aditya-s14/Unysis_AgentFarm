"""Route deviation geometry and debounce/cooldown state machine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from config import get_settings
from models.schemas import RouteStop
from tools.maps_api import haversine_km

# Demo fixture bounds (India belt with margin)
_LAT_MIN, _LAT_MAX = 8.0, 35.0
_LNG_MIN, _NG_MAX = 68.0, 98.0


def validate_demo_coords(lat: float, lng: float) -> bool:
    return _LAT_MIN <= lat <= _LAT_MAX and _LNG_MIN <= lng <= _NG_MAX


def distance_to_route_km(lat: float, lng: float, stops: list[RouteStop]) -> float:
    """Minimum distance from a point to the planned route polyline (km)."""
    if not stops:
        return 0.0

    ordered = sorted(stops, key=lambda s: s.sequence)
    if len(ordered) == 1:
        return haversine_km((lat, lng), (ordered[0].lat, ordered[0].lng))

    point = (lat, lng)
    min_d = float("inf")
    for i in range(len(ordered) - 1):
        a = (ordered[i].lat, ordered[i].lng)
        b = (ordered[i + 1].lat, ordered[i + 1].lng)
        for step in range(11):
            t = step / 10.0
            sample = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            min_d = min(min_d, haversine_km(point, sample))
    return round(min_d, 3)


def is_on_route(deviation_km: float, threshold_km: float | None = None) -> bool:
    threshold = threshold_km if threshold_km is not None else get_settings().DEVIATION_THRESHOLD_KM
    return deviation_km <= threshold


@dataclass
class DeviationState:
    off_route_since: str | None = None
    last_alert_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> DeviationState:
        if not data:
            return cls()
        return cls(
            off_route_since=data.get("off_route_since"),
            last_alert_at=data.get("last_alert_at"),
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "off_route_since": self.off_route_since,
            "last_alert_at": self.last_alert_at,
        }


@dataclass
class DeviationEvaluation:
    should_alert: bool
    new_state: DeviationState
    on_route: bool
    deviation_km: float


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def evaluate_deviation(
    *,
    deviation_km: float,
    now: datetime,
    state: DeviationState,
    threshold_km: float | None = None,
    debounce_seconds: int | None = None,
    cooldown_min: int | None = None,
) -> DeviationEvaluation:
    """Decide whether to fire a deviation alert after debounce and cooldown."""
    settings = get_settings()
    threshold = threshold_km if threshold_km is not None else settings.DEVIATION_THRESHOLD_KM
    debounce = debounce_seconds if debounce_seconds is not None else settings.DEVIATION_DEBOUNCE_SECONDS
    cooldown = cooldown_min if cooldown_min is not None else settings.DEVIATION_ALERT_COOLDOWN_MIN

    on_route = is_on_route(deviation_km, threshold)
    now_iso = now.astimezone(timezone.utc).isoformat()

    if on_route:
        return DeviationEvaluation(
            should_alert=False,
            new_state=DeviationState(off_route_since=None, last_alert_at=state.last_alert_at),
            on_route=True,
            deviation_km=deviation_km,
        )

    new_state = DeviationState(
        off_route_since=state.off_route_since or now_iso,
        last_alert_at=state.last_alert_at,
    )

    if new_state.off_route_since:
        off_since = _parse_iso(new_state.off_route_since)
        if (now - off_since).total_seconds() < debounce:
            return DeviationEvaluation(
                should_alert=False,
                new_state=new_state,
                on_route=False,
                deviation_km=deviation_km,
            )

    if new_state.last_alert_at:
        last_alert = _parse_iso(new_state.last_alert_at)
        if (now - last_alert).total_seconds() < cooldown * 60:
            return DeviationEvaluation(
                should_alert=False,
                new_state=new_state,
                on_route=False,
                deviation_km=deviation_km,
            )

    new_state.last_alert_at = now_iso
    return DeviationEvaluation(
        should_alert=True,
        new_state=new_state,
        on_route=False,
        deviation_km=deviation_km,
    )


def position_status(
    *,
    on_route: bool,
    reported_at: datetime,
    now: datetime | None = None,
    stale_minutes: int | None = None,
) -> str:
    """Return TruckPosition status string."""
    settings = get_settings()
    stale = stale_minutes if stale_minutes is not None else settings.TRACKING_STALE_MINUTES
    now = now or datetime.now(timezone.utc)
    age_min = (now - reported_at.astimezone(timezone.utc)).total_seconds() / 60.0
    if age_min > stale:
        return "stale"
    if on_route:
        return "on_route"
    return "deviating"
