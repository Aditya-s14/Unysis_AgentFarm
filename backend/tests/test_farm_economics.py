"""Tests for D3 farm economics calculator."""

from __future__ import annotations

from datetime import date, datetime, time, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from agents.metrics import _demand_matching_waste, _routed_farm_to_dp
from main import app
from models.schemas import (
    AtRiskStock,
    DemandPoint,
    Farm,
    PriceOfferAcceptance,
    Route,
    RoutePlan,
    RouteStop,
    Truck,
)
from tools.farm_economics import (
    _farm_logistics_share,
    _per_farm_waste_kg,
    compute_farm_economics,
)


def _farm(farm_id: str = "farm-001", *, lat: float = 13.0827, lng: float = 77.5439) -> Farm:
    return Farm(
        id=farm_id,
        name=f"Farm {farm_id}",
        lat=lat,
        lng=lng,
        crop_type="tomato",
        acreage=8.0,
        typical_yield_kg=1200.0,
        harvest_window_start=date(2026, 6, 15),
        harvest_window_end=date(2026, 7, 30),
    )


def _demand_points() -> list[DemandPoint]:
    return [
        DemandPoint(
            id="dp-apmc-01",
            name="Yeshwanthpur APMC",
            lat=13.0280,
            lng=77.5366,
            type="apmc",
            base_demand_per_day=5000,
        ),
        DemandPoint(
            id="dp-priv-01",
            name="Reliance Fresh DC",
            lat=18.5018,
            lng=73.8745,
            type="private",
            base_demand_per_day=1200,
        ),
    ]


def _truck(truck_id: str = "tr-001", *, cost_per_km: float = 28.5) -> Truck:
    return Truck(
        id=truck_id,
        capacity_kg=1000,
        cost_per_km=cost_per_km,
        availability_start=time(5, 30),
        availability_end=time(20, 0),
    )


def _route_with_farms(farm_ids: list[str], *, distance_km: float = 100.0) -> RoutePlan:
    stops = [
        RouteStop(sequence=i, lat=13.0, lng=77.5, label=fid)
        for i, fid in enumerate(farm_ids)
    ]
    stops.append(
        RouteStop(
            sequence=len(farm_ids),
            lat=13.028,
            lng=77.536,
            demand_point_id="dp-apmc-01",
        ),
    )
    return RoutePlan(
        routes=[
            Route(
                truck_id="tr-001",
                stops=stops,
                distance_km=distance_km,
            ),
        ],
    )


def test_logistics_allocation_sums_to_route_cost():
    farms = [_farm("farm-a"), _farm("farm-b")]
    at_risk = [
        AtRiskStock(farm_id="farm-a", crop_type="tomato", kg_at_risk=600),
        AtRiskStock(farm_id="farm-b", crop_type="tomato", kg_at_risk=400),
    ]
    at_risk_by_farm = {s.farm_id: s.kg_at_risk for s in at_risk}
    route_plan = _route_with_farms(["farm-a", "farm-b"], distance_km=50.0)
    trucks = [_truck(cost_per_km=20.0)]

    shares = _farm_logistics_share(route_plan, trucks, at_risk_by_farm)
    expected_total = 50.0 * 20.0
    assert shares["farm-a"] == pytest.approx(expected_total * 0.6)
    assert shares["farm-b"] == pytest.approx(expected_total * 0.4)
    assert sum(shares.values()) == pytest.approx(expected_total)


def test_per_farm_waste_sums_to_aggregate():
    farms = [_farm("farm-a"), _farm("farm-b")]
    dps = _demand_points()
    at_risk = [
        AtRiskStock(farm_id="farm-a", crop_type="tomato", kg_at_risk=800),
        AtRiskStock(farm_id="farm-b", crop_type="tomato", kg_at_risk=600),
    ]
    route_plan = _route_with_farms(["farm-a", "farm-b"])
    dp_daily = {dp.id: dp.base_demand_per_day for dp in dps}
    fake_state = {"route_plan": route_plan}
    farm_to_dp = _routed_farm_to_dp(fake_state, farms, dps)
    per_farm = _per_farm_waste_kg(at_risk, farm_to_dp, dp_daily)
    aggregate, _ = _demand_matching_waste(at_risk, farm_to_dp, dp_daily)
    assert sum(per_farm.values()) == pytest.approx(aggregate)


