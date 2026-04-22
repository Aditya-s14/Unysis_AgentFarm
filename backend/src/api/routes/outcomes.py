"""``POST /api/outcome/log`` — Tier-2 cross-run learning feedback."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.database import get_db
from ...schemas.plan_schema import OutcomeLogRequest
from ...services.outcome_service import OutcomeService

router = APIRouter(prefix="/outcome", tags=["outcomes"])


@router.post("/log", status_code=status.HTTP_202_ACCEPTED)
async def post_outcome_log(
    payload: OutcomeLogRequest,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Record actual outcomes for a previously executed plan."""

    service = OutcomeService(session)
    count = await service.log_outcomes(
        run_id=payload.run_id,
        outcomes=[o.model_dump() for o in payload.outcomes],
    )
    return {"logged_count": count, "run_id": str(payload.run_id)}
