"""Tests for D1 price discovery board."""

from __future__ import annotations

import csv
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from models.schemas import DemandPoint, Farm, PriceOfferAcceptance
from tools.price_discovery import (
    build_price_board,
    build_price_quote,
    load_crop_prices,
    nearest_demand_point,
)

_CSV = __import__("pathlib").Path(__file__).resolve().parents[2] / "data" / "sample_crop_prices.csv"


def _farm(
    farm_id: str = "farm-001",
    *,
    lat: float = 13.0827,
    lng: float = 77.5439,
    crop: str = "tomato",
) -> Farm:
    return Farm(
        id=farm_id,
        name=f"Farm {farm_id}",
        lat=lat,
        lng=lng,
        crop_type=crop,
        acreage=8.0,
        typical_yield_kg=1200.0,
        harvest_window_start=date(2026, 6, 15),
        harvest_window_end=date(2026, 7, 30),
    )


def _demand_points() -> list[DemandPoint]:
    return [
        DemandPoint(
            id="dp-apmc-01",
            name="Yeshwanthpur APMC Yard",
            lat=13.0280,
            lng=77.5366,
            type="apmc",
            base_demand_per_day=2000,
        ),
        DemandPoint(
            id="dp-apmc-03",
            name="Hubli APMC Main Gate",
            lat=15.3647,
            lng=75.1239,
            type="apmc",
            base_demand_per_day=1800,
        ),
        DemandPoint(
            id="dp-priv-01",
            name="Reliance Fresh DC Pune",
            lat=18.5018,
            lng=73.8745,
            type="private",
            base_demand_per_day=1200,
        ),
        DemandPoint(
            id="dp-priv-03",
            name="Star Bazaar Hubli",
            lat=15.4021,
            lng=75.0777,
            type="private",
            base_demand_per_day=800,
        ),
    ]


def test_private_premium_mixed_by_crop():
    """Tomato/onion retain direct premium; mango/banana can discount vs APMC (D3 realism)."""
    import tools.price_discovery as pd

    pd._CROP_PRICES = None
    prices = load_crop_prices()
    dps = _demand_points()
    for crop in ("tomato", "onion"):
        q = build_price_quote(_farm(crop=crop), dps)
        assert q is not None
        assert q.private_offer_per_kg > q.apmc_price_per_kg
    for crop in ("mango", "banana"):
        q = build_price_quote(_farm(crop=crop), dps)
        assert q is not None
        assert q.private_offer_per_kg < q.apmc_price_per_kg


def test_build_price_quote_has_apmc_and_private_ids():
    q = build_price_quote(_farm(), _demand_points())
    assert q is not None
    assert q.apmc_demand_point_id.startswith("dp-apmc")
    assert q.private_demand_point_id.startswith("dp-priv")
    assert q.estimated_payout_inr == pytest.approx(q.private_offer_per_kg * q.tonnage_kg, rel=0.01)


def test_nearest_apmc_farm001_yeshwanthpur_region():
    farm = _farm("farm-001", lat=13.0827, lng=77.5439)
    dps = _demand_points()
    apmc = nearest_demand_point(farm, dps, "apmc")
    assert apmc is not None
    assert apmc.id == "dp-apmc-01"


def test_crop_prices_csv_has_four_crops():
    with _CSV.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 4
    crops = {r["crop_type"] for r in rows}
    assert crops == {"tomato", "onion", "banana", "mango"}


def test_build_price_board_count():
    farms = [_farm("farm-001"), _farm("farm-006", lat=19.9975, lng=73.7898, crop="onion")]
    board = build_price_board(farms, _demand_points())
    assert len(board) == 2


def test_accept_private_offer_idempotent(client):
    acceptance = PriceOfferAcceptance(
        farm_id="farm-001",
        crop_type="tomato",
        apmc_demand_point_id="dp-apmc-01",
        private_demand_point_id="dp-priv-01",
        accepted_price_per_kg=21.0,
        tonnage_kg=1200.0,
    )
    mock_saved = acceptance.model_copy()
    with patch(
        "routes.pricing.save_acceptance",
        new=AsyncMock(side_effect=[(mock_saved, True), (mock_saved, False)]),
    ), patch(
        "routes.pricing._load_farms_and_demand",
        new=AsyncMock(return_value=([_farm()], _demand_points())),
    ), patch(
        "routes.pricing.build_price_quote",
        return_value=build_price_quote(_farm(), _demand_points()),
    ):
        first = client.post("/api/price-board/accept", json=acceptance.model_dump())
        assert first.status_code == 200
        assert first.json()["accepted"] is True
        second = client.post("/api/price-board/accept", json=acceptance.model_dump())
        assert second.status_code == 409
