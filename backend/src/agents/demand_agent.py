"""Demand Agent — 7-day demand forecast with festival + outcome adjustments."""

from __future__ import annotations

from typing import Any, Dict

from ..services.demand_service import DemandService
from .base_agent import BaseAgent


class DemandAgent(BaseAgent):
    """Writes ``demand_forecast`` on the state.

    TODO:
      * for each demand point, pull base_demand, apply festival multipliers,
        heatwave adjustments, and past-outcome corrections
      * single LLM call (temperature=0) for narrative rationale
      * skip if no demand change detected (conditional edge in graph)
    """

    def __init__(self, demand_service: DemandService | None = None) -> None:
        super().__init__(name="demand_agent")
        self._demand = demand_service or DemandService()

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(
            "demand_agent_start", demand_points=len(state.get("demand_points", []))
        )
        state["demand_forecast"] = state.get("demand_forecast", {})

        self._append_trace(
            state,
            step="forecast_demand",
            data={"demand_points": len(state.get("demand_points", []))},
        )
        return state
