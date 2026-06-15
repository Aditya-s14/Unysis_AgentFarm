"""Breakdown assistance — live vehicle incident reporting and re-plan."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import BreakdownReport, BreakdownReplanRequest
from tools.breakdown.incident import BreakdownError, list_incidents
from tools.breakdown.service import (
    approve_breakdown_incident,
    intake_breakdown_report,
    replan_reported_incident,
    report_breakdown,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/run/{run_id}/breakdown")
async def post_breakdown(run_id: str, body: BreakdownReport) -> dict:
    """Report a truck breakdown; drivers may submit report-only (no replan)."""
    try:
        preview = await report_breakdown(run_id, body)
        return preview.model_dump(mode="json")
    except BreakdownError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("POST /api/run/%s/breakdown failed", run_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/run/{run_id}/breakdown/{incident_id}/replan")
async def post_breakdown_replan(
    run_id: str,
    incident_id: str,
    body: BreakdownReplanRequest,
) -> dict:
    """FPO replans a driver-reported breakdown and returns preview for approval."""
    try:
        preview = await replan_reported_incident(
            run_id,
            incident_id,
            completed_farm_ids=body.completed_farm_ids,
            spare_truck_id=body.spare_truck_id,
        )
        return preview.model_dump(mode="json")
    except BreakdownError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "POST /api/run/%s/breakdown/%s/replan failed",
            run_id,
            incident_id,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/run/{run_id}/breakdown/{incident_id}/approve")
async def post_breakdown_approve(run_id: str, incident_id: str) -> dict:
    """FPO approves breakdown replan and dispatches delta notifications."""
    try:
        preview = await approve_breakdown_incident(run_id, incident_id)
        return preview.model_dump(mode="json")
    except BreakdownError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "POST /api/run/%s/breakdown/%s/approve failed",
            run_id,
            incident_id,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/run/{run_id}/breakdown")
async def get_breakdown_incidents(run_id: str) -> dict:
    """List breakdown incidents for a run."""
    incidents = await list_incidents(run_id)
    return {
        "run_id": run_id,
        "incidents": [i.model_dump(mode="json") for i in incidents],
    }
