"""Live truck GPS tracking and route deviation alerts."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException

from models.schemas import PositionReport
from tools.db import get_plan_run_detail
from tools.notifications.run_state import rebuild_state_from_snapshot
from tools.tracking.incident import TrackingError, list_deviation_alerts
from tools.tracking.service import ingest_position, list_positions, verify_ingest_key

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/run/{run_id}/tracking/{truck_id}/position")
async def post_truck_position(
    run_id: str,
    truck_id: str,
    body: PositionReport,
    x_tracking_key: str | None = Header(default=None, alias="X-Tracking-Key"),
) -> dict:
    """Ingest driver/FPO GPS position and evaluate route deviation."""
    try:
        verify_ingest_key(x_tracking_key)
        from tools.db import get_plan_by_run_id

        plan = await get_plan_by_run_id(run_id)
        trucks = None
        if plan is not None:
            detail = await get_plan_run_detail(run_id)
            if detail:
                try:
                    state = rebuild_state_from_snapshot(run_id=run_id, plan=plan, detail=detail)
                    trucks = state.get("trucks")
                except ValueError:
                    trucks = None
        result = await ingest_position(run_id, truck_id, body, trucks=trucks)
        return result.model_dump(mode="json")
    except TrackingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "POST /api/run/%s/tracking/%s/position failed",
            run_id,
            truck_id,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/run/{run_id}/tracking")
async def get_truck_tracking(run_id: str) -> dict:
    """Return live positions for all routed trucks on a run."""
    try:
        positions = await list_positions(run_id)
        return {
            "run_id": run_id,
            "positions": [p.model_dump(mode="json") for p in positions],
        }
    except TrackingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("GET /api/run/%s/tracking failed", run_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/run/{run_id}/tracking/deviations")
async def get_deviation_alerts(run_id: str) -> dict:
    """Return route deviation alert history for a run."""
    alerts = await list_deviation_alerts(run_id)
    return {
        "run_id": run_id,
        "alerts": [a.model_dump(mode="json") for a in alerts],
    }
