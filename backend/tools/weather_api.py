"""OpenWeatherMap free-tier weather + Redis cache with scenario overlays.

When OpenWeather is unavailable, all farms fall back to **live_weather rules**
(baseline 0 mm / 28°C, live thresholds — no scripted heat/monsoon overlay).

Scripted overlays (only when API data is present):
  normal_day          — rain=0, moderate temp (~28°C), all farms risk=normal
  heat_wave           — temp >38°C, heat_wave flag, risk floor=warning
  monsoon_disruption  — high-risk zone farms rain>25mm, warning or severe
  live_weather        — no overlay; classify from observed readings only
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timezone
from typing import Any

import httpx
import redis.asyncio as redis

from config import get_settings
from models.schemas import Farm, WeatherEvent
from tools.scenario_effects import (
    HEAT,
    LIVE,
    MONSOON,
    NORMAL,
    is_monsoon_high_risk_farm,
    normalize_scenario_type,
)

logger = logging.getLogger(__name__)

_REDIS: redis.Redis | None = None

WEATHER_CACHE_PREFIX = "weather2:"
WEATHER_CACHE_TTL_S = 1200
WEATHER_LAST_GOOD_PREFIX = "weather2:last:"
WEATHER_LAST_GOOD_TTL_S = 7 * 24 * 3600
STALE_READING_DISCLAIMER = (
    "Couldn't fetch the current weather update; showing the most recently fetched reading."
)
OW_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OW_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

_OWM_SEMAPHORE = asyncio.Semaphore(10)

_NORMAL_TEMP_C = 28.0
_HEAT_WAVE_TEMP_C = 39.0
_MONSOON_RAIN_MM = 28.0

# Sensor / API reading sanity bounds (India-relevant ambient range).
_MIN_TEMP_C = -10.0
_MAX_TEMP_C = 55.0
_MAX_RAIN_MM = 500.0
_REJECT_TEMP_BELOW = -50.0
_REJECT_TEMP_ABOVE = 80.0
_REJECT_RAIN_ABOVE = 1000.0


def sanitize_sensor_readings(
    rain_mm: float,
    temp_c: float,
) -> tuple[float, float, str]:
    """Validate and clamp weather readings.

    Returns ``(rain_mm, temp_c, quality)`` where quality is one of
    ``ok``, ``clamped``, or ``rejected`` (caller should use live_weather fallback).
    """
    if (
        temp_c < _REJECT_TEMP_BELOW
        or temp_c > _REJECT_TEMP_ABOVE
        or rain_mm < 0
        or rain_mm > _REJECT_RAIN_ABOVE
    ):
        return 0.0, _NORMAL_TEMP_C, "rejected"

    clamped = False
    if rain_mm > _MAX_RAIN_MM:
        rain_mm = _MAX_RAIN_MM
        clamped = True
    if temp_c < _MIN_TEMP_C:
        temp_c = _MIN_TEMP_C
        clamped = True
    if temp_c > _MAX_TEMP_C:
        temp_c = _MAX_TEMP_C
        clamped = True

    return rain_mm, temp_c, "clamped" if clamped else "ok"


def _live_weather_fallback_event(farm: Farm) -> WeatherEvent:
    """Build a per-farm event using live_weather classification (no scripted overlay)."""
    return _event_from_readings(farm, 0.0, _NORMAL_TEMP_C, scenario_type=LIVE)


def _live_weather_fallback_farm_meta(
    farm: Farm,
    event: WeatherEvent,
    *,
    data_quality: str | None = None,
    humidity_pct: float | None = None,
    wind_speed_ms: float | None = None,
) -> dict[str, Any]:
    """Farm meta row when OpenWeather was not used — live_weather fallback rules."""
    meta: dict[str, Any] = {
        "farm_id": farm.id,
        "api_used": False,
        "fallback_mode": "live_weather",
        "base_rain_mm": 0.0,
        "base_temp_c": _NORMAL_TEMP_C,
        "adjusted_rain_mm": float(event.precipitation_mm or 0),
        "adjusted_temp_c": _parse_temp_from_desc(event.description) or _NORMAL_TEMP_C,
        "severity": event.severity,
        "description": event.description,
        "precipitation_mm": float(event.precipitation_mm or 0),
    }
    if data_quality:
        meta["data_quality"] = data_quality
    if humidity_pct is not None:
        meta["humidity_pct"] = humidity_pct
    if wind_speed_ms is not None:
        meta["wind_speed_ms"] = wind_speed_ms
    return meta


def _live_weather_fallback_batch(
    farms: list[Farm],
    *,
    requested_scenario: str,
    synthetic_reason: str,
) -> tuple[list[WeatherEvent], dict[str, Any]]:
    """All-farm fallback: live_weather rules, effective scenario = live_weather."""
    events = [_live_weather_fallback_event(f) for f in farms]
    farm_meta = [_live_weather_fallback_farm_meta(f, e) for f, e in zip(farms, events)]
    meta = _aggregate_farm_meta(farm_meta, requested_scenario)
    meta["synthetic_reason"] = synthetic_reason
    return events, meta


async def _redis_client() -> redis.Redis:
    """Lazy singleton Redis client (shared across fetch_weather calls)."""
    global _REDIS
    if _REDIS is None:
        _REDIS = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _REDIS


def _cache_key(lat: float, lng: float, endpoint: str) -> str:
    tag = "cur" if "weather" in endpoint and "forecast" not in endpoint else "fct"
    return f"{WEATHER_CACHE_PREFIX}{lat:.4f}:{lng:.4f}:{tag}"


def _last_good_key(lat: float, lng: float) -> str:
    return f"{WEATHER_LAST_GOOD_PREFIX}{lat:.4f}:{lng:.4f}"


async def _save_last_good_reading(
    r: redis.Redis,
    farm: Farm,
    *,
    base_rain_mm: float,
    base_temp_c: float,
    humidity_pct: float | None = None,
    wind_speed_ms: float | None = None,
) -> None:
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "base_rain_mm": round(base_rain_mm, 2),
        "base_temp_c": round(base_temp_c, 2),
        "humidity_pct": humidity_pct,
        "wind_speed_ms": wind_speed_ms,
    }
    try:
        await r.set(
            _last_good_key(farm.lat, farm.lng),
            json.dumps(payload),
            ex=WEATHER_LAST_GOOD_TTL_S,
        )
    except Exception:
        pass


async def _load_last_good_reading(
    r: redis.Redis,
    farm: Farm,
) -> dict[str, Any] | None:
    try:
        raw = await r.get(_last_good_key(farm.lat, farm.lng))
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def _stale_cache_fallback_farm_meta(
    farm: Farm,
    event: WeatherEvent,
    *,
    base_rain_mm: float,
    base_temp_c: float,
    reading_fetched_at: str,
    data_quality: str = "stale_cache",
    humidity_pct: float | None = None,
    wind_speed_ms: float | None = None,
) -> dict[str, Any]:
    adj_temp = _parse_temp_from_desc(event.description) or base_temp_c
    return {
        "farm_id": farm.id,
        "api_used": False,
        "fallback_mode": "stale_cache",
        "stale_reading": True,
        "reading_fetched_at": reading_fetched_at,
        "weather_disclaimer": STALE_READING_DISCLAIMER,
        "data_quality": data_quality,
        "base_rain_mm": round(base_rain_mm, 1),
        "base_temp_c": round(base_temp_c, 1),
        "adjusted_rain_mm": float(event.precipitation_mm or 0),
        "adjusted_temp_c": round(adj_temp, 1),
        "severity": event.severity,
        "description": event.description,
        "precipitation_mm": float(event.precipitation_mm or 0),
        "humidity_pct": humidity_pct,
        "wind_speed_ms": wind_speed_ms,
    }


async def _try_stale_cache_fallback(
    farm: Farm,
    r: redis.Redis,
    scenario_type: str,
) -> tuple[WeatherEvent, dict[str, Any]] | None:
    """Use last successful OpenWeather reading when a fresh fetch is unavailable."""
    stored = await _load_last_good_reading(r, farm)
    if not stored:
        return None

    base_rain = float(stored.get("base_rain_mm") or 0.0)
    base_temp = float(stored.get("base_temp_c") or _NORMAL_TEMP_C)
    base_rain, base_temp, quality = sanitize_sensor_readings(base_rain, base_temp)
    if quality == "rejected":
        return None

    event = _event_from_readings(farm, base_rain, base_temp, scenario_type=scenario_type)
    logger.warning(
        "weather: farm=%s — stale cache fallback (fetched_at=%s)",
        farm.id,
        stored.get("fetched_at"),
    )
    return event, _stale_cache_fallback_farm_meta(
        farm,
        event,
        base_rain_mm=base_rain,
        base_temp_c=base_temp,
        reading_fetched_at=str(stored.get("fetched_at") or ""),
        data_quality=quality,
        humidity_pct=stored.get("humidity_pct"),
        wind_speed_ms=stored.get("wind_speed_ms"),
    )


def _scenario_adjustment_label(scenario: str) -> str | None:
    if scenario == LIVE:
        return None
    if scenario == HEAT:
        return "Heat wave overlay (temp ≥39°C)"
    if scenario == MONSOON:
        return "Monsoon disruption overlay (high-rain zones)"
    if scenario == NORMAL:
        return "Normal-day overlay (rain cleared, temp moderated)"
    return None


def _apply_scenario_readings(
    farm: Farm,
    max_rain_mm: float,
    max_temp_c: float,
    scenario_type: str,
) -> tuple[float, float]:
    st = normalize_scenario_type(scenario_type)

    if st == LIVE:
        return max_rain_mm, max_temp_c

    if st == NORMAL:
        return 0.0, _NORMAL_TEMP_C

    if st == HEAT:
        return max(0.0, max_rain_mm), max(max_temp_c, _HEAT_WAVE_TEMP_C)

    if st == MONSOON:
        if is_monsoon_high_risk_farm(farm):
            return max(max_rain_mm, _MONSOON_RAIN_MM), max_temp_c
        return max_rain_mm, max_temp_c

    return max_rain_mm, max_temp_c


def _classify_risk(
    farm: Farm,
    max_rain_mm: float,
    max_temp_c: float,
    *,
    scenario_type: str = "",
) -> tuple[str, str]:
    st = normalize_scenario_type(scenario_type)

    if st == NORMAL:
        return "normal", (
            f"normal_day; rain=0; temp_moderate={max_temp_c:.1f}C; risk=normal"
        )

    if st == HEAT:
        severity = "warning" if max_temp_c > 38 else "normal"
        desc_parts = [
            "heat_wave",
            f"temp={max_temp_c:.1f}C",
            f"rain={max_rain_mm:.1f}mm",
            f"risk={severity}",
        ]
        return severity, "; ".join(desc_parts)

    if st == MONSOON:
        if is_monsoon_high_risk_farm(farm) and max_rain_mm > 25:
            severity = "severe" if max_rain_mm > 40 else "warning"
        elif max_rain_mm > 50:
            severity = "severe"
        elif max_rain_mm > 20:
            severity = "warning"
        else:
            severity = "normal"
        zone = "high_risk_zone" if is_monsoon_high_risk_farm(farm) else "standard"
        return severity, (
            f"monsoon_disruption; zone={zone}; rain={max_rain_mm:.1f}mm; "
            f"temp={max_temp_c:.1f}C; risk={severity}"
        )

    if st == LIVE:
        if max_temp_c >= 40.0 or max_rain_mm > 50.0:
            severity = "severe"
        elif max_temp_c >= 38.0 or max_rain_mm > 20.0:
            severity = "warning"
        else:
            severity = "normal"
        return severity, (
            f"live_weather; rain={max_rain_mm:.1f}mm; temp={max_temp_c:.1f}C; risk={severity}"
        )

    if max_rain_mm > 50:
        severity = "severe"
    elif max_rain_mm > 20:
        severity = "warning"
    else:
        severity = "normal"
    return severity, (
        f"rain_risk={severity}; max_rain_next24h_mm~{max_rain_mm:.1f}; temp={max_temp_c:.1f}C"
    )


def _event_from_readings(
    farm: Farm,
    max_rain_mm: float,
    max_temp_c: float,
    *,
    scenario_type: str = "",
    today: date | None = None,
) -> WeatherEvent:
    d = today or date.today()
    rain, temp = _apply_scenario_readings(farm, max_rain_mm, max_temp_c, scenario_type)
    sev, desc = _classify_risk(farm, rain, temp, scenario_type=scenario_type)
    return WeatherEvent(
        id=f"wx-{farm.id}",
        event_date=d,
        region=farm.name,
        description=desc,
        severity=sev,
        precipitation_mm=round(rain, 2),
    )


def _parse_current(payload: dict[str, Any]) -> tuple[float, float, float | None, float | None]:
    main = payload.get("main") or {}
    wind = payload.get("wind") or {}
    temp = float(main.get("temp", 0.0))
    rain_obj = payload.get("rain") or {}
    rain = float(rain_obj.get("1h", rain_obj.get("3h", 0.0)))
    humidity = main.get("humidity")
    wind_speed = wind.get("speed")
    return (
        rain,
        temp,
        float(humidity) if humidity is not None else None,
        float(wind_speed) if wind_speed is not None else None,
    )


def _parse_forecast_24h(payload: dict[str, Any]) -> tuple[float, float]:
    flist = payload.get("list") or []
    max_rain = 0.0
    max_temp = 0.0
    for item in flist[:8]:
        main = item.get("main") or {}
        t = float(main.get("temp", 0.0))
        max_temp = max(max_temp, t)
        rain_obj = item.get("rain") or {}
        r = float(rain_obj.get("3h", 0.0))
        max_rain = max(max_rain, r)
    return max_rain, max_temp


async def _fetch_farm_readings(
    farm: Farm,
    api_key: str,
    r: redis.Redis,
    http: httpx.AsyncClient,
    scenario_type: str,
) -> tuple[WeatherEvent, dict[str, Any]]:
    cur_key = _cache_key(farm.lat, farm.lng, OW_CURRENT_URL)
    fct_key = _cache_key(farm.lat, farm.lng, OW_FORECAST_URL)
    params = {"lat": farm.lat, "lon": farm.lng, "appid": api_key, "units": "metric"}

    async def _get_or_fetch(url: str, cache_key: str) -> dict[str, Any] | None:
        try:
            raw = await r.get(cache_key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        async with _OWM_SEMAPHORE:
            try:
                resp = await http.get(url, params=params, timeout=20.0)
                resp.raise_for_status()
                data = resp.json()
                try:
                    await r.set(cache_key, json.dumps(data), ex=WEATHER_CACHE_TTL_S)
                except Exception:
                    pass
                return data
            except Exception as exc:
                logger.warning(
                    "Weather API call failed for farm %s (%s): %s",
                    farm.id,
                    url.split("/")[-1],
                    exc,
                )
                return None

    cur_payload, fct_payload = await asyncio.gather(
        _get_or_fetch(OW_CURRENT_URL, cur_key),
        _get_or_fetch(OW_FORECAST_URL, fct_key),
    )

    api_used = cur_payload is not None or fct_payload is not None
    humidity_pct: float | None = None
    wind_speed_ms: float | None = None

    if not api_used:
        stale = await _try_stale_cache_fallback(farm, r, scenario_type)
        if stale:
            return stale
        logger.warning(
            "weather: both endpoints failed for farm %s — live_weather fallback",
            farm.id,
        )
        event = _live_weather_fallback_event(farm)
        return event, _live_weather_fallback_farm_meta(farm, event)

    cur_rain, cur_temp, humidity_pct, wind_speed_ms = (
        _parse_current(cur_payload) if cur_payload else (0.0, 0.0, None, None)
    )
    fct_rain, fct_temp = _parse_forecast_24h(fct_payload) if fct_payload else (0.0, 0.0)

    base_rain = max(cur_rain, fct_rain)
    base_temp = max(cur_temp, fct_temp)
    base_rain, base_temp, data_quality = sanitize_sensor_readings(base_rain, base_temp)

    if data_quality == "rejected":
        stale = await _try_stale_cache_fallback(farm, r, scenario_type)
        if stale:
            return stale
        logger.warning(
            "weather: rejected outlier readings for farm %s — live_weather fallback",
            farm.id,
        )
        event = _live_weather_fallback_event(farm)
        return event, _live_weather_fallback_farm_meta(
            farm,
            event,
            data_quality="rejected",
            humidity_pct=humidity_pct,
            wind_speed_ms=wind_speed_ms,
        )

    await _save_last_good_reading(
        r,
        farm,
        base_rain_mm=base_rain,
        base_temp_c=base_temp,
        humidity_pct=humidity_pct,
        wind_speed_ms=wind_speed_ms,
    )

    event = _event_from_readings(farm, base_rain, base_temp, scenario_type=scenario_type)
    adj_temp = _parse_temp_from_desc(event.description) or base_temp

    st = normalize_scenario_type(scenario_type)
    logger.info(
        "weather: farm=%-20s base_rain=%.1fmm base_temp=%.1fC severity=%s scenario=%s api=openweather",
        farm.id,
        base_rain,
        base_temp,
        event.severity,
        st,
    )

    farm_meta: dict[str, Any] = {
        "farm_id": farm.id,
        "api_used": True,
        "data_quality": data_quality,
        "base_rain_mm": round(base_rain, 1),
        "base_temp_c": round(base_temp, 1),
        "adjusted_rain_mm": float(event.precipitation_mm or 0),
        "adjusted_temp_c": round(adj_temp, 1),
        "humidity_pct": humidity_pct,
        "wind_speed_ms": wind_speed_ms,
    }
    return event, farm_meta


def _parse_temp_from_desc(desc: str) -> float | None:
    import re
    m = re.search(r"temp(?:_moderate)?=([\d.]+)\s*C", desc, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"temp=([\d.]+)C", desc)
    return float(m.group(1)) if m else None


def _aggregate_farm_meta(farm_meta: list[dict[str, Any]], scenario: str) -> dict[str, Any]:
    api_count = sum(1 for m in farm_meta if m.get("api_used"))
    stale_count = sum(1 for m in farm_meta if m.get("fallback_mode") == "stale_cache")
    synthetic_count = sum(
        1 for m in farm_meta if m.get("fallback_mode") == "live_weather"
    )
    total = len(farm_meta) or 1

    if api_count == total:
        weather_source = "openweather"
    elif stale_count == total and api_count == 0:
        weather_source = "stale_cache"
    elif api_count == 0 and stale_count == 0:
        weather_source = "synthetic_fallback"
    else:
        weather_source = "mixed"

    scenario_modifier_applied = weather_source == "synthetic_fallback" or any(
        abs(float(m.get("adjusted_rain_mm") or 0) - float(m.get("base_rain_mm") or 0)) > 0.05
        or abs(float(m.get("adjusted_temp_c") or 0) - float(m.get("base_temp_c") or 0)) > 0.05
        for m in farm_meta
    )

    def _has_real_reading(m: dict[str, Any]) -> bool:
        return bool(m.get("api_used")) or m.get("fallback_mode") == "stale_cache"

    base_temps = [m["base_temp_c"] for m in farm_meta if _has_real_reading(m)]
    base_rains = [m["base_rain_mm"] for m in farm_meta if _has_real_reading(m)]
    adj_temps = [m["adjusted_temp_c"] for m in farm_meta]
    adj_rains = [m["adjusted_rain_mm"] for m in farm_meta]
    humidities = [m["humidity_pct"] for m in farm_meta if m.get("humidity_pct") is not None]
    winds = [m["wind_speed_ms"] for m in farm_meta if m.get("wind_speed_ms") is not None]

    def _avg(vals: list[float]) -> float | None:
        return round(sum(vals) / len(vals), 1) if vals else None

    requested = normalize_scenario_type(scenario)
    effective = requested
    if weather_source == "synthetic_fallback":
        effective = LIVE
        scenario_modifier_applied = False

    meta: dict[str, Any] = {
        "weather_source": weather_source,
        "scenario_modifier_applied": scenario_modifier_applied,
        "scenario_type": effective,
        "requested_scenario_type": requested,
        "effective_scenario_type": effective,
        "scenario_adjustment_label": _scenario_adjustment_label(effective),
        "farms_with_live_api": api_count,
        "farms_with_stale_cache": stale_count,
        "farms_total": total,
    }

    if weather_source == "synthetic_fallback":
        meta["fallback_mode"] = "live_weather"
        meta["synthetic_reason"] = (
            "OpenWeather unavailable — live_weather fallback "
            "(0 mm / 28°C baseline, live risk thresholds; no scripted overlay)"
        )
    elif weather_source == "stale_cache":
        meta["fallback_mode"] = "stale_cache"
        meta["stale_reading"] = True
        meta["weather_disclaimer"] = STALE_READING_DISCLAIMER
        fetched_times = [
            m.get("reading_fetched_at")
            for m in farm_meta
            if m.get("reading_fetched_at")
        ]
        if fetched_times:
            meta["reading_fetched_at"] = min(fetched_times)
    elif weather_source == "mixed":
        if stale_count > 0:
            meta["fallback_mode"] = "partial_stale_cache"
            parts: list[str] = []
            if stale_count:
                parts.append(
                    f"{stale_count} farm(s) showing cached readings (API unavailable)"
                )
            if synthetic_count:
                parts.append(
                    f"{synthetic_count} farm(s) using live_weather fallback (no cache)"
                )
            meta["weather_disclaimer"] = STALE_READING_DISCLAIMER
            meta["synthetic_reason"] = "; ".join(parts)
        else:
            meta["fallback_mode"] = "partial_live_weather"
            meta["synthetic_reason"] = (
                f"{total - api_count} farm(s) used live_weather fallback after API failure"
            )

    if base_temps and scenario_modifier_applied and weather_source in (
        "openweather",
        "mixed",
        "stale_cache",
    ):
        meta["temperature_c_base"] = _avg(base_temps)
        meta["rainfall_mm_base"] = round(max(base_rains), 1) if base_rains else 0.0

    if adj_temps:
        meta["temperature_c"] = _avg(adj_temps)
    if adj_rains:
        meta["rainfall_mm"] = round(max(adj_rains), 1)

    h = _avg(humidities)
    w = _avg(winds)
    if h is not None:
        meta["humidity_pct"] = h
    if w is not None:
        meta["wind_speed_ms"] = round(w, 1)

    meta["farm_readings"] = farm_meta
    return meta


async def fetch_weather(
    farms: list[Farm],
    *,
    scenario_type: str = "",
) -> dict[str, Any]:
    """Fetch weather per farm. Returns ``{events, meta}`` — never raises."""
    settings = get_settings()
    api_key = (settings.OPENWEATHER_API_KEY or "").strip()
    st = normalize_scenario_type(scenario_type)

    if not api_key:
        logger.info(
            "OPENWEATHER_API_KEY missing; live_weather fallback for all farms "
            "(requested scenario=%s)",
            st,
        )
        events, meta = _live_weather_fallback_batch(
            farms,
            requested_scenario=st,
            synthetic_reason="OPENWEATHER_API_KEY is not configured",
        )
        return {"events": events, "meta": meta}

    try:
        r = await _redis_client()
        async with httpx.AsyncClient() as http:
            tasks = [
                _fetch_farm_readings(farm, api_key, r, http, scenario_type)
                for farm in farms
            ]
            pairs = await asyncio.gather(*tasks)
    except Exception as exc:  # noqa: BLE001
        logger.error("fetch_weather: unexpected error — live_weather fallback: %s", exc)
        events, meta = _live_weather_fallback_batch(
            farms,
            requested_scenario=st,
            synthetic_reason=f"Unexpected fetch error: {exc}",
        )
        return {"events": events, "meta": meta}

    events = [p[0] for p in pairs]
    farm_meta = [p[1] for p in pairs]
    for fm, event in zip(farm_meta, events):
        fm["severity"] = event.severity
        fm["description"] = event.description
        fm["precipitation_mm"] = float(event.precipitation_mm or 0)
    meta = _aggregate_farm_meta(farm_meta, st)
    return {"events": events, "meta": meta}
