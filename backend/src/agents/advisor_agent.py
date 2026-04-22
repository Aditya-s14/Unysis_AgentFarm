"""Advisor Agent — decoupled on-demand query service.

Not part of the main LangGraph pipeline; invoked by ``POST /api/advisor/query``.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from ..config.settings import get_settings
from .base_agent import BaseAgent


class AdvisorAgent(BaseAgent):
    """Answers plain-language questions about an existing plan.

    TODO:
      * load plan + relevant KPIs from DB (by ``run_id``)
      * load conversation history from Redis (Tier-3 memory)
      * LLM call at :attr:`Settings.ADVISOR_TEMP` (0.3)
      * append user + assistant messages to session buffer
      * respect SMS-length formatting when requested
    """

    def __init__(self) -> None:
        super().__init__(name="advisor_agent")
        self._settings = get_settings()

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Not used in the main graph — present for API symmetry."""

        self.logger.info("advisor_execute_noop")
        return state

    async def answer(
        self,
        run_id: uuid.UUID,
        session_id: str,
        user_question: str,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Generate a contextual answer. Stub."""

        self.logger.info(
            "advisor_answer_stub",
            run_id=str(run_id),
            session_id=session_id,
            language=language,
        )
        return {
            "answer": "Advisor Agent not yet implemented.",
            "session_id": session_id,
            "referenced_entities": [],
            "history": [],
        }

    async def load_history(self, session_id: str) -> List[Dict[str, str]]:
        """Fetch recent messages for a session from Redis. Stub."""

        return []

    async def append_history(
        self, session_id: str, role: str, content: str
    ) -> None:
        """Append a message to the session buffer. Stub."""

        _ = (session_id, role, content)
