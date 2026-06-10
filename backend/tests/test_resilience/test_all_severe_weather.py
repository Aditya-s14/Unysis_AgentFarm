"""All farms severe weather — validator warns, pipeline completes."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from graph import PipelineRequest, run_scenario
from models.schemas import WeatherEvent
from tests.test_resilience.conftest import (
    mini_demand_points,
    mini_farms,
    mini_trucks,
)


def _all_severe_weather(farms, **_kwargs):  # noqa: ANN001
    events = [
        WeatherEvent(
            id=f"wx-{f.id}",
            event_date=date.today(),
            region=f.name,
            description=f"live_weather; rain=60.0mm; temp=42.0C; risk=severe",
            severity="severe",
            precipitation_mm=60.0,
        )
        for f in farms
    ]
    return {
        "events": events,
        "meta": {
            "weather_source": "synthetic_fallback",
            "scenario_type": "live_weather",
        },
    }


@pytest.mark.asyncio
async def test_all_severe_weather_pipeline_completes(pipeline_patches) -> None:
    with patch("agents.weather_agent.fetch_weather", new=AsyncMock(side_effect=_all_severe_weather)):
        result = await run_scenario(
            PipelineRequest(
                farms=mini_farms(),
                demand_points=mini_demand_points(),
                trucks=mini_trucks(),
                scenario_type="live_weather",
            ),
        )

    assert all(v == "severe" for v in result.weather_risk_summary.values())
    assert result.run_id
    validator_traces = [t for t in result.agent_traces if t.get("agent_name") == "validator"]
    assert validator_traces
    details = validator_traces[-1].get("details") or {}
    assert details.get("all_severe_weather") is True
    plan_warnings = (result.plan.validation.warnings or []) if result.plan and result.plan.validation else []
    assert any("ALL_SEVERE_WEATHER" in w for w in plan_warnings)
