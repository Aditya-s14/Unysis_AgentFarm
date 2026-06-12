"""Capacitated VRP with OR-Tools (PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH) + greedy fallback."""

from __future__ import annotations

import logging
from datetime import time
from itertools import permutations

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from config import get_settings
from models.schemas import (
    AtRiskStock,
    DemandPoint,
    Farm,
    Route,
    RoutePlan,
    RouteStop,
    Truck,
)

logger = logging.getLogger(__name__)


def _demand_at_farm(farm: Farm, at_risk: list[AtRiskStock]) -> int:
    kg = sum(s.kg_at_risk for s in at_risk if s.farm_id == farm.id)
    return max(1, min(int(kg), 50_000))


def _demand_at_dp(dp: DemandPoint) -> int:
    return max(1, int(dp.base_demand_per_day / 50))


def _build_demands(
    farms: list[Farm],
    demand_points: list[DemandPoint],
    at_risk_stock: list[AtRiskStock],
    *,
    demand_scale: float = 1.0,
) -> list[int]:
    scale = max(0.1, min(1.0, demand_scale))
    n = 1 + len(farms) + len(demand_points)
    demands = [0] * n
    for i, farm in enumerate(farms):
        demands[1 + i] = max(1, int(_demand_at_farm(farm, at_risk_stock) * scale))
    for j, dp in enumerate(demand_points):
        demands[1 + len(farms) + j] = max(1, int(_demand_at_dp(dp) * scale))
    return demands


def _node_coord_index(
    farms: list[Farm],
    demand_points: list[DemandPoint],
    idx: int,
) -> tuple[float, float, str | None, str | None]:
    """Return (lat, lng, farm_id, demand_point_id) for matrix index."""
    if idx == 0:
        return 0.0, 0.0, None, None
    if 1 <= idx <= len(farms):
        f = farms[idx - 1]
        return f.lat, f.lng, f.id, None
    j = idx - 1 - len(farms)
    dp = demand_points[j]
    return dp.lat, dp.lng, None, dp.id


_MAX_ROUTE_KM = 14.0 * 50.0  # legal drive limit × conservative speed (km)
# Drop penalties (km-equivalent per unserved stop). Urgent stock costs far
# more to abandon, so when capacity forces drops the solver sacrifices
# comfortable farms first. Mandis are delivery anchors — never worth dropping.
_DROP_PENALTY_URGENT_KM = 10_000.0   # <12 h to spoilage
_DROP_PENALTY_SOON_KM = 6_000.0      # <48 h
_DROP_PENALTY_AT_RISK_KM = 3_000.0   # flagged at-risk, >=48 h
_DROP_PENALTY_SAFE_KM = 1_000.0      # not at risk
_DROP_PENALTY_MANDI_KM = 10_000.0


def _drop_penalty_km(
    node: int,
    farms: list[Farm],
    at_risk_by_farm: dict[str, AtRiskStock],
) -> float:
    if node > len(farms):
        return _DROP_PENALTY_MANDI_KM
    stock = at_risk_by_farm.get(farms[node - 1].id)
    if stock is None:
        return _DROP_PENALTY_SAFE_KM
    hours = stock.hours_until_spoilage
    if hours is None:
        return _DROP_PENALTY_AT_RISK_KM
    if hours <= 12.0:
        return _DROP_PENALTY_URGENT_KM
    if hours <= 48.0:
        return _DROP_PENALTY_SOON_KM
    return _DROP_PENALTY_AT_RISK_KM


