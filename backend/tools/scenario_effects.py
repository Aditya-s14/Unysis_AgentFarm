"""Scenario-type normalization and shared adjustment factors.

Frontend sends: normal_day | heat_wave | monsoon_disruption | live_weather
Tests may send:  normal | monsoon | default
"""

from __future__ import annotations

import re
from typing import Any

from models.schemas import Farm, WeatherEvent

WeatherEventLike = WeatherEvent | dict[str, Any]

# Canonical scenario slugs
NORMAL = "normal_day"
HEAT = "heat_wave"
MONSOON = "monsoon_disruption"
LIVE = "live_weather"

_CANONICAL = frozenset({NORMAL, HEAT, MONSOON, LIVE})

_ALIASES: dict[str, str] = {
    "normal": NORMAL,
    "normal_day": NORMAL,
    "default": NORMAL,
    "": NORMAL,
    "heat_wave": HEAT,
    "heatwave": HEAT,
    "monsoon": MONSOON,
    "monsoon_disruption": MONSOON,
    "capacity_stress": NORMAL,
    "live_weather": LIVE,
    "live": LIVE,
    "real_time": LIVE,
    "realtime": LIVE,
    "real_time_weather": LIVE,
}

_TEMP_RE = re.compile(r"temp(?:_moderate)?=([\d.]+)\s*C", re.IGNORECASE)
_RAIN_RE = re.compile(r"rain=([\d.]+)\s*mm", re.IGNORECASE)


def normalize_scenario_type(scenario_type: str | None) -> str:
    key = (scenario_type or "").strip().lower()
    return _ALIASES.get(key, key if key in _CANONICAL else NORMAL)


def is_live_scenario(scenario_type: str | None) -> bool:
    return normalize_scenario_type(scenario_type) == LIVE


def _event_get(event: WeatherEventLike | None, key: str, default: Any = None) -> Any:
    """Read a field from a WeatherEvent or LangGraph-serialized dict."""
    if event is None:
        return default
    if isinstance(event, dict):
        return event.get(key, default)
    return getattr(event, key, default)


def coerce_weather_event(event: WeatherEventLike | None) -> WeatherEvent | None:
    """Rehydrate LangGraph-serialized dicts into WeatherEvent models."""
    if event is None:
        return None
    if isinstance(event, dict):
        return WeatherEvent.model_validate(event)
    return event


def coerce_weather_events(
    events: list[WeatherEventLike] | None,
) -> list[WeatherEvent]:
    if not events:
        return []
    out: list[WeatherEvent] = []
    for event in events:
        coerced = coerce_weather_event(event)
        if coerced is not None:
            out.append(coerced)
    return out


def readings_from_event(event: WeatherEventLike | None) -> tuple[float, float]:
    """Parse rain (mm) and temp (C) from a weather event description / precip field."""
    if event is None:
        return 0.0, 28.0
    desc = str(_event_get(event, "description") or "")
    precip = float(_event_get(event, "precipitation_mm") or 0.0)
    rain_m = _RAIN_RE.search(desc)
    rain = float(rain_m.group(1)) if rain_m else precip
    temp_m = _TEMP_RE.search(desc)
    temp = float(temp_m.group(1)) if temp_m else 28.0
    return rain, temp


def live_stress_kind(rain_mm: float, temp_c: float) -> str:
    """Map live readings to the nearest template stress profile for downstream factors."""
    if temp_c >= 38.0:
        return HEAT
    if rain_mm > 20.0:
        return MONSOON
    return NORMAL


def live_stress_kind_from_event(event: WeatherEventLike | None) -> str:
    rain, temp = readings_from_event(event)
    return live_stress_kind(rain, temp)


def is_monsoon_high_risk_farm(farm: Farm) -> bool:
    """Western Ghats / coastal belt — heavier monsoon exposure in demo geography."""
    return farm.lng < 76.2 or farm.lat < 13.4


def shelf_life_factor(
    scenario_type: str | None,
    *,
    event: WeatherEventLike | None = None,
) -> float:
    """Multiplier on base shelf-life days (lower = faster spoilage)."""
    st = normalize_scenario_type(scenario_type)
    if st == LIVE:
        st = live_stress_kind_from_event(event)
    if st == HEAT:
        return 0.60  # 40% reduction
    if st == MONSOON:
        return 0.80  # 20% humidity spoilage reduction
    return 1.0


def travel_time_multiplier(
    scenario_type: str | None,
    *,
    events: list[WeatherEventLike] | None = None,
) -> float:
    """Extra road delay factor for monsoon-affected legs."""
    st = normalize_scenario_type(scenario_type)
    if st == LIVE and events:
        if any(live_stress_kind_from_event(e) == MONSOON for e in events):
            return 1.3
        return 1.0
    if st == MONSOON:
        return 1.3
    return 1.0


def market_absorption_factor(
    scenario_type: str | None,
    *,
    events: list[WeatherEventLike] | None = None,
) -> float:
    """Effective mandi daily demand under scenario stress (KPI demand-cap)."""
    st = normalize_scenario_type(scenario_type)
    if st == LIVE and events:
        kinds = {live_stress_kind_from_event(e) for e in events}
        if MONSOON in kinds:
            return 0.82
        if HEAT in kinds:
            return 0.94
        return 1.0
    if st == MONSOON:
        return 0.82
    if st == HEAT:
        return 0.94
    return 1.0


