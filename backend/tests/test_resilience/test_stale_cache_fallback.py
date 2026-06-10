"""Stale weather cache — use last successful OpenWeather reading when API fails."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.test_resilience.conftest import mini_farms
from tools.weather_api import (
    STALE_READING_DISCLAIMER,
    WEATHER_LAST_GOOD_PREFIX,
    _last_good_key,
    fetch_weather,
)


class _FakeRedis:
    """Minimal Redis stub: short cache empty, last-good keys populated."""

    def __init__(self, last_good: dict[str, dict]) -> None:
        self._last_good = last_good

    async def get(self, key: str) -> str | None:
        if key.startswith(WEATHER_LAST_GOOD_PREFIX):
            payload = self._last_good.get(key)
            return json.dumps(payload) if payload else None
        return None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:  # noqa: ARG002
        if key.startswith(WEATHER_LAST_GOOD_PREFIX):
            self._last_good[key] = json.loads(value)


def _last_good_payload(*, rain: float, temp: float) -> dict:
    return {
        "fetched_at": datetime(2026, 6, 10, 8, 0, tzinfo=timezone.utc).isoformat(),
        "base_rain_mm": rain,
        "base_temp_c": temp,
        "humidity_pct": 62.0,
        "wind_speed_ms": 2.4,
    }


@pytest.mark.asyncio
async def test_api_failure_uses_stale_cache_per_farm() -> None:
    farms = mini_farms()
    last_good = {
        _last_good_key(farms[0].lat, farms[0].lng): _last_good_payload(rain=5.0, temp=34.0),
        _last_good_key(farms[1].lat, farms[1].lng): _last_good_payload(rain=0.0, temp=31.5),
    }
    fake_redis = _FakeRedis(last_good)

    with (
        patch("tools.weather_api.get_settings") as mock_settings,
        patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=ConnectionError("offline"))),
        patch("tools.weather_api._redis_client", new=AsyncMock(return_value=fake_redis)),
    ):
        mock_settings.return_value.OPENWEATHER_API_KEY = "test-key"
        mock_settings.return_value.REDIS_URL = "redis://localhost:6379/0"
        result = await fetch_weather(farms, scenario_type="live_weather")

    meta = result["meta"]
    assert meta["weather_source"] == "stale_cache"
    assert meta.get("fallback_mode") == "stale_cache"
    assert meta.get("weather_disclaimer") == STALE_READING_DISCLAIMER
    assert meta.get("farms_with_stale_cache") == 2
    assert meta.get("farms_with_live_api") == 0

    temps = [m["base_temp_c"] for m in meta["farm_readings"]]
    assert 34.0 in temps
    assert 31.5 in temps
    assert all(m.get("stale_reading") for m in meta["farm_readings"])

    for event in result["events"]:
        assert "live_weather" in event.description
        assert event.severity in ("normal", "warning", "severe")


@pytest.mark.asyncio
async def test_no_stale_cache_falls_back_to_live_weather_baseline() -> None:
    farms = mini_farms()
    fake_redis = _FakeRedis({})

    with (
        patch("tools.weather_api.get_settings") as mock_settings,
        patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=ConnectionError("offline"))),
        patch("tools.weather_api._redis_client", new=AsyncMock(return_value=fake_redis)),
    ):
        mock_settings.return_value.OPENWEATHER_API_KEY = "test-key"
        mock_settings.return_value.REDIS_URL = "redis://localhost:6379/0"
        result = await fetch_weather(farms, scenario_type="live_weather")

    meta = result["meta"]
    assert meta["weather_source"] == "synthetic_fallback"
    assert meta.get("fallback_mode") == "live_weather"
    assert all(m["base_temp_c"] == 28.0 for m in meta["farm_readings"])


@pytest.mark.asyncio
async def test_successful_fetch_saves_last_good_reading() -> None:
    from tools.weather_api import _fetch_farm_readings

    farm = mini_farms()[0]
    fake_redis = _FakeRedis({})

    cur_payload = {
        "main": {"temp": 33.2, "humidity": 55},
        "wind": {"speed": 1.8},
        "rain": {"1h": 2.0},
    }
    fct_payload = {
        "list": [{"main": {"temp": 30.0}, "rain": {"3h": 1.0}} for _ in range(8)],
    }

    class _MockResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    async def _fake_get(url: str, **kwargs):  # noqa: ANN003, ARG001
        if "forecast" in url:
            return _MockResponse(fct_payload)
        return _MockResponse(cur_payload)

    http = AsyncMock()
    http.get = AsyncMock(side_effect=_fake_get)
    await _fetch_farm_readings(farm, "test-key", fake_redis, http, "live_weather")

    key = _last_good_key(farm.lat, farm.lng)
    assert key in fake_redis._last_good
    stored = fake_redis._last_good[key]
    assert stored["base_temp_c"] == 33.2
    assert stored["base_rain_mm"] == 2.0
