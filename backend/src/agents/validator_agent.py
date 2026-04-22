"""Validator Agent — rule-based plan feasibility checker (no LLM)."""

from __future__ import annotations

from typing import Any, Dict

from .base_agent import BaseAgent


class ValidatorAgent(BaseAgent):
    """Writes ``validation_result`` on the state.

    TODO:
      * check truck capacity vs assigned load
      * verify time windows (driver max 14h, availability windows)
      * ensure at-risk stock is prioritised
      * on failure, increment ``retry_count`` — orchestrator loops back
    """

    def __init__(self) -> None:
        super().__init__(name="validator_agent")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("validator_start")
        state["validation_result"] = state.get(
            "validation_result",
            {"is_valid": True, "violations": [], "warnings": []},
        )

        self._append_trace(
            state,
            step="validate_plan",
            data={
                "is_valid": state["validation_result"].get("is_valid", True),
                "violations": len(state["validation_result"].get("violations", [])),
            },
        )
        return state
