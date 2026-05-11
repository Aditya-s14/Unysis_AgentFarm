"""OpenWeatherMap forecast + Redis cache with deterministic fallback (never raises on API loss)."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import httpx
import redis.asyncio as redis

from config import get_settings
from models.schemas import Farm, WeatherEvent

logger = logging.getLogger(__name__)

WEATHER_CACHE_PREFIX = "weather:"
WEATHER_CACHE_TTL_S = 3600
OW_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def _weather_cache_key(lat: float, lng: float) -> str:
    return f"{WEATHER_CACHE_PREFIX}{lat:.4f}:{lng:.4f}"


def _classify_risk(max_rain_mm: float, max_temp_c: float) -> tuple[str, str]:
    """Rain severity; append heat_wave in description when temp > 40 °C."""
    if max_rain_mm > 50:
        rain_severity = "severe"
    elif max_rain_mm > 20:
        rain_severity = "warning"
    else:
        rain_severity = "normal"

    parts = [f"rain_risk={rain_severity}", f"max_rain_next24h_mm~{max_rain_mm:.1f}"]
    if max_temp_c > 40:
        parts.append("heat_wave")
    desc = "; ".join(parts)
    return rain_severity, desc


def _synthetic_event(farm: Farm, *, today: date | None = None) -> WeatherEvent:
    d = today or date.today()
    return WeatherEvent(
        id=f"fallback-{farm.id}",
        event_date=d,
        region=farm.name,
        description="synthetic mild conditions (API unavailable)",
        severity="normal",
        precipitation_mm=0.0,
    )


def _event_from_payload(
    farm: Farm,
    max_rain_mm: float,
    max_temp_c: float,
    *,
    today: date | None = None,
) -> WeatherEvent:
    d = today or date.today()
    sev, desc = _classify_risk(max_rain_mm, max_temp_c)
    return WeatherEvent(
        id=f"wx-{farm.id}",
        event_date=d,
        region=farm.name,
        description=desc,
        severity=sev,
        precipitation_mm=round(max_rain_mm, 2),
    )


def _aggregate_next_24h(forecast_list: list[dict[str, Any]]) -> tuple[float, float]:
    max_rain = 0.0
    max_temp = 0.0
    for item in forecast_list[:8]:
        main = item.get("main") or {}
        t = float(main.get("temp", 0.0))
        max_temp = max(max_temp, t)
        rain_obj = item.get("rain") or {}
        r3h = float(rain_obj.get("3h", 0.0))
        max_rain = max(max_rain, r3h)
    return max_rain, max_temp


async def _fetch_forecast_payload(
    lat: float,
    lng: float,
    api_key: str,
    *,
    client: httpx.AsyncClient,
) -> dict[str, Any]:
    params = {
        "lat": lat,
        "lon": lng,
        "appid": api_key,
        "units": "metric",
    }
    r = await client.get(OW_FORECAST_URL, params=params)
    r.raise_for_status()
    return r.json()


async def fetch_weather(farms: list[Farm]) -> list[WeatherEvent]:
    """
    One WeatherEvent per farm from OpenWeather 5-day/3h forecast (next 24h snapshot).

    Cache: ``weather:{lat}:{lng}`` TTL 1h. On any failure, returns mild synthetic events.
    """
    settings = get_settings()
    api_key = (settings.OPENWEATHER_API_KEY or "").strip()
    if not api_key:
        logger.info("OPENWEATHER_API_KEY missing; using synthetic weather for all farms")
        return [_synthetic_event(f) for f in farms]

    out: list[WeatherEvent] = []
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            for farm in farms:
                key = _weather_cache_key(farm.lat, farm.lng)
                try:
                    raw = await r.get(key)
                    if raw:
                        payload = json.loads(raw)
                    else:
                        payload = await _fetch_forecast_payload(
                            farm.lat, farm.lng, api_key, client=client
                        )
                        await r.set(key, json.dumps(payload), ex=WEATHER_CACHE_TTL_S)

                    flist = payload.get("list")
                    if not isinstance(flist, list) or not flist:
                        out.append(_synthetic_event(farm))
                        continue
                    max_rain, max_temp = _aggregate_next_24h(flist)
                    out.append(_event_from_payload(farm, max_rain, max_temp))
                except Exception as exc:
                    logger.warning("weather failed for farm %s: %s", farm.id, exc)
                    out.append(_synthetic_event(farm))
    finally:
        await r.aclose()

    return out
