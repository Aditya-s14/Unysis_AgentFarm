"""D4 routing helpers — DP ordering, VRP demand boost inputs, guaranteed pickup injection."""

from __future__ import annotations

import logging
import math

from models.schemas import (
    AtRiskStock,
    BuyerDemandPost,
    DemandPoint,
    Farm,
    MarketAcceptedCommitment,
    Route,
    RoutePlan,
    RouteStop,
    Truck,
)

logger = logging.getLogger(__name__)

# A single truck cannot legally cover more than ~14 h × 50 km/h in a day
# (mirrors vrp_solver._MAX_ROUTE_KM). A direct farm→buyer commitment longer
# than this needs a relay / multi-day handling, not a one-truck day trip.
_MAX_GUARANTEED_KM = 700.0


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def order_dps_market_first(
    dps: list,
    buyer_demands: list[BuyerDemandPost] | None = None,
    market_commitments: list[MarketAcceptedCommitment] | None = None,
) -> list:
    """Sort demand points: market commitment DPs → buyer posts → private → apmc → retail."""
    posts = buyer_demands or []
    commitments = market_commitments or []
    private_ids_with_commitments = {c.demand_point_id for c in commitments}
    private_ids_with_posts = {p.demand_point_id for p in posts}

    def sort_key(dp) -> int:
        if dp.type == "private" and dp.id in private_ids_with_commitments:
            return 0
        if dp.type == "private" and dp.id in private_ids_with_posts:
            return 1
        if dp.type == "private":
            return 2
        if dp.type == "apmc":
            return 3
        return 4

    return sorted(dps, key=sort_key)


def market_committed_qty_at_dp(
    dp: DemandPoint,
    market_commitments: list[MarketAcceptedCommitment] | None,
) -> float:
    if not market_commitments or dp.type != "private":
        return 0.0
    return sum(c.quantity_kg for c in market_commitments if c.demand_point_id == dp.id)


def overlay_market_farm_to_dp(
    mapping: dict[str, str],
    market_commitments: list[MarketAcceptedCommitment] | None,
) -> dict[str, str]:
    """Authoritative farm→DP overlay for accepted market commitments."""
    if not market_commitments:
        return mapping
    out = dict(mapping)
    for c in market_commitments:
        out[c.farm_id] = c.demand_point_id
    return out


def _commitment_satisfied(route_plan: RoutePlan, farm_id: str, dp_id: str) -> bool:
    for route in route_plan.routes:
        stops = sorted(route.stops, key=lambda s: s.sequence)
        farm_seq: int | None = None
        dp_seq: int | None = None
        for stop in stops:
            if stop.demand_point_id is None and stop.label == farm_id:
                farm_seq = stop.sequence
            if stop.demand_point_id == dp_id:
                dp_seq = stop.sequence
        if farm_seq is not None and dp_seq is not None and dp_seq >= farm_seq:
            return True
    return False


def _route_load_kg(route: Route) -> float:
    return sum(s.load_kg or 0 for s in route.stops)


def _pick_truck_for_guaranteed(
    trucks: list[Truck],
    route_plan: RoutePlan,
    quantity_kg: float,
) -> tuple[Truck | None, str | None]:
    """Pick an UNUSED truck for a dedicated guaranteed route.

    A guaranteed pickup is a separate physical trip, so it must use a truck
    not already assigned elsewhere — reusing an assigned truck would double-
    book one vehicle onto two simultaneous routes. When every truck is
    already committed we return None so the caller flags the commitment for
    manual handling rather than fabricating an impossible route.
    """
    if not trucks:
        return None, "no trucks available"

    used_ids = {r.truck_id for r in route_plan.routes}
    unused = [t for t in trucks if t.id not in used_ids]
    if not unused:
        return None, (
            "all trucks already assigned — cannot add a guaranteed pickup "
            "without double-booking a vehicle"
        )

    fitting = [t for t in unused if t.capacity_kg >= quantity_kg]
    if fitting:
        return min(fitting, key=lambda t: t.capacity_kg), None

    biggest = max(unused, key=lambda t: t.capacity_kg)
    return biggest, (
        f"over-capacity: unused truck {biggest.id} ({biggest.capacity_kg:.0f} kg) "
        f"for committed {quantity_kg:.0f} kg"
    )


