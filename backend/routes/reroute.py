"""POST /api/scenario/{run_id}/reroute — alternate routes around a blockage (R4).

A driver (or FPO) reports a blocked leg of an existing plan. We reload that
run's original inputs (stashed in Redis by /scenario/run), penalize the
blocked leg in the distance matrix, and re-run the pipeline so OR-Tools
routes around it. The response is a brand-new plan/run; the driver app
(T5, Member B) shows the new stop order.

Role-guarded with require_role("driver", "fpo") — enforced regardless of the
global AUTH_ENABLED flag.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from graph import PipelineRequest, PipelineResult, run_scenario
from models.schemas import DemandPoint, Farm, Truck
from routes.scenario import (
    SCENARIO_INPUTS_PREFIX,
    RunScenarioResponse,
    stash_scenario_inputs,
)
from tools.auth import require_role

router = APIRouter()
logger = logging.getLogger(__name__)


class BlockedLeg(BaseModel):
    from_lat: float
    from_lng: float
    to_lat: float
    to_lng: float


class RerouteRequest(BaseModel):
    blocked_segment: BlockedLeg
    # 5x makes the solver strongly prefer any detour while keeping the leg
    # usable when it is genuinely the only option (e.g. single-farm region).
    penalty_factor: float = Field(default=5.0, gt=1.0, le=100.0)


@router.post("/scenario/{run_id}/reroute")
async def reroute_with_blockage(
    run_id: str,
    body: RerouteRequest,
    request: Request,
    user: dict = Depends(require_role("driver", "fpo")),
) -> dict:
    """Re-solve a run's routes with one leg penalized; returns the new plan."""
    try:
        raw = await request.app.state.redis.get(f"{SCENARIO_INPUTS_PREFIX}{run_id}")
    except Exception as exc:
        logger.exception("reroute: Redis unavailable")
        raise HTTPException(status_code=503, detail="Input store unavailable") from exc
    if raw is None:
        raise HTTPException(
            status_code=404,
            detail="Original inputs for this run are unavailable (expired or unknown run_id). Re-run the scenario.",
        )

    inputs = json.loads(raw)
    seg = body.blocked_segment
    blocked = [{
        "from": [seg.from_lat, seg.from_lng],
        "to": [seg.to_lat, seg.to_lng],
        "penalty": body.penalty_factor,
    }]

    req = PipelineRequest(
        farms=[Farm(**f) for f in inputs["farms"]],
        demand_points=[DemandPoint(**d) for d in inputs["demand_points"]],
        trucks=[Truck(**t) for t in inputs["trucks"]],
        scenario_type=inputs.get("scenario_type") or "default",
        blocked_segments=blocked,
    )
    try:
        result: PipelineResult = await run_scenario(req)
    except Exception as exc:
        logger.exception("reroute: pipeline failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # The new run is itself reroutable (multiple blockages stack by chaining).
    await stash_scenario_inputs(
        request,
        result.run_id,
        scenario_type=req.scenario_type,
        farms=req.farms,
        demand_points=req.demand_points,
        trucks=req.trucks,
    )

    response = RunScenarioResponse(
        run_id=result.run_id,
        plan=result.plan,
        kpis=result.kpis,
        agent_traces=result.agent_traces,
        human_review=result.human_review,
        demand_forecast=result.demand_forecast,
        at_risk_stock=result.at_risk_stock,
        weather_summary=result.weather_summary,
        weather_risk_summary=result.weather_risk_summary,
        weather_snapshot=result.weather_snapshot,
    ).model_dump(mode="json")
    response["reroute"] = {
        "previous_run_id": run_id,
        "blocked_segment": seg.model_dump(),
        "penalty_factor": body.penalty_factor,
        "requested_by": {"phone": user.get("sub"), "role": user.get("role")},
    }
    return response
