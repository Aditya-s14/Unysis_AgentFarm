"""Per-farm P&L: revenue − logistics − spoilage (D3 farm economics)."""

from __future__ import annotations

import logging
import math
from collections import defaultdict

from agents.metrics import _routed_farm_to_dp
from models.schemas import (
    AtRiskStock,
    DemandPoint,
    Farm,
    FarmEconomicsRow,
    PriceOfferAcceptance,
    RoutePlan,
    Truck,
)
from tools.price_discovery import build_price_quote, nearest_demand_point

logger = logging.getLogger(__name__)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _per_farm_waste_kg(
    at_risk: list[AtRiskStock],
    farm_to_dp: dict[str, str],
    dp_daily_demand: dict[str, float],
) -> dict[str, float]:
    """Waste kg per farm using the same demand-cap formula as KPI optimized waste."""
    dp_farm_count: dict[str, int] = defaultdict(int)
    for stock in at_risk:
        dp_id = farm_to_dp.get(stock.farm_id)
        if dp_id:
            dp_farm_count[dp_id] += 1

    waste_by_farm: dict[str, float] = {}
    for stock in at_risk:
        dp_id = farm_to_dp.get(stock.farm_id)
        if dp_id is None:
            waste_by_farm[stock.farm_id] = stock.kg_at_risk
            continue
        n = dp_farm_count[dp_id]
        daily_demand = dp_daily_demand.get(dp_id, 0.0)
        deliverable = min(stock.kg_at_risk, daily_demand / max(n, 1))
        waste_by_farm[stock.farm_id] = max(stock.kg_at_risk - deliverable, 0.0)
    return waste_by_farm


def _farm_logistics_share(
    route_plan: RoutePlan | None,
    trucks: list[Truck],
    at_risk_by_farm: dict[str, float],
) -> dict[str, float]:
    """Allocate each route's total ₹ cost across farms by kg_at_risk share.

    Uses ``Route.distance_km`` (schemas.Route) × ``Truck.cost_per_km``.
    """
    truck_by_id = {t.id: t for t in trucks}
    logistics: dict[str, float] = {}

    if not route_plan:
        return logistics

    for route in route_plan.routes:
        truck = truck_by_id.get(route.truck_id)
        if truck is None:
            continue

        # Route.distance_km is set by vrp_solver; None must not inflate direct-switch recs.
        if route.distance_km is None:
            logger.warning(
                "farm_economics: route truck=%s missing distance_km; treating as 0",
                route.truck_id,
            )
        distance_km = route.distance_km if route.distance_km is not None else 0.0
        route_cost_inr = distance_km * truck.cost_per_km

        farm_ids = [
            s.label for s in route.stops
            if s.demand_point_id is None and s.label
        ]
        total_kg = sum(at_risk_by_farm.get(fid, 0.0) for fid in farm_ids)
        if total_kg <= 0:
            continue

        for farm_id in farm_ids:
            kg = at_risk_by_farm.get(farm_id, 0.0)
            logistics[farm_id] = logistics.get(farm_id, 0.0) + route_cost_inr * (kg / total_kg)

    return logistics


