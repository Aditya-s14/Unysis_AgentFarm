"""POST /api/advisor/query and POST /api/outcome/log."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.advisor_agent import answer_query
from models.schemas import PlanOutcome
from tools.db import create_plan_outcome
from tools.http_errors import friendly_outcome_error

router = APIRouter()
logger = logging.getLogger(__name__)


class AdvisorQueryRequest(BaseModel):
    run_id: str
    session_id: str
    question: str


@router.post("/advisor/query")
async def advisor_query(body: AdvisorQueryRequest) -> dict:
    """Answer a plain-language question about a run's plan (Kisan Mitra persona)."""
    try:
        resp = await answer_query(
            run_id=body.run_id,
            session_id=body.session_id,
            question=body.question,
        )
        return {
            "answer": resp.reply,
            "sources": resp.sources,
            "run_id": resp.run_id,
            "session_id": resp.session_id,
        }
    except Exception as exc:
        logger.exception("POST /api/advisor/query failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/outcome/log", status_code=201)
async def log_outcome(body: PlanOutcome) -> dict:
    """Persist an observed plan outcome for the learning loop."""
    try:
        row = await create_plan_outcome(
            plan_id=UUID(str(body.plan_id)),
            waste_kg_predicted=body.waste_kg_predicted,
            waste_kg_actual=body.waste_kg_actual,
            delivery_time_predicted_hours=body.delivery_time_predicted_hours,
            delivery_time_actual_hours=body.delivery_time_actual_hours,
            demand_predicted=body.demand_predicted,
            demand_actual=body.demand_actual,
            notes=body.notes,
            demand_point_id=body.demand_point_id,
            crop_type=body.crop_type,
            day_of_week=body.day_of_week,
            road_segment=body.road_segment,
            season=body.season,
        )
        return {"id": str(row.id), "plan_id": str(row.plan_id)}
    except Exception as exc:
        logger.exception("POST /api/outcome/log failed")
        raise friendly_outcome_error(exc) from exc
