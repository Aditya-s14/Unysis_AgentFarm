"""Mandi arrival confirmation — writes actuals to plan_outcomes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models.db_models import PlanOutcomeRow
from models.schemas import MandiArrivalConfirm
from tools.db import get_plan_by_run_id, get_session_maker

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/run/{run_id}/mandi/{mandi_id}/confirm")
async def post_mandi_confirm(
    run_id: str,
    mandi_id: str,
    body: MandiArrivalConfirm,
) -> dict:
    """Mandi confirms truck arrival — persists demand_actual + delivery_time_actual to plan_outcomes."""
    plan = await get_plan_by_run_id(run_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No plan found for run {run_id!r}")
    try:
        row = PlanOutcomeRow(
            plan_id=plan.id,
            waste_kg_predicted=0.0,
            waste_kg_actual=0.0,
            delivery_time_predicted_hours=0.0,
            delivery_time_actual_hours=body.delivery_time_actual_hours,
            demand_predicted=0.0,
            demand_actual=body.demand_actual,
            demand_point_id=mandi_id,
            crop_type=body.crop_type,
            notes=f"mandi_confirm:{mandi_id}",
        )
        async with get_session_maker()() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
    except Exception as exc:  # noqa: BLE001
        logger.exception("POST /api/run/%s/mandi/%s/confirm failed", run_id, mandi_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "run_id": run_id,
        "mandi_id": mandi_id,
        "demand_actual": body.demand_actual,
        "delivery_time_actual_hours": body.delivery_time_actual_hours,
        "outcome_id": str(row.id),
    }
