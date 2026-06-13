"""Tests for D2 direct buyer demand posts and buyer-first routing."""

from __future__ import annotations

import importlib
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

demand_agent_mod = importlib.import_module("agents.demand_agent")
logistics_mod = importlib.import_module("agents.logistics_agent")
from main import app
from models.schemas import BuyerDemandPost, BuyerDemandPostCreate, DemandPoint, Farm, FarmerCommitment
from tools.buyer_demands import aggregate_buyer_demand_by_mandi, stable_post_id
from tools.commitments import COMMITMENT_WEIGHT, FORECAST_WEIGHT
from tools.vrp_solver import _demand_at_dp

_POSTS = [
    BuyerDemandPost(
        id="buyer-dp-priv-01-tomato",
        demand_point_id="dp-priv-01",
        buyer_name="Taj West End Kitchen",
        buyer_type="restaurant",
        crop_type="tomato",
        quantity_kg=800,
        price_per_kg=22,
    ),
    BuyerDemandPost(
        id="buyer-dp-priv-02-onion",
        demand_point_id="dp-priv-02",
        buyer_name="Metro Cash Nashik",
        buyer_type="supermarket",
        crop_type="onion",
        quantity_kg=600,
        price_per_kg=16,
    ),
]


def _private_dp(dp_id: str, *, base: float = 1200.0) -> DemandPoint:
    return DemandPoint(
        id=dp_id,
        name=f"Private {dp_id}",
        lat=18.5,
        lng=73.8,
        type="private",
        base_demand_per_day=base,
    )


def _apmc_dp(dp_id: str) -> DemandPoint:
    return DemandPoint(
        id=dp_id,
        name=f"APMC {dp_id}",
        lat=19.0,
        lng=73.0,
        type="apmc",
        base_demand_per_day=5000.0,
    )


def test_stable_post_id_deterministic():
    assert stable_post_id("dp-priv-01", "Tomato") == "buyer-dp-priv-01-tomato"
    assert stable_post_id("dp-priv-01", "tomato") == "buyer-dp-priv-01-tomato"


def test_aggregate_buyer_demand_by_mandi():
    totals = aggregate_buyer_demand_by_mandi(_POSTS)
    assert totals["dp-priv-01"] == pytest.approx(800.0)
    assert totals["dp-priv-02"] == pytest.approx(600.0)


def test_order_dps_buyer_first_sort_keys():
    dps = [
        _apmc_dp("dp-apmc-1"),
        _private_dp("dp-priv-02"),
        _private_dp("dp-priv-01"),
        DemandPoint(
            id="dp-retail-1",
            name="Retail",
            lat=18.0,
            lng=73.0,
            type="retail",
            base_demand_per_day=500,
        ),
    ]
    ordered = logistics_mod._order_dps_buyer_first(dps, _POSTS)
    assert ordered[0].type == "private"
    assert ordered[1].type == "private"
    assert {ordered[0].id, ordered[1].id} == {"dp-priv-01", "dp-priv-02"}
    assert ordered[2].type == "apmc"
    assert ordered[3].type == "retail"


def test_demand_at_dp_uses_posted_qty():
    dp = _private_dp("dp-priv-01", base=400)
    base_units = _demand_at_dp(dp)
    boosted = _demand_at_dp(dp, _POSTS)
    assert boosted > base_units
    assert boosted == max(base_units, int(800 / 50))


