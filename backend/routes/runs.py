"""GET /api/run/{run_id} and GET /api/run/{run_id}/traces."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from tools.db import get_plan_by_run_id, list_run_logs_for_run

router = APIRouter()
logger = logging.getLogger(__name__)


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
    }


@router.get("/run/{run_id}/traces")
async def get_run_traces(run_id: str) -> list:
    """Return agent traces for a pipeline run.

    The orchestrator stores ``agent_traces`` inside the run_log ``detail_json``
    under the key ``"agent_traces"``.  If that key is present we return it
    directly (gives the full per-agent breakdown).  Otherwise we fall back to
    returning the raw run_log rows as-is.
    """
    rows = await list_run_logs_for_run(run_id)
    for row in rows:
        detail = row.detail_json or {}
        if isinstance(detail.get("agent_traces"), list):
            return detail["agent_traces"]
    # Fallback: return raw run_log rows
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
