"""Capacitated VRP with OR-Tools (PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH) + greedy fallback."""

from __future__ import annotations

import logging
from datetime import time

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


def _try_ortools(
    distance_matrix_km: list[list[float]],
    demands: list[int],
    trucks: list[Truck],
    time_limit_s: int,
    farms: list[Farm],
    demand_points: list[DemandPoint],
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
    )
    if plan is not None and any(r.stops for r in plan.routes):
        return plan

    logger.warning("OR-Tools returned no usable plan; using greedy fallback")
    return _greedy_route_plan(
        distance_matrix,
        demands,
        trucks,
        farms,
        demand_points,
    )
