"""OpenWeatherMap free-tier weather + Redis cache with scenario overlays.

Scenario overlays (applied after live/synthetic readings):
  normal_day          — rain=0, moderate temp (~28°C), all farms risk=normal
  heat_wave           — temp >38°C, heat_wave flag, risk floor=warning
  monsoon_disruption  — high-risk zone farms rain>25mm, warning or severe
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from typing import Any

import httpx
import redis.asyncio as redis

from config import get_settings
from models.schemas import Farm, WeatherEvent
from tools.scenario_effects import (
    HEAT,
    MONSOON,
    NORMAL,
    is_monsoon_high_risk_farm,
    normalize_scenario_type,
)

logger = logging.getLogger(__name__)

_REDIS: redis.Redis | None = None

WEATHER_CACHE_PREFIX = "weather2:"
WEATHER_CACHE_TTL_S = 1200
OW_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OW_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

_OWM_SEMAPHORE = asyncio.Semaphore(10)

_NORMAL_TEMP_C = 28.0
_HEAT_WAVE_TEMP_C = 39.0
_MONSOON_RAIN_MM = 28.0


async def _redis_client() -> redis.Redis:
    """Lazy singleton Redis client (shared across fetch_weather calls)."""
    global _REDIS
    if _REDIS is None:
        _REDIS = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _REDIS


def _cache_key(lat: float, lng: float, endpoint: str) -> str:
    tag = "cur" if "weather" in endpoint and "forecast" not in endpoint else "fct"
    return f"{WEATHER_CACHE_PREFIX}{lat:.4f}:{lng:.4f}:{tag}"


def _scenario_adjustment_label(scenario: str) -> str | None:
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
        logger.warning("weather: both endpoints failed for farm %s — scenario overlay", farm.id)
        event = _event_from_readings(
            farm, 0.0, _NORMAL_TEMP_C, scenario_type=scenario_type,
        )
        return event, {
            "farm_id": farm.id,
            "api_used": False,
            "base_rain_mm": 0.0,
            "base_temp_c": _NORMAL_TEMP_C,
            "adjusted_rain_mm": event.precipitation_mm,
            "adjusted_temp_c": _parse_temp_from_desc(event.description) or _NORMAL_TEMP_C,
        }

    cur_rain, cur_temp, humidity_pct, wind_speed_ms = (
        _parse_current(cur_payload) if cur_payload else (0.0, 0.0, None, None)
    )
    fct_rain, fct_temp = _parse_forecast_24h(fct_payload) if fct_payload else (0.0, 0.0)

    base_rain = max(cur_rain, fct_rain)
    base_temp = max(cur_temp, fct_temp)
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

    return event, {
        "farm_id": farm.id,
        "api_used": True,
        "base_rain_mm": round(base_rain, 1),
        "base_temp_c": round(base_temp, 1),
        "adjusted_rain_mm": float(event.precipitation_mm or 0),
        "adjusted_temp_c": round(adj_temp, 1),
        "humidity_pct": humidity_pct,
        "wind_speed_ms": wind_speed_ms,
    }


def _parse_temp_from_desc(desc: str) -> float | None:
    import re
    m = re.search(r"temp(?:_moderate)?=([\d.]+)\s*C", desc, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"temp=([\d.]+)C", desc)
    return float(m.group(1)) if m else None


def _aggregate_farm_meta(farm_meta: list[dict[str, Any]], scenario: str) -> dict[str, Any]:
    api_count = sum(1 for m in farm_meta if m.get("api_used"))
    total = len(farm_meta) or 1

    if api_count == 0:
        weather_source = "synthetic_fallback"
    elif api_count == total:
        weather_source = "openweather"
    else:
        weather_source = "mixed"

    scenario_modifier_applied = weather_source == "synthetic_fallback" or any(
        abs(float(m.get("adjusted_rain_mm") or 0) - float(m.get("base_rain_mm") or 0)) > 0.05
        or abs(float(m.get("adjusted_temp_c") or 0) - float(m.get("base_temp_c") or 0)) > 0.05
        for m in farm_meta
    )

    base_temps = [m["base_temp_c"] for m in farm_meta if m.get("api_used")]
    base_rains = [m["base_rain_mm"] for m in farm_meta if m.get("api_used")]
    adj_temps = [m["adjusted_temp_c"] for m in farm_meta]
    adj_rains = [m["adjusted_rain_mm"] for m in farm_meta]
    humidities = [m["humidity_pct"] for m in farm_meta if m.get("humidity_pct") is not None]
    winds = [m["wind_speed_ms"] for m in farm_meta if m.get("wind_speed_ms") is not None]

    def _avg(vals: list[float]) -> float | None:
        return round(sum(vals) / len(vals), 1) if vals else None

    meta: dict[str, Any] = {
        "weather_source": weather_source,
        "scenario_modifier_applied": scenario_modifier_applied,
        "scenario_type": scenario,
        "scenario_adjustment_label": _scenario_adjustment_label(scenario),
        "farms_with_live_api": api_count,
        "farms_total": total,
    }

    if weather_source == "synthetic_fallback":
        meta["synthetic_reason"] = (
            "OPENWEATHER_API_KEY not configured or all API calls failed"
        )
    elif weather_source == "mixed":
        meta["synthetic_reason"] = (
            f"{total - api_count} farm(s) used scenario fallback after API failure"
        )

    if base_temps and scenario_modifier_applied and weather_source in ("openweather", "mixed"):
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
            "OPENWEATHER_API_KEY missing; using scenario overlays for all farms (scenario=%s)",
            st,
        )
        events = [
            _event_from_readings(f, 0.0, _NORMAL_TEMP_C, scenario_type=scenario_type)
            for f in farms
        ]
        farm_meta = [
            {
                "farm_id": f.id,
                "api_used": False,
                "base_rain_mm": 0.0,
                "base_temp_c": _NORMAL_TEMP_C,
                "adjusted_rain_mm": float(e.precipitation_mm or 0),
                "adjusted_temp_c": _parse_temp_from_desc(e.description) or _NORMAL_TEMP_C,
            }
            for f, e in zip(farms, events)
        ]
        meta = _aggregate_farm_meta(farm_meta, st)
        meta["synthetic_reason"] = "OPENWEATHER_API_KEY is not configured"
        return {"events": events, "meta": meta}

    r = await _redis_client()
    try:
        async with httpx.AsyncClient() as http:
            tasks = [
                _fetch_farm_readings(farm, api_key, r, http, scenario_type)
                for farm in farms
            ]
            pairs = await asyncio.gather(*tasks)
    except Exception as exc:  # noqa: BLE001
        logger.error("fetch_weather: unexpected error — scenario overlay fallback: %s", exc)
        events = [
            _event_from_readings(f, 0.0, _NORMAL_TEMP_C, scenario_type=scenario_type)
            for f in farms
        ]
        farm_meta = [
            {
                "farm_id": f.id,
                "api_used": False,
                "base_rain_mm": 0.0,
                "base_temp_c": _NORMAL_TEMP_C,
                "adjusted_rain_mm": float(e.precipitation_mm or 0),
                "adjusted_temp_c": _parse_temp_from_desc(e.description) or _NORMAL_TEMP_C,
            }
            for f, e in zip(farms, events)
        ]
        meta = _aggregate_farm_meta(farm_meta, st)
        meta["synthetic_reason"] = f"Unexpected fetch error: {exc}"
        return {"events": events, "meta": meta}

    events = [p[0] for p in pairs]
    farm_meta = [p[1] for p in pairs]
    meta = _aggregate_farm_meta(farm_meta, st)
    return {"events": events, "meta": meta}
