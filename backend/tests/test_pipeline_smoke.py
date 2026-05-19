"""End-to-end pipeline smoke test with mocked external APIs."""

from __future__ import annotations

from datetime import date, time as dt_time
from unittest.mock import AsyncMock, patch

import pytest

from graph import PipelineRequest, run_scenario
from models.schemas import DemandPoint, Farm, Truck, WeatherEvent


def _mini_farms() -> list[Farm]:
    hw_start = date(2026, 1, 1)
    hw_end = date(2026, 12, 31)
    return [
        Farm(
            id="farm-smoke-1",
            name="Smoke Farm 1",
            lat=13.08,
            lng=77.54,
            crop_type="tomato",
            acreage=5.0,
            typical_yield_kg=400.0,
            harvest_window_start=hw_start,
            harvest_window_end=hw_end,
        ),
        Farm(
            id="farm-smoke-2",
            name="Smoke Farm 2",
            lat=13.34,
            lng=77.10,
            crop_type="onion",
            acreage=6.0,
            typical_yield_kg=350.0,
            harvest_window_start=hw_start,
            harvest_window_end=hw_end,
        ),
    ]


def _mini_demand_points() -> list[DemandPoint]:
    return [
        DemandPoint(
            id="dp-smoke-1",
            name="Smoke Mandi",
            lat=13.02,
            lng=77.53,
            type="apmc",
            base_demand_per_day=800.0,
        ),
    ]


def _mini_trucks() -> list[Truck]:
    return [
        Truck(
            id="tr-smoke-1",
            capacity_kg=3000.0,
            cost_per_km=20.0,
            availability_start=dt_time(5, 0),
            availability_end=dt_time(20, 0),
        ),
    ]


def _fake_weather(farms: list[Farm], **_kwargs: object) -> dict:
    events = [
        WeatherEvent(
            id=f"wx-{f.id}",
            event_date=date.today(),
            region=f.name,
            description="smoke_test; risk=normal",
            severity="normal",
            precipitation_mm=0.0,
        )
        for f in farms
    ]
    return {
        "events": events,
        "meta": {
            "weather_source": "synthetic_fallback",
            "scenario_modifier_applied": True,
            "scenario_type": "normal_day",
        },
    }


def _fake_matrix(origins, destinations):  # noqa: ANN001
    n_o, n_d = len(origins), len(destinations)
    return [[10.0 + abs(i - j) for j in range(n_d)] for i in range(n_o)]


@pytest.mark.asyncio
async def test_pipeline_smoke_normal_day() -> None:
    farms = _mini_farms()
    dps = _mini_demand_points()
    trucks = _mini_trucks()

    with (
        patch("agents.weather_agent.fetch_weather", new=AsyncMock(side_effect=_fake_weather)),
        patch("tools.maps_api.get_distance_matrix", new=AsyncMock(side_effect=_fake_matrix)),
        patch("memory.outcome_store.get_demand_history", new=AsyncMock(return_value=[])),
        patch("memory.outcome_store.get_route_history", new=AsyncMock(return_value=[])),
        patch("agents.demand_agent._llm_multipliers", new=AsyncMock(return_value=({}, None))),
        patch("agents.inventory_agent._llm_rank", new=AsyncMock(return_value=([], None))),
        patch("tools.db.create_plan", new=AsyncMock(return_value=type("P", (), {"id": "00000000-0000-0000-0000-000000000001"})())),
        patch("tools.db.create_run_log", new=AsyncMock()),
    ):
        result = await run_scenario(
            PipelineRequest(
                farms=farms,
                demand_points=dps,
                trucks=trucks,
                scenario_type="normal_day",
            ),
        )

    assert result.run_id
    assert result.kpis
    assert "waste_reduction_pct" in result.kpis
    assert len(result.agent_traces) >= 5
    assert result.human_review is False or result.plan is not None