@pytest.mark.asyncio
async def test_day0_commitment_and_buyer_post_same_private_dp(monkeypatch):
    """Forecast uses max(I2 blend, posted_kg) — not sum of both blends."""

    async def _bias(*args, **kwargs):
        return 1.0

    async def _llm(*args, **kwargs):
        return {}, None

    monkeypatch.setattr(demand_agent_mod, "_bias_correction", _bias)
    monkeypatch.setattr(demand_agent_mod, "_llm_multipliers", _llm)

    dp = _private_dp("dp-priv-01", base=1000.0)
    farm = Farm(
        id="farm-x",
        name="Farm X",
        lat=18.51,
        lng=73.87,
        crop_type="tomato",
        acreage=5.0,
        typical_yield_kg=1000.0,
        harvest_window_start=date(2026, 6, 15),
        harvest_window_end=date(2026, 7, 30),
    )
    committed_kg = 500.0
    posted_kg = 800.0

    state = {
        "demand_points": [dp],
        "farms": [farm],
        "weather_risk_summary": {},
        "scenario_type": "normal_day",
        "farmer_commitments": [
            FarmerCommitment(
                farm_id="farm-x",
                tonnage_kg=committed_kg,
                demand_point_id="dp-priv-01",
            ),
        ],
        "buyer_demands": [
            BuyerDemandPost(
                id=stable_post_id("dp-priv-01", "tomato"),
                demand_point_id="dp-priv-01",
                buyer_name="Buyer",
                buyer_type="restaurant",
                crop_type="tomato",
                quantity_kg=posted_kg,
                price_per_kg=22,
            ),
        ],
        "agent_traces": [],
    }

    baseline = await demand_agent_mod.run({**state, "farmer_commitments": [], "buyer_demands": []})
    raw_day0 = baseline["demand_forecast"]["dp-priv-01"][0]

    i2_only = await demand_agent_mod.run({**state, "buyer_demands": []})
    i2_blend = round(FORECAST_WEIGHT * raw_day0 + COMMITMENT_WEIGHT * committed_kg, 2)

    both = await demand_agent_mod.run(state)
    day0_both = both["demand_forecast"]["dp-priv-01"][0]

    assert i2_only["demand_forecast"]["dp-priv-01"][0] == i2_blend
    expected_both = round(max(i2_blend, posted_kg), 2)
    assert day0_both == expected_both
    assert day0_both != pytest.approx(i2_blend + posted_kg)
    assert any("buyer_demand_floor=applied" in t.get("notes", "") for t in both["agent_traces"])


@pytest.mark.asyncio
async def test_buyer_api_round_trip_and_stable_delete(monkeypatch):
    """POST twice same (dp, crop) → same id; DELETE removes post."""
    from tools import buyer_demand_store as store

    memory: dict[str, str] = {}

    class FakeRedis:
        async def get(self, key):
            return memory.get(key)

        async def set(self, key, value, ex=None):
            memory[key] = value

        async def delete(self, key):
            return 1 if memory.pop(key, None) is not None else 0

        async def scan_iter(self, match=None, count=None):
            prefix = (match or "").replace("*", "")
            for k in list(memory):
                if k.startswith(prefix):
                    yield k

    monkeypatch.setattr(store, "_REDIS", FakeRedis())

    private = _private_dp("dp-priv-01")
    body = BuyerDemandPostCreate(
        demand_point_id=private.id,
        buyer_name="Test Buyer",
        buyer_type="restaurant",
        crop_type="tomato",
        quantity_kg=400,
        price_per_kg=20,
    )

    async def _private_map():
        return {private.id: private}

    monkeypatch.setattr(
        "routes.buyer._load_private_demand_points",
        _private_map,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/buyer/demand", json=body.model_dump())
        assert r1.status_code == 200
        id1 = r1.json()["post"]["id"]

        r2 = await client.post(
            "/api/buyer/demand",
            json={**body.model_dump(), "quantity_kg": 900},
        )
        assert r2.status_code == 200
        id2 = r2.json()["post"]["id"]
        assert id1 == id2

        listed = await client.get("/api/buyer/demand")
        assert listed.status_code == 200
        posts = listed.json()["posts"]
        assert any(p["id"] == id1 and p["quantity_kg"] == 900 for p in posts)

        deleted = await client.delete(f"/api/buyer/demand/{id1}")
        assert deleted.status_code == 200

        listed2 = await client.get("/api/buyer/demand")
        assert not any(p["id"] == id1 for p in listed2.json()["posts"])


def test_geo_regions_private_first_with_posts():
    farms = [
        Farm(
            id="f1",
            name="F1",
            lat=18.5,
            lng=73.8,
            crop_type="tomato",
            acreage=5.0,
            typical_yield_kg=1000.0,
            harvest_window_start=date(2026, 6, 15),
            harvest_window_end=date(2026, 7, 30),
        ),
    ]
    dps = [_apmc_dp("dp-apmc-1"), _private_dp("dp-priv-01")]
    regions = logistics_mod._geo_regions(farms, dps, buyer_demands=_POSTS)
    _, region_dps = regions[0]
    assert region_dps[0].id == "dp-priv-01"
