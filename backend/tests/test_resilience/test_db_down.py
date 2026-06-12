"""Database unavailable during persist — pipeline still returns in-memory plan."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from graph import PipelineRequest, run_scenario
from tests.test_resilience.conftest import (
    mini_demand_points,
    mini_farms,
    mini_trucks,
)


def _fake_weather(farms, **_kwargs):  # noqa: ANN001
    from datetime import date

    from models.schemas import WeatherEvent

    events = [
        WeatherEvent(
            id=f"wx-{f.id}",
            event_date=date.today(),
            region=f.name,
            description="test; risk=normal",
            severity="normal",
            precipitation_mm=0.0,
        )
        for f in farms
    ]
    return {"events": events, "meta": {"weather_source": "synthetic_fallback"}}


@pytest.mark.asyncio
async def test_pipeline_completes_when_db_persist_fails(pipeline_patches) -> None:
    with (
        patch("agents.weather_agent.fetch_weather", new=AsyncMock(side_effect=_fake_weather)),
        patch("tools.db.create_plan", new=AsyncMock(side_effect=RuntimeError("db down"))),
    ):
        result = await run_scenario(
            PipelineRequest(
                farms=mini_farms(),
                demand_points=mini_demand_points(),
                trucks=mini_trucks(),
                scenario_type="normal_day",
            ),
        )

    assert result.run_id
    assert result.plan is not None