def _farm_truck_map(route_plan: RoutePlan | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not route_plan:
        return mapping
    for route in route_plan.routes:
        for stop in route.stops:
            if stop.demand_point_id is None and stop.label:
                mapping[stop.label] = route.truck_id
    return mapping


def _direct_logistics_inr(
    farm: Farm,
    demand_points: list[DemandPoint],
    truck: Truck | None,
) -> float:
    """Demo estimate: round-trip haversine to nearest private DC × cost_per_km.

    Intentionally simplified for hackathon demo — not a bug if direct logistics
    differs from multi-stop VRP legs.
    """
    private = nearest_demand_point(farm, demand_points, "private")
    if private is None or truck is None:
        return 0.0
    one_way_km = _haversine_km(farm.lat, farm.lng, private.lat, private.lng)
    return round(2.0 * one_way_km * truck.cost_per_km, 2)


def compute_farm_economics(
    farms: list[Farm],
    demand_points: list[DemandPoint],
    trucks: list[Truck],
    at_risk_stock: list[AtRiskStock],
    route_plan: RoutePlan | None,
    acceptances: dict[str, PriceOfferAcceptance] | None = None,
) -> list[FarmEconomicsRow]:
    """Return per-farm economics rows for at-risk farms with price quotes."""
    if not at_risk_stock:
        return []

    farm_by_id = {f.id: f for f in farms}
    at_risk_by_farm = {s.farm_id: s.kg_at_risk for s in at_risk_stock}
    truck_by_id = {t.id: t for t in trucks}
    accepted = acceptances or {}

    dp_daily_demand = {dp.id: dp.base_demand_per_day for dp in demand_points}
    fake_state = {"route_plan": route_plan or RoutePlan()}
    farm_to_dp = _routed_farm_to_dp(fake_state, farms, demand_points)
    waste_by_farm = _per_farm_waste_kg(at_risk_stock, farm_to_dp, dp_daily_demand)
    apmc_logistics = _farm_logistics_share(route_plan, trucks, at_risk_by_farm)
    farm_truck = _farm_truck_map(route_plan)

    rows: list[FarmEconomicsRow] = []

    for stock in at_risk_stock:
        farm = farm_by_id.get(stock.farm_id)
        if farm is None:
            continue

        quote = build_price_quote(farm, demand_points)
        if quote is None:
            continue

        waste_kg = waste_by_farm.get(stock.farm_id, 0.0)
        sold_kg = max(0.0, stock.kg_at_risk - waste_kg)

        apmc_rev = round(quote.apmc_price_per_kg * sold_kg, 2)
        apmc_log = round(apmc_logistics.get(stock.farm_id, 0.0), 2)
        apmc_spoil = round(waste_kg * quote.apmc_price_per_kg, 2)
        apmc_net = round(apmc_rev - apmc_log - apmc_spoil, 2)

        truck = truck_by_id.get(farm_truck.get(stock.farm_id, ""))
        direct_log = _direct_logistics_inr(farm, demand_points, truck)

        direct_rev = round(quote.private_offer_per_kg * sold_kg, 2)
        direct_spoil = round(waste_kg * quote.private_offer_per_kg, 2)
        direct_net = round(direct_rev - direct_log - direct_spoil, 2)

        margin_delta = round(direct_net - apmc_net, 2)

        if stock.farm_id in accepted:
            acc = accepted[stock.farm_id]
            channel = getattr(acc, "channel", "private") or "private"
            recommendation = "direct_accepted" if channel == "private" else "apmc_accepted"
        elif apmc_net < direct_net:
            recommendation = "switch_to_direct"
        else:
            recommendation = "stay_apmc"

        rows.append(
            FarmEconomicsRow(
                farm_id=farm.id,
                farm_name=farm.name,
                crop_type=quote.crop_type,
                kg_at_risk=round(stock.kg_at_risk, 2),
                waste_kg=round(waste_kg, 2),
                sold_kg=round(sold_kg, 2),
                apmc_price_per_kg=quote.apmc_price_per_kg,
                apmc_revenue_inr=apmc_rev,
                apmc_logistics_inr=apmc_log,
                apmc_spoilage_inr=apmc_spoil,
                apmc_net_margin_inr=apmc_net,
                routed_demand_point_id=farm_to_dp.get(stock.farm_id),
                private_offer_per_kg=quote.private_offer_per_kg,
                private_buyer_name=quote.private_buyer_name,
                direct_revenue_inr=direct_rev,
                direct_logistics_inr=direct_log,
                direct_spoilage_inr=direct_spoil,
                direct_net_margin_inr=direct_net,
                margin_delta_inr=margin_delta,
                recommendation=recommendation,
                private_demand_point_id=quote.private_demand_point_id,
            ),
        )

    return sorted(rows, key=lambda r: r.farm_name)