def _farm_load_kg(farm_id: str, at_risk_stock: list[AtRiskStock]) -> float:
    kg = sum(s.kg_at_risk for s in at_risk_stock if s.farm_id == farm_id)
    return max(kg, 1.0)


def _build_guaranteed_route(
    commitment: MarketAcceptedCommitment,
    farm: Farm,
    dp: DemandPoint,
    truck: Truck,
    at_risk_stock: list[AtRiskStock],
) -> Route:
    load_kg = _farm_load_kg(commitment.farm_id, at_risk_stock)
    dist_km = _haversine_km(farm.lat, farm.lng, dp.lat, dp.lng)
    return Route(
        truck_id=truck.id,
        distance_km=round(dist_km, 3),
        stops=[
            RouteStop(
                sequence=0,
                lat=farm.lat,
                lng=farm.lng,
                label=farm.id,
                load_kg=load_kg,
            ),
            RouteStop(
                sequence=1,
                lat=dp.lat,
                lng=dp.lng,
                demand_point_id=dp.id,
                label=dp.id,
            ),
        ],
    )


def ensure_guaranteed_routes(
    route_plan: RoutePlan,
    market_commitments: list[MarketAcceptedCommitment] | None,
    farms: list[Farm],
    demand_points: list[DemandPoint],
    trucks: list[Truck],
    at_risk_stock: list[AtRiskStock],
) -> tuple[int, list[str]]:
    """Inject dedicated farm→DP routes when VRP missed a market commitment.

    Returns (injected_count, warning_messages).
    """
    if not market_commitments:
        return 0, []

    farm_by_id = {f.id: f for f in farms}
    dp_by_id = {d.id: d for d in demand_points}
    injected = 0
    warnings: list[str] = []

    for commitment in market_commitments:
        if _commitment_satisfied(route_plan, commitment.farm_id, commitment.demand_point_id):
            continue

        farm = farm_by_id.get(commitment.farm_id)
        dp = dp_by_id.get(commitment.demand_point_id)
        if farm is None:
            warnings.append(f"missing farm {commitment.farm_id!r} for guaranteed route")
            continue
        if dp is None:
            warnings.append(
                f"missing demand point {commitment.demand_point_id!r} for guaranteed route",
            )
            continue

        # A one-truck day trip can't legally cover an arbitrarily long direct
        # haul. Flag such commitments for manual/multi-day handling instead of
        # injecting an illegal route that looks dispatchable.
        direct_km = _haversine_km(farm.lat, farm.lng, dp.lat, dp.lng)
        if direct_km > _MAX_GUARANTEED_KM:
            warnings.append(
                f"guaranteed pickup farm={commitment.farm_id} dp={commitment.demand_point_id} "
                f"is {direct_km:.0f} km (> {_MAX_GUARANTEED_KM:.0f} km legal day trip) — "
                "needs relay/multi-day handling, not auto-routed"
            )
            logger.warning(
                "ensure_guaranteed_routes: commitment farm=%s dp=%s exceeds legal day trip (%.0f km); skipping",
                commitment.farm_id, commitment.demand_point_id, direct_km,
            )
            continue

        truck, warn = _pick_truck_for_guaranteed(trucks, route_plan, commitment.quantity_kg)
        if truck is None:
            warnings.append(
                f"no truck for guaranteed pickup farm={commitment.farm_id} dp={commitment.demand_point_id}",
            )
            continue
        if warn:
            warnings.append(warn)
            logger.warning("ensure_guaranteed_routes: %s", warn)

        route_plan.routes.append(
            _build_guaranteed_route(commitment, farm, dp, truck, at_risk_stock),
        )
        injected += 1
        logger.info(
            "ensure_guaranteed_routes: injected farm=%s → dp=%s truck=%s",
            commitment.farm_id,
            commitment.demand_point_id,
            truck.id,
        )

    return injected, warnings
