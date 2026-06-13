"""Farmer pre-commitment contracts — eligibility and mandi aggregation."""

from __future__ import annotations

from datetime import date

from models.schemas import DemandPoint, Farm, FarmerCommitment
from tools.maps_api import haversine_km

FORECAST_WEIGHT = 0.6
COMMITMENT_WEIGHT = 1.0
COMMITMENT_DAYS_BEFORE_HARVEST = 7


def is_commitment_eligible(farm: Farm, today: date | None = None) -> bool:
    """True when harvest window starts within the next 7 days (inclusive)."""
    ref = today or date.today()
    days_until = (farm.harvest_window_start - ref).days
    return 0 <= days_until <= COMMITMENT_DAYS_BEFORE_HARVEST


def nearest_demand_point_id(farm: Farm, demand_points: list[DemandPoint]) -> str | None:
    """Return the id of the demand point closest to *farm* (haversine)."""
    if not demand_points:
        return None
    best = min(
        demand_points,
        key=lambda dp: haversine_km((farm.lat, farm.lng), (dp.lat, dp.lng)),
    )
    return best.id


def aggregate_commitments_by_mandi(
    commitments: list[FarmerCommitment],
    farms: list[Farm],
    demand_points: list[DemandPoint],
) -> dict[str, float]:
    """Sum committed tonnage per demand point id."""
    farm_by_id = {f.id: f for f in farms}
    totals: dict[str, float] = {}

    for c in commitments:
        if c.tonnage_kg <= 0:
            continue
        dp_id = c.demand_point_id
        if not dp_id:
            farm = farm_by_id.get(c.farm_id)
            if farm is None:
                continue
            dp_id = nearest_demand_point_id(farm, demand_points)
        if not dp_id:
            continue
        totals[dp_id] = totals.get(dp_id, 0.0) + c.tonnage_kg

    return totals
