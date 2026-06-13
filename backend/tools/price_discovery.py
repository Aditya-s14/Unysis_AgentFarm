"""Real-time price discovery — APMC vs private buyer quotes per farm."""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from models.schemas import DemandPoint, Farm
from tools.db import resolve_data_dir

_CROP_PRICES: dict[str, tuple[float, float]] | None = None


@dataclass
class PriceQuote:
    farm_id: str
    farm_name: str
    crop_type: str
    tonnage_kg: float
    apmc_demand_point_id: str
    apmc_name: str
    apmc_price_per_kg: float
    private_demand_point_id: str
    private_buyer_name: str
    private_offer_per_kg: float
    premium_vs_apmc_pct: float
    estimated_payout_inr: float
    quote_as_of: str

    def to_dict(self) -> dict:
        return asdict(self)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    to_rad = math.radians
    d_lat = to_rad(lat2 - lat1)
    d_lng = to_rad(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(to_rad(lat1)) * math.cos(to_rad(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_demand_point(
    farm: Farm,
    demand_points: list[DemandPoint],
    point_type: str,
) -> DemandPoint | None:
    """Closest demand point of *point_type* (apmc / private / retail)."""
    candidates = [dp for dp in demand_points if dp.type == point_type]
    if not candidates:
        return None
    best = candidates[0]
    best_km = _haversine_km(farm.lat, farm.lng, best.lat, best.lng)
    for dp in candidates[1:]:
        km = _haversine_km(farm.lat, farm.lng, dp.lat, dp.lng)
        if km < best_km:
            best = dp
            best_km = km
    return best


def load_crop_prices() -> dict[str, tuple[float, float]]:
    """Return crop_type → (base_apmc_price_per_kg, private_premium_pct)."""
    global _CROP_PRICES
    if _CROP_PRICES is not None:
        return _CROP_PRICES

    path = resolve_data_dir() / "sample_crop_prices.csv"
    prices: dict[str, tuple[float, float]] = {}
    if path.is_file():
        with path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                crop = row["crop_type"].strip().lower()
                prices[crop] = (
                    float(row["base_apmc_price_per_kg"]),
                    float(row["private_premium_pct"]),
                )
    _CROP_PRICES = prices
    return prices


def _mandi_variance(apmc_id: str) -> float:
    """±3% variance by mandi index for demo realism."""
    try:
        n = int(apmc_id.rsplit("-", 1)[-1])
    except ValueError:
        n = 1
    return 1.0 + ((n % 7) - 3) * 0.01


def build_price_quote(farm: Farm, demand_points: list[DemandPoint]) -> PriceQuote | None:
    apmc = nearest_demand_point(farm, demand_points, "apmc")
    private = nearest_demand_point(farm, demand_points, "private")
    if apmc is None or private is None:
        return None

    crop = farm.crop_type.strip().lower()
    price_table = load_crop_prices()
    base, premium_pct = price_table.get(crop, (20.0, 0.12))

    apmc_price = round(base * _mandi_variance(apmc.id), 2)
    private_offer = round(apmc_price * (1.0 + premium_pct), 2)
    premium = round((private_offer - apmc_price) / apmc_price * 100.0, 1) if apmc_price else 0.0
    tonnage = float(farm.typical_yield_kg)

    return PriceQuote(
        farm_id=farm.id,
        farm_name=farm.name,
        crop_type=crop,
        tonnage_kg=tonnage,
        apmc_demand_point_id=apmc.id,
        apmc_name=apmc.name,
        apmc_price_per_kg=apmc_price,
        private_demand_point_id=private.id,
        private_buyer_name=private.name,
        private_offer_per_kg=private_offer,
        premium_vs_apmc_pct=premium,
        estimated_payout_inr=round(private_offer * tonnage, 0),
        quote_as_of=datetime.now(timezone.utc).isoformat(),
    )


def build_price_board(
    farms: list[Farm],
    demand_points: list[DemandPoint],
) -> list[PriceQuote]:
    quotes: list[PriceQuote] = []
    for farm in farms:
        q = build_price_quote(farm, demand_points)
        if q is not None:
            quotes.append(q)
    return quotes
