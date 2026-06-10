"""Internet outage — external routing APIs fail, Haversine fallback."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tools.maps_api import get_distance_matrix, haversine_km


@pytest.mark.asyncio
async def test_distance_matrix_survives_routing_api_failures() -> None:
    pts = [(12.97, 77.59), (13.08, 77.54)]
    with (
        patch("tools.maps_api._ors_pair_km", new=AsyncMock(return_value=None)),
        patch("tools.maps_api._osrm_pair_km", new=AsyncMock(return_value=None)),
        patch("tools.maps_api._google_pair_km", new=AsyncMock(return_value=None)),
        patch("tools.maps_api._cache_get", new=AsyncMock(return_value=None)),
        patch("tools.maps_api._cache_set", new=AsyncMock()),
    ):
        mat = await get_distance_matrix(pts, pts)

    assert len(mat) == 2
    assert mat[0][0] == 0.0
    expected = haversine_km(pts[0], pts[1])
    assert abs(mat[0][1] - expected) < 0.01


@pytest.mark.asyncio
async def test_weather_falls_back_when_api_unreachable() -> None:
    from tools.weather_api import fetch_weather

    from tests.test_resilience.conftest import mini_farms

    with (
        patch("tools.weather_api.get_settings") as mock_settings,
        patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=ConnectionError("offline"))),
        patch("tools.weather_api._redis_client", new=AsyncMock(side_effect=ConnectionError("redis down"))),
    ):
        mock_settings.return_value.OPENWEATHER_API_KEY = "test-key"
        mock_settings.return_value.REDIS_URL = "redis://localhost:6379/0"
        result = await fetch_weather(mini_farms(), scenario_type="live_weather")

    assert len(result["events"]) == 2
    meta = result["meta"]
    assert meta["weather_source"] == "synthetic_fallback"
    assert meta.get("fallback_mode") == "live_weather"
    assert meta.get("scenario_modifier_applied") is False
