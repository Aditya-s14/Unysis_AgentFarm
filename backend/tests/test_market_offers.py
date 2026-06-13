"""Tests for D4 bid/ask offer ledger and guaranteed routing."""

from __future__ import annotations

import importlib
from datetime import date, datetime, time, timezone

import pytest
from httpx import ASGITransport, AsyncClient

logistics_mod = importlib.import_module("agents.logistics_agent")
metrics_mod = importlib.import_module("agents.metrics")
from main import app
from models.schemas import (
    BuyerDemandPost,
    DemandPoint,
    Farm,
    MarketAcceptedCommitment,
    MarketOfferCreate,
    Route,
    RoutePlan,
    RouteStop,
    Truck,
)
from tools.market_routing import ensure_guaranteed_routes, order_dps_market_first, overlay_market_farm_to_dp

_COMMITMENTS = [
    MarketAcceptedCommitment(
        offer_id="market-ask-dp-priv-01-tomato-seed001",
        farm_id="farm-001",
        demand_point_id="dp-priv-01",
        crop_type="tomato",
        quantity_kg=800,
        price_per_kg=22,
        accepted_at=datetime.now(timezone.utc),
    ),
]

_POSTS = [
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


def _tomato_farm(farm_id: str = "farm-001") -> Farm:
    return Farm(
        id=farm_id,
        name="Nandi Valley",
        lat=13.0827,
        lng=77.5439,
        crop_type="tomato",
        acreage=8.4,
        typical_yield_kg=1200,
        harvest_window_start=date(2026, 6, 15),
        harvest_window_end=date(2026, 7, 30),
    )


def test_order_dps_market_first_sort_keys():
    dps = [
        _apmc_dp("dp-apmc-1"),
        _private_dp("dp-priv-03"),
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
    ordered = order_dps_market_first(dps, _POSTS, _COMMITMENTS)
    assert ordered[0].id == "dp-priv-01"
    assert ordered[1].id == "dp-priv-02"
    assert ordered[2].id == "dp-priv-03"
    assert ordered[3].type == "apmc"
    assert ordered[4].type == "retail"


def test_overlay_market_farm_to_dp():
    mapping = {"farm-001": "dp-apmc-1"}
    out = overlay_market_farm_to_dp(mapping, _COMMITMENTS)
    assert out["farm-001"] == "dp-priv-01"


def test_ensure_guaranteed_routes_injects_when_feasible():
    """A commitment within a legal day-trip gets a dedicated injected route."""
    farm = _tomato_farm()  # Bengaluru (13.08, 77.54)
    # Buyer near the farm so the direct trip is legal (well under the cap).
    dp = DemandPoint(
        id="dp-priv-09",
        name="Nearby Direct Buyer",
        lat=13.20,
        lng=77.60,
        type="private",
        base_demand_per_day=1000.0,
    )
    commitments = [
        MarketAcceptedCommitment(
            offer_id="o-near",
            farm_id="farm-001",
            demand_point_id="dp-priv-09",
            crop_type="tomato",
            quantity_kg=800,
            price_per_kg=22,
            accepted_at=datetime.now(timezone.utc),
        ),
    ]
    trucks = [
        Truck(
            id="tr-001",
            capacity_kg=5000,
            cost_per_km=18.0,
            availability_start=time(4, 0),
            availability_end=time(22, 0),
        ),
    ]
    plan = RoutePlan(routes=[])
    injected, _warnings = ensure_guaranteed_routes(
        plan, commitments, [farm], [dp], trucks, [],
    )
    assert injected == 1
    assert len(plan.routes) == 1
    route = plan.routes[0]
    assert route.truck_id == "tr-001"
    farm_stops = [s for s in route.stops if s.label == "farm-001"]
    dp_stops = [s for s in route.stops if s.demand_point_id == "dp-priv-09"]
    assert farm_stops and dp_stops
    assert farm_stops[0].sequence < dp_stops[0].sequence


def test_ensure_guaranteed_routes_flags_far_commitment():
    """A commitment beyond a legal one-truck day-trip is flagged, not injected.

    Bengaluru farm -> Pune buyer (~700+ km) cannot be one truck in one legal
    day; injecting such a route would present an illegal, undispatchable plan.
    It must be skipped and surfaced as a warning for manual/multi-day handling.
    """
    farm = _tomato_farm()  # Bengaluru
    dp = _private_dp("dp-priv-01")  # Pune (18.5, 73.8)
    trucks = [
        Truck(
            id="tr-001",
            capacity_kg=5000,
            cost_per_km=18.0,
            availability_start=time(4, 0),
            availability_end=time(22, 0),
        ),
    ]
    plan = RoutePlan(routes=[])
    injected, warnings = ensure_guaranteed_routes(
        plan, _COMMITMENTS, [farm], [dp], trucks, [],
    )
    assert injected == 0
    assert len(plan.routes) == 0
    assert any("legal day trip" in w for w in warnings)


def test_ensure_guaranteed_routes_skips_when_satisfied():
    plan = RoutePlan(
        routes=[
            Route(
                truck_id="tr-001",
                stops=[
                    RouteStop(sequence=0, lat=13.0, lng=77.0, label="farm-001"),
                    RouteStop(
                        sequence=1,
                        lat=18.5,
                        lng=73.8,
                        demand_point_id="dp-priv-01",
                    ),
                ],
            ),
        ],
    )
    injected, _ = ensure_guaranteed_routes(
        plan, _COMMITMENTS, [], [_private_dp("dp-priv-01")], [], [],
    )
    assert injected == 0
    assert len(plan.routes) == 1


def test_routed_farm_to_dp_overlay():
    farm = _tomato_farm()
    dp_apmc = _apmc_dp("dp-apmc-1")
    state = {
        "market_commitments": _COMMITMENTS,
        "route_plan": RoutePlan(
            routes=[
                Route(
                    truck_id="tr-001",
                    stops=[
                        RouteStop(sequence=0, lat=13.0, lng=77.0, label="farm-001"),
                        RouteStop(
                            sequence=1,
                            lat=19.0,
                            lng=73.0,
                            demand_point_id="dp-apmc-1",
                        ),
                    ],
                ),
            ],
        ),
    }
    mapping = metrics_mod._routed_farm_to_dp(
        state, [farm], [dp_apmc, _private_dp("dp-priv-01")],
    )
    assert mapping["farm-001"] == "dp-priv-01"


@pytest.mark.asyncio
async def test_market_offer_api_round_trip(monkeypatch):
    from tools import market_offer_store as store

    memory: dict[str, str] = {}

    class FakeRedis:
        async def get(self, key):
            return memory.get(key)

        async def set(self, key, value, ex=None):
            memory[key] = value

        async def scan_iter(self, match=None, count=None):
            prefix = (match or "").replace("*", "")
            for k in list(memory):
                if k.startswith(prefix):
                    yield k

    monkeypatch.setattr(store, "_REDIS", FakeRedis())

    private_01 = _private_dp("dp-priv-01")
    private_02 = _private_dp("dp-priv-02")

    async def _private_map():
        return {private_01.id: private_01, private_02.id: private_02}

    monkeypatch.setattr("routes.market._load_private_demand_points", _private_map)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ask_body = MarketOfferCreate(
            side="ask",
            role="farmer",
            farm_id="farm-002",
            demand_point_id="dp-priv-01",
            crop_type="tomato",
            quantity_kg=500,
            price_per_kg=21,
        )
        resp = await client.post("/api/market/offer", json=ask_body.model_dump())
        assert resp.status_code == 200
        offer_id = resp.json()["offer"]["id"]
        assert offer_id.startswith("market-ask-")

        bid_body = MarketOfferCreate(
            side="bid",
            role="buyer",
            buyer_name="Demo Restaurant",
            demand_point_id="dp-priv-02",
            crop_type="onion",
            quantity_kg=400,
            price_per_kg=17,
        )
        bid_resp = await client.post("/api/market/offer", json=bid_body.model_dump())
        assert bid_resp.status_code == 200
        bid_id = bid_resp.json()["offer"]["id"]

        resp = await client.get("/api/market/offers")
        assert resp.status_code == 200
        offers = resp.json()["offers"]
        assert any(o["id"] == offer_id for o in offers)

        accept_resp = await client.post(
            "/api/market/accept",
            json={"offer_id": offer_id},
        )
        assert accept_resp.status_code == 200
        data = accept_resp.json()
        assert data["commitment"]["farm_id"] == "farm-002"
        assert data["farmer_commitment"]["demand_point_id"] == "dp-priv-01"

        bad = await client.post("/api/market/accept", json={"offer_id": bid_id})
        assert bad.status_code == 422

        good = await client.post(
            "/api/market/accept",
            json={"offer_id": bid_id, "farm_id": "farm-006"},
        )
        assert good.status_code == 200
        assert good.json()["commitment"]["farm_id"] == "farm-006"


def test_logistics_buyer_first_still_works():
    """Backward compat: _order_dps_buyer_first without market commitments."""
    dps = [_apmc_dp("dp-apmc-1"), _private_dp("dp-priv-01"), _private_dp("dp-priv-02")]
    ordered = logistics_mod._order_dps_buyer_first(dps, _POSTS)
    assert ordered[0].id == "dp-priv-02"
    assert ordered[1].id == "dp-priv-01"
    assert ordered[2].type == "apmc"
