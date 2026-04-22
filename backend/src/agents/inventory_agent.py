"""Inventory Agent — spoilage risk and at-risk stock prioritisation."""

from __future__ import annotations

from typing import Any, Dict

from ..services.inventory_service import InventoryService
from .base_agent import BaseAgent


class InventoryAgent(BaseAgent):
    """Writes ``at_risk_stock`` on the state.

    TODO:
      * compute spoilage window using CROP_SHELF_LIFE * temp_factor
      * weight by days_since_harvest + upcoming weather risk
      * LLM (temperature=0) to rank priorities
    """

    def __init__(self, inventory_service: InventoryService | None = None) -> None:
        super().__init__(name="inventory_agent")
        self._inventory = inventory_service or InventoryService()

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("inventory_agent_start")
        state["at_risk_stock"] = state.get("at_risk_stock", [])

        self._append_trace(
            state,
            step="compute_at_risk",
            data={"at_risk_count": len(state["at_risk_stock"])},
        )
        return state