def _try_ortools(
    distance_matrix_km: list[list[float]],
    demands: list[int],
    trucks: list[Truck],
    time_limit_s: int,
    farms: list[Farm],
    demand_points: list[DemandPoint],
    at_risk_stock: list[AtRiskStock] | None = None,
) -> RoutePlan | None:
    n = len(distance_matrix_km)
    if n < 2 or len(trucks) == 0:
        return None
    num_vehicles = min(len(trucks), n - 1)
    depot = 0
    # Integer meters for OR-Tools (positive transits)
    matrix_m = [
        [max(1, int(distance_matrix_km[i][j] * 1000)) for j in range(n)] for i in range(n)
    ]

    capacities = [max(1, int(trucks[i].capacity_kg)) for i in range(num_vehicles)]

    manager = pywrapcp.RoutingIndexManager(n, num_vehicles, depot)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        fn = manager.IndexToNode(from_index)
        tn = manager.IndexToNode(to_index)
        return matrix_m[fn][tn]

    transit_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_index)

    def demand_callback(from_index: int) -> int:
        return demands[manager.IndexToNode(from_index)]

    demand_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_index,
        0,
        capacities,
        True,
        "Capacity",
    )

    max_route_m = int(_MAX_ROUTE_KM * 1000)
    routing.AddDimension(
        transit_index,
        0,
        max_route_m,
        True,
        "Distance",
    )

    # Without disjunctions, CVRP demands full coverage: whenever regional
    # demand exceeds allocated capacity (or the drive cap), the model is
    # infeasible, OR-Tools returns nothing, and the cap-less greedy fallback
    # produces illegal 18h+ routes. Urgency-weighted drop penalties keep
    # coverage the overwhelming priority — and make the solver sacrifice
    # comfortable farms first when capacity genuinely runs out.
    at_risk_by_farm = {s.farm_id: s for s in (at_risk_stock or [])}
    for node in range(1, n):
        penalty_m = int(_drop_penalty_km(node, farms, at_risk_by_farm) * 1000)
        routing.AddDisjunction([manager.NodeToIndex(node)], penalty_m)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.FromSeconds(time_limit_s)

    sol = routing.SolveWithParameters(params)
    if not sol:
        return None

    routes_out: list[Route] = []
    total_km = 0.0
    for v in range(num_vehicles):
        idx = routing.Start(v)
        truck = trucks[v]
        stops: list[RouteStop] = []
        seq = 0
        dist_km = 0.0
        prev = depot
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node != depot:
                lat, lng, fid, did = _node_coord_index(
                    farms,
                    demand_points,
                    node,
                )
                stops.append(
                    RouteStop(
                        sequence=seq,
                        lat=lat,
                        lng=lng,
                        demand_point_id=did,
                        label=fid or did or str(node),
                    ),
                )
                dist_km += distance_matrix_km[prev][node]
                prev = node
                seq += 1
            idx = sol.Value(routing.NextVar(idx))
        routes_out.append(
            Route(
                truck_id=truck.id,
                stops=stops,
                distance_km=round(max(0.0, dist_km), 3) if stops else None,
            ),
        )
        total_km += dist_km

    return RoutePlan(
        routes=routes_out,
        objective_value=round(total_km, 3) if total_km else round(
            sol.ObjectiveValue() / 1000.0,
            3,
        ),
        notes="ortools",
    )


def _greedy_route_plan(
    distance_matrix_km: list[list[float]],
    demands: list[int],
    trucks: list[Truck],
    farms: list[Farm],
    demand_points: list[DemandPoint],
) -> RoutePlan:
    """Nearest-neighbor split across trucks when capacities allow; else round-robin."""
    n = len(distance_matrix_km)
    customers = list(range(1, n))
    customers.sort(key=lambda u: distance_matrix_km[0][u])

    num_vehicles = min(len(trucks), n - 1)
    capacities = [max(1, int(trucks[i].capacity_kg)) for i in range(num_vehicles)]

    assignments: list[list[int]] = [[] for _ in range(num_vehicles)]
    loads = [0] * num_vehicles
    for node in customers:
        placed = False
        order = sorted(
            range(num_vehicles),
            key=lambda v: distance_matrix_km[0][node],
        )
        for v in order:
            if loads[v] + demands[node] <= capacities[v]:
                assignments[v].append(node)
                loads[v] += demands[node]
                placed = True
                break
        if not placed:
            logger.warning(
                "greedy: node %d demand %d kg exceeds remaining capacity on all trucks",
                node,
                demands[node],
            )

    routes_out: list[Route] = []
    for v in range(num_vehicles):
        truck = trucks[v]
        stop_list = assignments[v]
        prev = 0
        dist_km = 0.0
        stops: list[RouteStop] = []
        seq = 0
        for node in stop_list:
            dist_km += distance_matrix_km[prev][node]
            lat, lng, fid, did = _node_coord_index(farms, demand_points, node)
            stops.append(
                RouteStop(
                    sequence=seq,
                    lat=lat,
                    lng=lng,
                    demand_point_id=did,
                    label=fid or did or str(node),
                ),
            )
            seq += 1
            prev = node
        routes_out.append(
            Route(
                truck_id=truck.id,
                stops=stops,
                distance_km=round(max(0.0, dist_km), 3) if stops else None,
            ),
        )

    return RoutePlan(
        routes=routes_out,
        objective_value=None,
        notes="greedy_nearest_mandi_fallback",
    )


def _stop_matrix_index(
    stop: RouteStop,
    farms: list[Farm],
    demand_points: list[DemandPoint],
) -> int | None:
    """Map a RouteStop back to its distance-matrix index (depot = 0)."""
    if stop.demand_point_id is None:
        for i, f in enumerate(farms):
            if f.id == stop.label:
                return 1 + i
        return None
    for j, d in enumerate(demand_points):
        if d.id == stop.demand_point_id:
            return 1 + len(farms) + j
    return None


# Brute-force ordering is exact and cheap for small groups: capped at
# 6! x 4! = 17,280 candidate sequences per route.
_MAX_BRUTE_FARMS = 6
_MAX_BRUTE_MANDIS = 4


def _path_km(
    order: tuple[int, ...] | list[int],
    distance_matrix_km: list[list[float]],
) -> float:
    prev = 0
    dist = 0.0
    for idx in order:
        dist += distance_matrix_km[prev][idx]
        prev = idx
    return dist


