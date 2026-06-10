"""Weather fallbacks always use live_weather rules, not scripted scenario overlays."""

from __future__ import annotations

import pytest

from tests.test_resilience.conftest import mini_farms
from tools.scenario_effects import HEAT, LIVE
from tools.weather_api import fetch_weather


@pytest.mark.asyncio
async def test_no_api_key_uses_live_weather_not_requested_scenario() -> None:
    """heat_wave selected but API missing → live_weather fallback, not 39°C overlay."""
    farms = mini_farms()
    result = await fetch_weather(farms, scenario_type="heat_wave")
    meta = result["meta"]

    assert meta["weather_source"] == "synthetic_fallback"
    assert meta["scenario_type"] == LIVE
    assert meta["requested_scenario_type"] == HEAT
    assert meta.get("fallback_mode") == "live_weather"
    assert meta.get("scenario_modifier_applied") is False

    for event in result["events"]:
        assert "live_weather" in event.description
        assert "heat_wave" not in event.description
        assert event.severity == "normal"


@pytest.mark.asyncio
async def test_monsoon_request_without_api_still_live_fallback() -> None:
    result = await fetch_weather(mini_farms(), scenario_type="monsoon_disruption")
    meta = result["meta"]
    assert meta["fallback_mode"] == "live_weather"
    assert all("monsoon_disruption" not in e.description for e in result["events"])
