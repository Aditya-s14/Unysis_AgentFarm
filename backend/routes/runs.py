"""GET /api/run/{run_id} and GET /api/run/{run_id}/traces."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tools.db import get_plan_by_run_id, list_notifications_for_run, list_run_logs_for_run
from tools.notifications.approval import ApprovalError, approve_run_and_notify, plan_approval_payload

router = APIRouter()
logger = logging.getLogger(__name__)


class ApproveRunRequest(BaseModel):
    approved_by: str = Field(default="fpo", max_length=64)


@router.get("/run/{run_id}")
async def get_run(run_id: str) -> dict:
    """Return the persisted plan for a given pipeline run."""
    row = await get_plan_by_run_id(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    return {
        "id": str(row.id),
        "run_id": row.run_id,
        "route_plan": row.route_plan_json,
        "validation": row.validation_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        **plan_approval_payload(row),
    }


@router.post("/run/{run_id}/approve")
async def approve_run(run_id: str, body: ApproveRunRequest | None = None) -> dict:
    """FPO approval gateway — notify farmers and drivers after sign-off."""
    approved_by = (body.approved_by if body else None) or "fpo"
    try:
        return await approve_run_and_notify(run_id, approved_by=approved_by)
    except ApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("POST /api/run/%s/approve failed", run_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/run/{run_id}/notifications")
async def get_run_notifications(run_id: str) -> dict:
    """Return notification audit log for a run."""
    rows = await list_notifications_for_run(run_id)
    return {
        "run_id": run_id,
        "notifications": [
            {
                "id": str(r.id),
                "farm_id": r.farm_id,
                "channel": r.channel,
                "phone": r.phone,
                "status": r.status,
                "priority": r.priority,
                "provider": r.provider,
                "message_body": r.message_body,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/run/{run_id}/weather")
async def get_run_weather(run_id: str) -> dict:
    """Return stored OpenWeather snapshot for a pipeline run (Redis, then Postgres)."""
    from tools.weather_store import get_run_weather_snapshot

    cached = await get_run_weather_snapshot(run_id)
    if cached:
        return cached

    rows = await list_run_logs_for_run(run_id)
    for row in reversed(rows):
        detail = row.detail_json or {}
        snapshot = detail.get("weather_snapshot")
        if isinstance(snapshot, dict) and snapshot:
            return snapshot

    raise HTTPException(
        status_code=404,
        detail=f"Weather snapshot for run {run_id!r} not found",
    )


@router.get("/run/{run_id}/traces")
async def get_run_traces(run_id: str) -> list:
    """Return agent traces for a pipeline run."""
    rows = await list_run_logs_for_run(run_id)
    for row in rows:
        detail = row.detail_json or {}
        if isinstance(detail.get("agent_traces"), list):
            return detail["agent_traces"]
    return [
        {
            "id": str(r.id),
            "run_id": r.run_id,
            "level": r.level,
            "message": r.message,
            "detail": r.detail_json or {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]