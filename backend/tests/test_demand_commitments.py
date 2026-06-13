"""Tests for farmer pre-commitment contracts and weighted demand."""

from __future__ import annotations

from datetime import date

import importlib

import pytest

demand_agent_mod = importlib.import_module("agents.demand_agent")
from models.schemas import DemandPoint, Farm, FarmerCommitment
from tools.commitments import (
    COMMITMENT_WEIGHT,
    FORECAST_WEIGHT,
    aggregate_commitments_by_mandi,
    is_commitment_eligible,
    nearest_demand_point_id,
)


def _farm(
    farm_id: str,
    *,
    lat: float = 13.08,
    lng: float = 77.54,
    harvest_start: date = date(2026, 6, 15),
) -> Farm:
    return Farm(
        id=farm_id,
        name=f"Farm {farm_id}",
        lat=lat,
        lng=lng,
        crop_type="tomato",
        acreage=5.0,
        typical_yield_kg=1000.0,
        harvest_window_start=harvest_start,
        harvest_window_end=date(2026, 7, 30),
    )


def _dp(dp_id: str, *, lat: float = 13.02, lng: float = 77.53, base: float = 3000.0) -> DemandPoint:
    return DemandPoint(
        id=dp_id,
        name=f"Mandi {dp_id}",
        lat=lat,
        lng=lng,
        type="apmc",
        base_demand_per_day=base,
    )


def test_is_commitment_eligible_within_seven_days():
    today = date(2026, 6, 12)
    assert is_commitment_eligible(_farm("f1", harvest_start=date(2026, 6, 12)), today)
    assert is_commitment_eligible(_farm("f2", harvest_start=date(2026, 6, 19)), today)
    assert not is_commitment_eligible(_farm("f3", harvest_start=date(2026, 6, 20)), today)
    assert not is_commitment_eligible(_farm("f4", harvest_start=date(2026, 3, 15)), today)


def test_aggregate_commitments_sums_by_mandi():
    farms = [
        _farm("farm-a", lat=13.08, lng=77.54),
        _farm("farm-b", lat=13.09, lng=77.55),
    ]
    dps = [_dp("dp-1"), _dp("dp-2", lat=19.0, lng=73.0)]
    commitments = [
        FarmerCommitment(farm_id="farm-a", tonnage_kg=1000),
        FarmerCommitment(farm_id="farm-b", tonnage_kg=500),
        FarmerCommitment(farm_id="farm-a", tonnage_kg=200, demand_point_id="dp-2"),
    ]
    totals = aggregate_commitments_by_mandi(commitments, farms, dps)
    assert totals["dp-1"] == pytest.approx(1500.0)
    assert totals["dp-2"] == pytest.approx(200.0)


def test_nearest_demand_point_id():
    farm = _farm("farm-x", lat=13.08, lng=77.54)
    near = _dp("dp-near", lat=13.02, lng=77.53)
    far = _dp("dp-far", lat=19.0, lng=73.0)
    assert nearest_demand_point_id(farm, [near, far]) == "dp-near"


@pytest.mark.asyncio
async def test_demand_agent_applies_weighted_commitments(monkeypatch):
    """Day-0 forecast blends 0.6 × model + 1.0 × committed kg."""
    async def _bias(*args, **kwargs):
        return 1.0

    async def _llm(*args, **kwargs):
        return {}, None

    monkeypatch.setattr(demand_agent_mod, "_bias_correction", _bias)
    monkeypatch.setattr(demand_agent_mod, "_llm_multipliers", _llm)

    farm = _farm("farm-c", harvest_start=date(2026, 6, 14))
    dp = _dp("dp-commit")

    state = {
        "demand_points": [dp],
        "farms": [farm],
        "weather_risk_summary": {},
        "scenario_type": "normal_day",
        "farmer_commitments": [
            FarmerCommitment(farm_id="farm-c", tonnage_kg=2000.0, demand_point_id="dp-commit"),
        ],
        "agent_traces": [],
    }

    result = await demand_agent_mod.run(state)
    forecast = result["demand_forecast"]["dp-commit"]
    assert len(forecast) == 7

    baseline_state = {**state, "farmer_commitments": []}
    baseline = await demand_agent_mod.run(baseline_state)
    raw_day0 = baseline["demand_forecast"]["dp-commit"][0]

    expected = round(FORECAST_WEIGHT * raw_day0 + COMMITMENT_WEIGHT * 2000.0, 2)
    assert forecast[0] == expected
    assert forecast[0] > raw_day0
    assert any("weighted_demand=applied" in t.get("notes", "") for t in result["agent_traces"])
