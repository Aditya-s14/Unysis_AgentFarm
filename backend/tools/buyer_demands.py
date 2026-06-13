"""Direct buyer demand posts — aggregation helpers for demand agent and VRP."""

from __future__ import annotations

from models.schemas import BuyerDemandPost


def stable_post_id(demand_point_id: str, crop_type: str) -> str:
    """Deterministic id for upsert + DELETE by post_id."""
    return f"buyer-{demand_point_id}-{crop_type.lower()}"


def aggregate_buyer_demand_by_mandi(posts: list[BuyerDemandPost]) -> dict[str, float]:
    """Sum posted quantity_kg per private demand point id."""
    totals: dict[str, float] = {}
    for p in posts:
        if p.quantity_kg <= 0:
            continue
        totals[p.demand_point_id] = totals.get(p.demand_point_id, 0.0) + p.quantity_kg
    return totals


def buyer_demand_for_crop(posts: list[BuyerDemandPost], dp_id: str, crop: str) -> float:
    """Crop-scoped sum of quantity_kg at a demand point."""
    crop_lower = crop.lower()
    return sum(
        p.quantity_kg
        for p in posts
        if p.demand_point_id == dp_id and p.crop_type.lower() == crop_lower
    )