def test_switch_to_direct_when_apmc_logistics_high():
    import tools.price_discovery as pd

    pd._CROP_PRICES = {"tomato": (20.0, 0.15)}

    farm = _farm()
    # Private DC near farm so direct logistics beat a long VRP leg.
    dps = [
        DemandPoint(
            id="dp-apmc-01",
            name="Yeshwanthpur APMC",
            lat=13.0280,
            lng=77.5366,
            type="apmc",
            base_demand_per_day=5000,
        ),
        DemandPoint(
            id="dp-priv-near",
            name="Local Fresh DC",
            lat=13.05,
            lng=77.55,
            type="private",
            base_demand_per_day=1200,
        ),
    ]
    trucks = [_truck(cost_per_km=50.0)]
    at_risk = [AtRiskStock(farm_id="farm-001", crop_type="tomato", kg_at_risk=1000)]
    route_plan = _route_with_farms(["farm-001"], distance_km=200.0)

    rows = compute_farm_economics(
        [farm], dps, trucks, at_risk, route_plan, acceptances={},
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.apmc_logistics_inr > row.direct_logistics_inr
    assert row.recommendation == "switch_to_direct"
    assert row.margin_delta_inr > 0


def test_direct_accepted_when_redis_acceptance():
    import tools.price_discovery as pd

    pd._CROP_PRICES = {"tomato": (20.0, 0.15)}

    farm = _farm()
    dps = _demand_points()
    trucks = [_truck()]
    at_risk = [AtRiskStock(farm_id="farm-001", crop_type="tomato", kg_at_risk=1000)]
    route_plan = _route_with_farms(["farm-001"], distance_km=10.0)
    acceptances = {
        "farm-001": PriceOfferAcceptance(
            farm_id="farm-001",
            crop_type="tomato",
            apmc_demand_point_id="dp-apmc-01",
            private_demand_point_id="dp-priv-01",
            accepted_price_per_kg=23.0,
            tonnage_kg=1000,
            accepted_at=datetime.now(timezone.utc),
        ),
    }

    rows = compute_farm_economics(
        [farm], dps, trucks, at_risk, route_plan, acceptances=acceptances,
    )
    assert rows[0].recommendation == "direct_accepted"


@pytest.mark.asyncio
async def test_farm_margins_api_round_trip(monkeypatch):
    import tools.price_discovery as pd

    pd._CROP_PRICES = {"tomato": (20.0, 0.15)}

    async def _empty_acceptances(farm_ids):
        return {}

    monkeypatch.setattr(
        "routes.economics.list_acceptances",
        _empty_acceptances,
    )

    farm = _farm()
    dps = _demand_points()
    trucks = [_truck()]
    at_risk = [AtRiskStock(farm_id="farm-001", crop_type="tomato", kg_at_risk=1000)]
    route_plan = _route_with_farms(["farm-001"], distance_km=30.0)

    body = {
        "farms": [farm.model_dump(mode="json")],
        "demand_points": [
            {
                "id": dp.id,
                "name": dp.name,
                "lat": dp.lat,
                "lng": dp.lng,
                "point_type": dp.type,
                "base_demand_per_day": dp.base_demand_per_day,
            }
            for dp in dps
        ],
        "trucks": [trucks[0].model_dump(mode="json")],
        "at_risk_stock": [at_risk[0].model_dump(mode="json")],
        "route_plan": route_plan.model_dump(mode="json"),
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/economics/farm-margins", json=body)
        assert resp.status_code == 200
        rows = resp.json()["rows"]
        assert len(rows) == 1
        assert rows[0]["farm_id"] == "farm-001"
        assert "apmc_net_margin_inr" in rows[0]
        assert "direct_net_margin_inr" in rows[0]
