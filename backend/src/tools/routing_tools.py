"""Routing helpers — distance math and distance matrix stubs."""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from ..utils.constants import HAVERSINE_ROAD_FACTOR

Coord = Tuple[float, float]


def haversine_km(a: Coord, b: Coord) -> float:
    """Return great-circle distance in kilometres between two lat/lng points."""

    r = 6371.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(h))
    return r * c


def road_distance_km(a: Coord, b: Coord, road_factor: float = HAVERSINE_ROAD_FACTOR) -> float:
    """Haversine distance scaled by a road detour factor."""

    return haversine_km(a, b) * road_factor


def build_distance_matrix(points: Sequence[Coord]) -> List[List[float]]:
    """Build an N x N road-distance matrix for ``points``."""

    n = len(points)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = road_distance_km(points[i], points[j])
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix
