"""Build a compact weather_summary payload for the API / dashboard."""

from __future__ import annotations

import re
from typing import Any

from models.schemas import Farm, WeatherEvent
from tools.scenario_effects import HEAT, MONSOON, NORMAL, normalize_scenario_type

_TEMP_RE = re.compile(r"temp(?:_moderate)?=([\d.]+)\s*C", re.IGNORECASE)
_RAIN_RE = re.compile(r"rain=([\d.]+)\s*mm", re.IGNORECASE)


def _event_desc(event: WeatherEvent | dict[str, Any]) -> str:
    if isinstance(event, dict):
        return str(event.get("description") or "")
    return str(getattr(event, "description", "") or "")


def _event_precip(event: WeatherEvent | dict[str, Any]) -> float:
    if isinstance(event, dict):
        return float(event.get("precipitation_mm") or 0.0)
    return float(getattr(event, "precipitation_mm", None) or 0.0)


def _parse_temp(desc: str) -> float | None:
    m = _TEMP_RE.search(desc)
    return float(m.group(1)) if m else None


def _parse_rain(desc: str, precip: float) -> float:
    m = _RAIN_RE.search(desc)
    if m:
        return float(m.group(1))
    return precip


def _condition_label(scenario: str) -> str:
    if scenario == HEAT:
        return "heat_wave"
    if scenario == MONSOON:
        return "rain"
    return "sunny"


def _risk_level(scenario: str, risk_summary: dict[str, str]) -> str:
    severe = sum(1 for v in risk_summary.values() if v == "severe")
    warning = sum(1 for v in risk_summary.values() if v == "warning")
    if scenario == HEAT or severe >= 3:
        return "High"
    if scenario == MONSOON or severe > 0 or warning >= 4:
        return "Moderate"
    if warning > 0:
        return "Moderate"
    return "Low"


def _transport_advisory(scenario: str, farms: list[Farm]) -> str:
    bengaluru_farms = [f for f in farms if 12.5 <= f.lat <= 14.0 and 77.0 <= f.lng <= 78.5]
    has_cluster = len(bengaluru_farms) >= 2

    if scenario == NORMAL:
        return "No weather-related transport delays expected."
    if scenario == HEAT:
        if has_cluster:
            return "Afternoon heat on Bengaluru–Kolar corridor — prefer morning legs."
        return "High temperatures region-wide — schedule pickups before noon."
    if scenario == MONSOON:
        if has_cluster:
            return "Delays possible on Bengaluru–Kolar route; allow extra road time."
        return "Heavy rain in western/coastal belts — verify NH legs before dispatch."
    return "Monitor regional forecasts before dispatch."


def _recommended_action(scenario: str, risk_level: str) -> str:
    if scenario == NORMAL:
        return "Proceed with standard dispatch windows."
    if scenario == HEAT:
        return "Dispatch perishables before noon; shelf life reduced ~40%."
    if scenario == MONSOON:
        if risk_level == "High":
            return "Reroute around flooded segments; prioritise covered storage."
        return "Stagger departures; confirm mandi access on rain-affected roads."
    return "Review farm-level risk before loading trucks."


def build_weather_summary(
    *,
    scenario_type: str,
    farms: list[Farm],
    weather_events: list[WeatherEvent | dict[str, Any]] | None = None,
    weather_risk_summary: dict[str, str] | None = None,
    weather_fetch_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate pipeline weather state into a dashboard-friendly summary."""
    scenario = normalize_scenario_type(scenario_type)
    events = weather_events or []
    risk_summary = dict(weather_risk_summary or {})
    farm_by_id = {f.id: f for f in farms}

    temps: list[float] = []
    rains: list[float] = []
    for farm, event in zip(farms, events):
        desc = _event_desc(event)
        precip = _event_precip(event)
        t = _parse_temp(desc)
        if t is not None:
            temps.append(t)
        rains.append(_parse_rain(desc, precip))

    if temps:
        temp_c = round(sum(temps) / len(temps), 1)
    elif scenario == HEAT:
        temp_c = 39.0
    elif scenario == NORMAL:
        temp_c = 28.0
    else:
        temp_c = 27.0

    rain_mm = round(max(rains) if rains else 0.0, 1)
    risk_level = _risk_level(scenario, risk_summary)

    affected_names: list[str] = []
    for farm_id, level in risk_summary.items():
        if level in ("warning", "severe"):
            farm = farm_by_id.get(farm_id)
            if farm:
                affected_names.append(farm.name)

    rainfall_probability_pct: float | None = None
    if scenario == MONSOON and rain_mm > 0:
        rainfall_probability_pct = min(95.0, 55.0 + rain_mm * 1.2)
    elif scenario == NORMAL:
        rainfall_probability_pct = 5.0

    summary: dict[str, Any] = {
        "condition": _condition_label(scenario),
        "temperature_c": temp_c,
        "rainfall_mm": rain_mm,
        "rainfall_probability_pct": rainfall_probability_pct,
        "risk_level": risk_level,
        "affected_farms": affected_names,
        "transport_advisory": _transport_advisory(scenario, farms),
        "recommended_action": _recommended_action(scenario, risk_level),
        "scenario_type": scenario,
    }

    meta = dict(weather_fetch_meta or {})
    if meta:
        summary["weather_source"] = meta.get("weather_source", "synthetic_fallback")
        summary["scenario_modifier_applied"] = bool(meta.get("scenario_modifier_applied", True))
        if meta.get("scenario_adjustment_label"):
            summary["scenario_adjustment_label"] = meta["scenario_adjustment_label"]
        if meta.get("synthetic_reason"):
            summary["synthetic_reason"] = meta["synthetic_reason"]
        if meta.get("temperature_c_base") is not None:
            summary["temperature_c_base"] = meta["temperature_c_base"]
        if meta.get("rainfall_mm_base") is not None:
            summary["rainfall_mm_base"] = meta["rainfall_mm_base"]
        if meta.get("humidity_pct") is not None:
            summary["humidity_pct"] = meta["humidity_pct"]
        if meta.get("wind_speed_ms") is not None:
            summary["wind_speed_ms"] = meta["wind_speed_ms"]
        summary["farms_with_live_api"] = meta.get("farms_with_live_api", 0)
        summary["farms_total"] = meta.get("farms_total", len(farms))
    else:
        summary["weather_source"] = "synthetic_fallback"
        summary["scenario_modifier_applied"] = True
        summary["synthetic_reason"] = "Weather fetch metadata unavailable"

    return summary