def apply_live_weather_matrix(
    matrix: list[list[float]],
    farms: list[Farm],
    events: list[WeatherEventLike],
) -> list[list[float]]:
    """Apply monsoon / heat matrix tweaks when live readings warrant it."""
    out = matrix
    if any(live_stress_kind_from_event(e) == MONSOON for e in events):
        out = apply_monsoon_distance_matrix(out, farms)
    if any(live_stress_kind_from_event(e) == HEAT for e in events):
        risk_hours = {f.id: 96.0 for f in farms}
        out = apply_heat_wave_morning_bias(out, farms, risk_hours)
    return out


def naive_coordination_penalty(
    scenario_type: str | None,
    *,
    at_risk_count: int = 0,
    events: list[WeatherEventLike] | None = None,
) -> float:
    """Extra naive-routing waste from uncoordinated farm→mandi trips under stress."""
    st = normalize_scenario_type(scenario_type)
    if st == LIVE and events:
        kinds = {live_stress_kind_from_event(e) for e in events}
        if HEAT in kinds:
            st = HEAT
        elif MONSOON in kinds:
            st = MONSOON
        else:
            st = NORMAL
    penalty = 1.05
    if st == HEAT:
        penalty += (1.0 - shelf_life_factor(st)) * 1.15
    elif st == MONSOON:
        penalty += (travel_time_multiplier(st) - 1.0) * 0.85
    else:
        congestion = min(0.42, max(0.15, at_risk_count * 0.018))
        penalty += congestion
    return penalty


def scenario_adjustment_details(
    *,
    scenario_type: str,
    weather_fetch_meta: dict | None = None,
    retry_count: int = 0,
    demand_scale: float | None = None,
) -> dict[str, float | str | int | None]:
    """Structured scenario knobs for agent trace `details` blocks."""
    raw = (scenario_type or "").strip().lower()
    st = normalize_scenario_type(scenario_type)
    out: dict[str, float | str | int | None] = {
        "scenario_type_raw": raw or st,
        "scenario_type_normalized": st,
        "shelf_life_factor": shelf_life_factor(scenario_type),
        "travel_time_multiplier": travel_time_multiplier(scenario_type),
        "market_absorption_factor": market_absorption_factor(scenario_type),
    }
    if weather_fetch_meta:
        out["weather_source"] = weather_fetch_meta.get("weather_source")
    if retry_count:
        out["retry_count"] = retry_count
    if demand_scale is not None:
        out["demand_scale"] = demand_scale
    return out


def scenario_trace_note(scenario_type: str | None) -> str:
    raw = (scenario_type or "").strip().lower()
    if raw == "capacity_stress":
        return (
            "Scenario: capacity_stress demo — undersized truck fleet triggers validator "
            "retry loop; weather/shelf effects = normal_day."
        )
    st = normalize_scenario_type(scenario_type)
    notes = {
        NORMAL: "Scenario: normal_day — applied specific adjustments (mild weather, baseline shelf life, standard routing).",
        HEAT: "Scenario: heat_wave — applied specific adjustments (temp >38°C, shelf life −40%, morning-delivery route bias).",
        MONSOON: "Scenario: monsoon_disruption — applied specific adjustments (high-risk zone rain >25mm, shelf life −20%, travel ×1.3 on affected roads).",
        LIVE: (
            "Scenario: live_weather — OpenWeather readings per farm (no scripted overlay); "
            "shelf life and routing stress derived from observed rain/temp thresholds."
        ),
    }
    return notes.get(st, f"Scenario: {st} — applied specific adjustments.")


def apply_monsoon_distance_matrix(
    matrix: list[list[float]],
    farms: list[Farm],
) -> list[list[float]]:
    """Scale legs through monsoon high-risk nodes by travel_time_multiplier (1.3)."""
    mult = travel_time_multiplier(MONSOON)
    n = len(matrix)
    nf = len(farms)
    high_risk = {i + 1 for i, f in enumerate(farms) if is_monsoon_high_risk_farm(f)}
    out = [row[:] for row in matrix]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if i in high_risk or j in high_risk:
                out[i][j] *= mult
    return out


def apply_heat_wave_morning_bias(
    matrix: list[list[float]],
    farms: list[Farm],
    at_risk_hours: dict[str, float],
) -> list[list[float]]:
    """Prefer early farm→mandi legs for urgent stock (morning delivery bias)."""
    n = len(matrix)
    nf = len(farms)
    out = [row[:] for row in matrix]
    for i in range(1, nf + 1):
        farm_id = farms[i - 1].id
        hours = at_risk_hours.get(farm_id, 120.0)
        urgency = max(0.0, min(1.0, (72.0 - hours) / 72.0))
        mandi_discount = 1.0 - 0.18 * urgency
        for j in range(nf + 1, n):
            out[i][j] *= mandi_discount
        for k in range(1, nf + 1):
            if k != i:
                out[i][k] *= 1.0 + 0.12 * urgency
    return out
