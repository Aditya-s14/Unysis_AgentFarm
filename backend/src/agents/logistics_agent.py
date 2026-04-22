"""Logistics Agent — builds optimised routes via OR-Tools VRP."""

from __future__ import annotations

from typing import Any, Dict

from ..services.logistics_service import LogisticsService
from .base_agent import BaseAgent


class LogisticsAgent(BaseAgent):
    """Writes ``route_plan`` on the state.

    TODO:
      * build distance matrix (routing_tools.build_distance_matrix)
      * construct VRPInput from farms, demand points, trucks
      * call :class:`LogisticsService.solve`
      * on validator retry, pass ``relaxation_factor > 1.0``
    """

    def __init__(self, logistics_service: LogisticsService | None = None) -> None:
        super().__init__(name="logistics_agent")
        self._logistics = logistics_service or LogisticsService()

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        retry = int(state.get("retry_count", 0))
        self.logger.info("logistics_agent_start", retry=retry)
        state["route_plan"] = state.get(
            "route_plan",
            {
                "routes": [],
                "unassigned_farms": [],
                "solver_status": "stub",
                "solver_runtime_ms": 0.0,
            },
        )

        self._append_trace(
            state,
            step="solve_vrp",
            data={"retry": retry, "routes": len(state["route_plan"].get("routes", []))},
        )
        return state
