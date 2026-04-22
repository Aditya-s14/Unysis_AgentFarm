"""Abstract base class shared by every AgentFarm agent."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import structlog


class BaseAgent(ABC):
    """Base class for all agents.

    Subclasses implement :meth:`execute`, which mutates and returns the
    shared :class:`src.orchestrator.state_manager.AgentFarmState` dict.
    """

    def __init__(self, name: str, llm: Optional[Any] = None) -> None:
        self.name = name
        self.llm = llm
        self.tools: List[Any] = []
        self.logger: structlog.stdlib.BoundLogger = structlog.get_logger(agent=name)

    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent against the shared state and return the updated state."""

    async def run_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Look up a tool by name, invoke it, log its duration and errors."""

        tool = next((t for t in self.tools if getattr(t, "name", None) == tool_name), None)
        if tool is None:
            self.logger.error("tool_not_found", tool=tool_name)
            raise KeyError(f"Tool not registered: {tool_name}")

        start = time.perf_counter()
        try:
            fn = getattr(tool, "run", tool)
            result = await fn(**kwargs) if callable(fn) else None
        except Exception as exc:
            self.logger.exception("tool_error", tool=tool_name, error=str(exc))
            raise
        duration_ms = (time.perf_counter() - start) * 1000.0
        self.logger.info("tool_ok", tool=tool_name, duration_ms=round(duration_ms, 2))
        return result

    def _append_trace(self, state: Dict[str, Any], step: str, data: Dict[str, Any]) -> None:
        """Append a structured trace entry to ``state['agent_traces']``."""

        state.setdefault("agent_traces", []).append(
            {"agent": self.name, "step": step, "data": data}
        )
