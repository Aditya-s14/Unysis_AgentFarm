"""POST /api/calendar/truck-gap — peak harvest truck fleet gap analysis."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel

from models.schemas import Farm, Truck
from tools.crop_calendar import analyze_truck_gap
from tools.notifications.calendar_alerts import dispatch_truck_gap_alert

router = APIRouter()
logger = logging.getLogger(__name__)


class TruckGapRequest(BaseModel):
    farms: list[Farm]
    trucks: list[Truck]
    reference_date: date | None = None


@router.post("/calendar/truck-gap")
async def check_truck_gap(body: TruckGapRequest) -> dict:
    """Analyze peak harvest vs registered fleet; optionally alert FPO."""
    analysis = analyze_truck_gap(
        body.farms,
        body.trucks,
        body.reference_date or date.today(),
    )
    dispatch_stats = await dispatch_truck_gap_alert(analysis)
    return {
        **analysis.to_dict(),
        "alert_dispatched": bool(dispatch_stats.get("dispatched")),
    }
