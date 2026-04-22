"""``GET /api/run/{run_id}`` and traces endpoint."""

from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/run", tags=["runs"])


@router.get("/{run_id}", status_code=status.HTTP_200_OK)
async def get_run(run_id: uuid.UUID) -> Dict[str, Any]:
    """Return the persisted plan, KPIs, and a traces summary for a run.

    TODO: read ``ScenarioRun``, ``Plan``, ``RunLog`` rows from DB.
    """

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Run lookup not yet implemented (run_id={run_id}).",
    )


@router.get("/{run_id}/traces", status_code=status.HTTP_200_OK)
async def get_run_traces(run_id: uuid.UUID) -> Dict[str, Any]:
    """Return per-agent step traces for the given run.

    TODO: query ``run_logs`` table ordered by ``created_at``.
    """

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Trace lookup not yet implemented (run_id={run_id}).",
    )
