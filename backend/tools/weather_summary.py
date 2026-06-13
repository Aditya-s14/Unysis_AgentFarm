"""Build a compact weather_summary payload for the API / dashboard."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from models.schemas import Farm, WeatherEvent
from tools.scenario_effects import (
    HEAT,
    LIVE,
    MONSOON,
    NORMAL,
    live_stress_kind,
    normalize_scenario_type,
    readings_from_event,
)

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


def _condition_label(scenario: str, events: list | None = None) -> str:
    if scenario == LIVE and events:
        kinds = set()
        for event in events:
            rain, temp = readings_from_event(event)
            kinds.add(live_stress_kind(rain, temp))
        if HEAT in kinds:
            return "heat_wave"
        if MONSOON in kinds:
            return "rain"
        return "sunny"
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

    if scenario == LIVE:
        return (
            "Routes use live OpenWeather readings per farm — allow extra time if rain or heat "
            "thresholds trigger warning/severe risk."
        )
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
    if scenario == LIVE:
        if risk_level == "High":
            return "Prioritize at-risk farms; adjust shelf-life and routing from live readings."
        return "Proceed using per-farm OpenWeather risk — no scripted overlay."
    if scenario == NORMAL:
        return "Proceed with standard dispatch windows."
    if scenario == HEAT:
        return "Dispatch perishables before noon; shelf life reduced ~40%."
    if scenario == MONSOON:
        if risk_level == "High":
            return "Reroute around flooded segments; prioritise covered storage."
        return "Stagger departures; confirm mandi access on rain-affected roads."
    return "Review farm-level risk before loading trucks."


def _serialize_event(event: WeatherEvent | dict[str, Any]) -> dict[str, Any]:
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    return dict(event)


def _event_severity(event: WeatherEvent | dict[str, Any]) -> str:
    if isinstance(event, dict):
        return str(event.get("severity") or "normal")
    return str(getattr(event, "severity", None) or "normal")


def build_weather_snapshot(
    *,
    run_id: str,
    scenario_type: str,
    farms: list[Farm],
    weather_events: list[WeatherEvent | dict[str, Any]] | None = None,
    weather_risk_summary: dict[str, str] | None = None,
    weather_fetch_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full OpenWeather payload for persistence, advisor context, and API consumers."""
    events = list(weather_events or [])
    risk_summary = dict(weather_risk_summary or {})
    meta = dict(weather_fetch_meta or {})
    farm_meta_by_id = {
        str(m.get("farm_id")): m
        for m in (meta.get("farm_readings") or [])
        if m.get("farm_id")
    }

    farm_readings: list[dict[str, Any]] = []
    for farm, event in zip(farms, events):
        event_data = _serialize_event(event)
        fm = dict(farm_meta_by_id.get(farm.id) or {})
        rain, temp = readings_from_event(event)
        farm_readings.append(
            {
                "farm_id": farm.id,
                "farm_name": farm.name,
                "lat": round(farm.lat, 4),
                "lng": round(farm.lng, 4),
                "crop_type": farm.crop_type,
                "severity": risk_summary.get(farm.id) or _event_severity(event),
                "description": event_data.get("description") or "",
                "precipitation_mm": event_data.get("precipitation_mm"),
                "temp_c": round(temp, 1),
                "rain_mm": round(rain, 1),
                "base_temp_c": fm.get("base_temp_c"),
                "base_rain_mm": fm.get("base_rain_mm"),
                "adjusted_temp_c": fm.get("adjusted_temp_c"),
                "adjusted_rain_mm": fm.get("adjusted_rain_mm"),
                "humidity_pct": fm.get("humidity_pct"),
                "wind_speed_ms": fm.get("wind_speed_ms"),
                "api_used": bool(fm.get("api_used", meta.get("weather_source") == "openweather")),
                "stale_reading": bool(fm.get("stale_reading")),
                "reading_fetched_at": fm.get("reading_fetched_at"),
                "weather_disclaimer": fm.get("weather_disclaimer"),
            }
        )

    summary = build_weather_summary(
        scenario_type=scenario_type,
        farms=farms,
        weather_events=events,
        weather_risk_summary=risk_summary,
        weather_fetch_meta=meta,
    )

    return {
        "run_id": run_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "scenario_type": normalize_scenario_type(scenario_type),
        "weather_source": meta.get("weather_source") or summary.get("weather_source"),
        "summary": summary,
        "farm_readings": farm_readings,
        "weather_risk_summary": risk_summary,
        "weather_events": [_serialize_event(e) for e in events],
        "fetch_meta": meta,
    }


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
    if scenario == LIVE and rain_mm > 0:
        rainfall_probability_pct = min(95.0, 40.0 + rain_mm * 1.5)
    elif scenario == MONSOON and rain_mm > 0:
        rainfall_probability_pct = min(95.0, 55.0 + rain_mm * 1.2)
    elif scenario == NORMAL:
        rainfall_probability_pct = 5.0

    summary: dict[str, Any] = {
        "condition": _condition_label(scenario, events),
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
        if meta.get("weather_disclaimer"):
            summary["weather_disclaimer"] = meta["weather_disclaimer"]
        if meta.get("stale_reading"):
            summary["stale_reading"] = True
        if meta.get("reading_fetched_at"):
            summary["reading_fetched_at"] = meta["reading_fetched_at"]
        if meta.get("fallback_mode"):
            summary["fallback_mode"] = meta["fallback_mode"]
        if meta.get("farms_with_stale_cache") is not None:
            summary["farms_with_stale_cache"] = meta["farms_with_stale_cache"]
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
