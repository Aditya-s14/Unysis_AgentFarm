"""Demand forecasting service stub."""

from __future__ import annotations

from typing import Dict, List

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class DemandService:
    """Produces 7-day demand forecasts per demand point.

    TODO:
      * pull historical outcomes from :mod:`src.services.outcome_service`
      * apply festival multipliers from ``utils.constants.FESTIVAL_MULTIPLIERS``
      * adjust for weather (heatwave -> faster spoilage -> lower demand for
        long-haul buyers)
      * call LLM (temperature=0) for narrative explanation
    """

    async def forecast(
        self, demand_point_ids: List[str], horizon_days: int = 7
    ) -> Dict[str, List[float]]:
        """Return ``{demand_point_id: [daily_kg, ...]}``. Stub."""

        logger.info("demand_forecast_stub", count=len(demand_point_ids))
        return {d: [0.0] * horizon_days for d in demand_point_ids}