def _nn_order(
    indices: list[int],
    start: int,
    distance_matrix_km: list[list[float]],
) -> list[int]:
    """Nearest-neighbor chain through ``indices`` beginning at ``start``."""
    remaining = list(indices)
    out: list[int] = []
    cur = start
    while remaining:
        nxt = min(remaining, key=lambda i: distance_matrix_km[cur][i])
        remaining.remove(nxt)
        out.append(nxt)
        cur = nxt
    return out


def _best_partitioned_order(
    farm_idx: list[int],
    mandi_idx: list[int],
    distance_matrix_km: list[list[float]],
) -> list[int]:
    """Cheapest depot->farms->mandis sequence honoring the partition.

    Exact (brute force over both groups' permutations) when small enough,
    nearest-neighbor otherwise.
    """
    if (
        len(farm_idx) <= _MAX_BRUTE_FARMS
        and len(mandi_idx) <= _MAX_BRUTE_MANDIS
    ):
        best: list[int] | None = None
        best_km = float("inf")
        for fp in permutations(farm_idx):
            base_km = _path_km(fp, distance_matrix_km)
            if base_km >= best_km:
                continue
            for mp in permutations(mandi_idx):
                km = base_km
                prev = fp[-1] if fp else 0
                for idx in mp:
                    km += distance_matrix_km[prev][idx]
                    prev = idx
                if km < best_km:
                    best_km = km
                    best = list(fp) + list(mp)
        if best is not None:
            return best

    farms_part = _nn_order(farm_idx, 0, distance_matrix_km)
    start = farms_part[-1] if farms_part else 0
    return farms_part + _nn_order(mandi_idx, start, distance_matrix_km)


def _reorder_pickups_first(
    plan: RoutePlan,
    farms: list[Farm],
    demand_points: list[DemandPoint],
    distance_matrix_km: list[list[float]],
) -> RoutePlan:
    """Enforce farm pickups before mandi deliveries within each route.

    The CVRP models mandis as positive demand (capacity sizing), so the
    solver has no notion of pickup -> delivery direction and may interleave
    or even start a route at a mandi. Physically a truck must collect
    produce before it can deliver, so each route is re-sequenced to the
    cheapest farms-first-then-mandis order (exact for small routes, NN
    heuristic above the brute-force cap) and distance_km is recomputed.
    Truck <-> stop assignments are untouched.
    """
    total_km = 0.0
    for route in plan.routes:
        stops = sorted(route.stops, key=lambda s: s.sequence)
        by_idx: dict[int, RouteStop] = {}
        resolvable = True
        for s in stops:
            idx = _stop_matrix_index(s, farms, demand_points)
            if idx is None:
                resolvable = False
                break
            by_idx[idx] = s

        if resolvable and len(by_idx) == len(stops) and stops:
            farm_idx = [i for i, s in by_idx.items() if s.demand_point_id is None]
            mandi_idx = [i for i, s in by_idx.items() if s.demand_point_id is not None]
            order = _best_partitioned_order(farm_idx, mandi_idx, distance_matrix_km)
            new_stops = [by_idx[i] for i in order]
            for seq, s in enumerate(new_stops):
                s.sequence = seq
            route.stops = new_stops
            route.distance_km = round(max(0.0, _path_km(order, distance_matrix_km)), 3)

        if route.distance_km:
            total_km += route.distance_km

    if plan.objective_value is not None and total_km:
        plan.objective_value = round(total_km, 3)
    return plan


def solve_vrp(
    farms: list[Farm],
    demand_points: list[DemandPoint],
    trucks: list[Truck],
    at_risk_stock: list[AtRiskStock],
    distance_matrix: list[list[float]],
    demand_scale: float = 1.0,
) -> RoutePlan:
    """
    CVRP on nodes ``[depot, *farms, *demand_points]`` (index 0 = depot).

    ``distance_matrix`` must be square ``(1 + len(farms) + len(demand_points))``. Depot row/col 0;
    distances in **km**. Uses OR-Tools with a **30s** limit (from ``vrp_time_limit`` settings),
    real truck capacities, a per-route distance cap, and ``demand_scale`` on retry; if no solution,
    uses greedy allocation.
    """
    expected = 1 + len(farms) + len(demand_points)
    if len(distance_matrix) != expected or any(len(row) != expected for row in distance_matrix):
        raise ValueError(
            f"distance_matrix must be {expected}x{expected} for current farms/demand_points",
        )

    demands = _build_demands(
        farms,
        demand_points,
        at_risk_stock,
        demand_scale=demand_scale,
    )
    tl = max(1, int(get_settings().vrp_time_limit))

    plan = _try_ortools(
        distance_matrix,
        demands,
        trucks,
        tl,
        farms,
        demand_points,
        at_risk_stock,
    )
    if plan is not None and any(r.stops for r in plan.routes):
        return _reorder_pickups_first(plan, farms, demand_points, distance_matrix)

    logger.warning("OR-Tools returned no usable plan; using greedy fallback")
    plan = _greedy_route_plan(
        distance_matrix,
        demands,
        trucks,
        farms,
        demand_points,
    )
    return _reorder_pickups_first(plan, farms, demand_points, distance_matrix)
