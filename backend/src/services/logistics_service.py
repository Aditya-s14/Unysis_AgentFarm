"""Logistics / VRP service — OR-Tools wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..config.logging_config import get_logger
from ..config.settings import get_settings

logger = get_logger(__name__)


@dataclass
class VRPInput:
    """Inputs for the capacitated VRP with time windows."""

    distance_matrix: List[List[int]]
    demands: List[int]
    vehicle_capacities: List[int]
    num_vehicles: int
    depot_index: int = 0
    time_windows: List[tuple[int, int]] = field(default_factory=list)
    service_times: List[int] = field(default_factory=list)


@dataclass
class VRPResult:
    """VRP solution summary."""

    status: str
    routes: List[List[int]] = field(default_factory=list)
    total_distance: int = 0
    total_load: int = 0
    runtime_ms: float = 0.0
    infeasible: bool = False


class LogisticsService:
    """Wraps OR-Tools CVRPTW solving.

    Uses ``PATH_CHEAPEST_ARC`` for first-solution and
    ``GUIDED_LOCAL_SEARCH`` for local search, capped at
    :attr:`Settings.VRP_TIME_LIMIT` seconds.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    async def solve(
        self, problem: VRPInput, relaxation_factor: float = 1.0
    ) -> VRPResult:
        """Solve the VRP and return a :class:`VRPResult`.

        TODO:
          * build RoutingIndexManager + RoutingModel
          * register transit / capacity / time-window callbacks
          * apply ``relaxation_factor`` to capacities on validator retry
          * return parsed routes
        """

        logger.info(
            "vrp_solve_stub",
            vehicles=problem.num_vehicles,
            nodes=len(problem.demands),
            time_limit=self._settings.VRP_TIME_LIMIT,
            relaxation=relaxation_factor,
        )
        return VRPResult(status="STUB", routes=[], total_distance=0, total_load=0)

    async def validate_solution(
        self, result: VRPResult, constraints: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Hook used by the Validator node."""

        return result.status != "STUB" and not result.infeasible
