"""Shared fixtures for resilience tests."""

from __future__ import annotations

from datetime import date, time as dt_time
from unittest.mock import AsyncMock, patch

import pytest

from models.schemas import DemandPoint, Farm, Truck, WeatherEvent


def mini_farms() -> list[Farm]:
    hw_start = date(2026, 1, 1)
    hw_end = date(2026, 12, 31)
    return [
        Farm(
            id="farm-r1",
            name="Resilience Farm 1",
            lat=13.08,
            lng=77.54,
            crop_type="tomato",
            acreage=5.0,
            typical_yield_kg=400.0,
            harvest_window_start=hw_start,
            harvest_window_end=hw_end,
        ),
        Farm(
            id="farm-r2",
            name="Resilience Farm 2",
            lat=13.34,
            lng=77.10,
            crop_type="onion",
            acreage=6.0,
            typical_yield_kg=350.0,
            harvest_window_start=hw_start,
            harvest_window_end=hw_end,
        ),
    ]


def mini_demand_points() -> list[DemandPoint]:
    return [
        DemandPoint(
            id="dp-r1",
            name="Resilience Mandi",
            lat=13.02,
            lng=77.53,
            type="apmc",
            base_demand_per_day=800.0,
        ),
    ]


def mini_trucks() -> list[Truck]:
    return [
        Truck(
            id="tr-r1",
            capacity_kg=3000.0,
            cost_per_km=20.0,
            availability_start=dt_time(5, 0),
            availability_end=dt_time(20, 0),
        ),
    ]


def fake_matrix(origins, destinations):  # noqa: ANN001
    n_o, n_d = len(origins), len(destinations)
    return [[10.0 + abs(i - j) for j in range(n_d)] for i in range(n_o)]


@pytest.fixture
def pipeline_patches():
    """Standard mocks so resilience tests isolate one failure mode at a time."""
    with (
        patch("memory.outcome_store.get_demand_history", new=AsyncMock(return_value=[])),
        patch("memory.outcome_store.get_route_history", new=AsyncMock(return_value=[])),
        patch("agents.demand_agent._llm_multipliers", new=AsyncMock(return_value=({}, None))),
        patch("agents.inventory_agent._llm_rank", new=AsyncMock(return_value=([], None))),
        patch("tools.maps_api.get_distance_matrix", new=AsyncMock(side_effect=fake_matrix)),
        patch("tools.db.create_plan", new=AsyncMock(return_value=type("P", (), {"id": "00000000-0000-0000-0000-000000000001"})())),
        patch("tools.db.create_run_log", new=AsyncMock()),
        patch("tools.weather_store.save_run_weather_snapshot", new=AsyncMock()),
    ):
        yield
