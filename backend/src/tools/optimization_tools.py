"""Optimization-adjacent helpers used by the VRP solver."""

from __future__ import annotations

from typing import Dict, List

from ..config.logging_config import get_logger

logger = get_logger(__name__)


def to_int_matrix(matrix: List[List[float]], scale: int = 1000) -> List[List[int]]:
    """Scale a float distance matrix to integers (OR-Tools expects ints)."""

    return [[int(round(v * scale)) for v in row] for row in matrix]


def greedy_assignment(
    supply: Dict[str, float], demand: Dict[str, float]
) -> Dict[str, Dict[str, float]]:
    """Naive greedy allocation from supply to demand nodes.

    TODO: use this for the baseline KPI computation.
    """

    allocation: Dict[str, Dict[str, float]] = {s: {} for s in supply}
    remaining_demand = dict(demand)
    for s_id, s_qty in supply.items():
        for d_id, d_qty in remaining_demand.items():
            if s_qty <= 0:
                break
            take = min(s_qty, d_qty)
            if take <= 0:
                continue
            allocation[s_id][d_id] = take
            s_qty -= take
            remaining_demand[d_id] -= take
    return allocation
