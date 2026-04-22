"""Outcome Store service — Tier-2 (cross-run) memory."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class OutcomeService:
    """Read/write actual plan outcomes for cross-run learning.

    TODO:
      * implement DB-backed queries using ``PlanOutcome`` model
      * expose ``get_demand_history(demand_point_id, dow)`` etc.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_outcomes(
        self, run_id: uuid.UUID, outcomes: List[Dict[str, Any]]
    ) -> int:
        """Persist a batch of outcome records. Returns number logged."""

        logger.info("log_outcomes_stub", run_id=str(run_id), count=len(outcomes))
        return len(outcomes)

    async def get_demand_history(
        self, demand_point_id: uuid.UUID, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Return recent demand outcomes for this demand point. Stub."""

        return []

    async def get_route_history(
        self, farm_id: uuid.UUID, demand_point_id: uuid.UUID, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Return recent route timing outcomes. Stub."""

        return []
