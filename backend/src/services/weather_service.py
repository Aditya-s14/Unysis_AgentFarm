"""Weather service — OpenWeatherMap client with Redis-backed caching."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ..config.logging_config import get_logger
from ..config.settings import get_settings
from ..tools.weather_tools import classify_risk, synthetic_forecast
from .cache_service import CacheService, get_cache

logger = get_logger(__name__)


class WeatherService:
    """Fetches forecasts, caches them, and classifies risk."""

    def __init__(self, cache: Optional[CacheService] = None) -> None:
        self._settings = get_settings()
        self._cache = cache or get_cache()

    async def get_forecast(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Return a forecast dict for the given coordinates.

        Uses a 1-hour Redis cache; falls back to synthetic data when the API
        key is missing or the upstream call fails.
        """

        key = f"weather:{round(latitude, 3)}:{round(longitude, 3)}"
        cached = await self._cache.get(key)
        if cached is not None:
            return cached

        payload: Dict[str, Any]
        if not self._settings.OPENWEATHER_API_KEY:
            payload = synthetic_forecast(latitude, longitude)
        else:
            try:
                payload = await self._fetch_upstream(latitude, longitude)
            except Exception as exc:  # pragma: no cover - network path
                logger.warning("weather_fetch_failed", error=str(exc))
                payload = synthetic_forecast(latitude, longitude)

        payload["risk_level"] = classify_risk(
            payload.get("rain_mm", 0.0), payload.get("temperature_c", 0.0)
        ).value
        await self._cache.set(key, payload, ttl=self._settings.WEATHER_CACHE_TTL)
        return payload

    async def _fetch_upstream(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Call OpenWeatherMap; parse into the canonical forecast dict.

        TODO: replace with real 7-day forecast endpoint and daily rollup.
        """

        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self._settings.OPENWEATHER_API_KEY,
            "units": "metric",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        # Simplified rollup: first entry only (TODO: 7-day aggregation)
        first = (data.get("list") or [{}])[0]
        main = first.get("main", {})
        rain = first.get("rain", {}).get("3h", 0.0)
        return {
            "rain_mm": float(rain),
            "temperature_c": float(main.get("temp", 0.0)),
            "humidity_pct": float(main.get("humidity", 0.0)),
            "source": "openweathermap",
            "latitude": latitude,
            "longitude": longitude,
        }
