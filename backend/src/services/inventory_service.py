"""Inventory spoilage service stub."""

from __future__ import annotations

from typing import Any, Dict, List

from ..config.logging_config import get_logger
from ..utils.constants import CROP_SHELF_LIFE

logger = get_logger(__name__)


class InventoryService:
    """Estimates at-risk stock given shelf life and weather.

    TODO:
      * load current farm inventory from DB
      * compute spoilage = shelf_life * temp_factor * days_since_harvest
      * call LLM (temperature=0) to rank prioritisation
    """

    async def compute_at_risk(
        self, farms: List[Dict[str, Any]], weather: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Return at-risk stock entries. Stub."""

        logger.info("inventory_stub", farm_count=len(farms))
        at_risk: List[Dict[str, Any]] = []
        for farm in farms:
            shelf = CROP_SHELF_LIFE.get(farm.get("crop_type", ""), 7)
            at_risk.append(
                {
                    "farm_id": farm.get("id"),
                    "crop_type": farm.get("crop_type"),
                    "quantity_kg": 0.0,
                    "days_until_spoilage": shelf,
                    "priority_score": 0.0,
                }
            )
        return at_risk
