"""POST /api/scenario/run — invoke the full LangGraph pipeline via HTTP."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from graph import PipelineRequest, PipelineResult, run_scenario
from models.schemas import DemandPoint, Farm, Plan, Truck

router = APIRouter()
logger = logging.getLogger(__name__)


class _DemandPointIn(BaseModel):
    """HTTP shim that accepts both ``type`` and ``point_type`` field names.

    Clients such as the test script send ``"point_type": "apmc"`` whereas the
    internal ``DemandPoint`` schema uses ``"type"``.  This model bridges the gap
    without touching the core schema.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    lat: float
    lng: float
    type: str | None = None
    point_type: str | None = None
    base_demand_per_day: float

    @model_validator(mode="after")
    def _coerce_type(self) -> "_DemandPointIn":
        if self.type is None:
            self.type = self.point_type or "apmc"
        return self

    def to_schema(self) -> DemandPoint:
        return DemandPoint(
            id=self.id,
            name=self.name,
            lat=self.lat,
            lng=self.lng,
            type=self.type,  # type: ignore[arg-type]
            base_demand_per_day=self.base_demand_per_day,
        )


class RunScenarioRequest(BaseModel):
    """HTTP request body for POST /api/scenario/run."""

    scenario_type: str = "default"
    farms: list[Farm]
    demand_points: list[_DemandPointIn]
    trucks: list[Truck]


class RunScenarioResponse(BaseModel):
    """HTTP response for POST /api/scenario/run."""

    run_id: str
    plan: Plan | None = None
    kpis: dict[str, float] = Field(default_factory=dict)
    agent_traces: list[dict[str, Any]] = Field(default_factory=list)
    human_review: bool = False


@router.post("/scenario/run", response_model=RunScenarioResponse)
async def run_scenario_endpoint(body: RunScenarioRequest) -> RunScenarioResponse:
    """Run the full multi-agent pipeline and return the optimised plan + KPIs."""
    try:
        req = PipelineRequest(
            farms=body.farms,
            demand_points=[dp.to_schema() for dp in body.demand_points],
            trucks=body.trucks,
            scenario_type=body.scenario_type,
        )
        result: PipelineResult = await run_scenario(req)
        return RunScenarioResponse(
            run_id=result.run_id,
            plan=result.plan,
            kpis=result.kpis,
            agent_traces=result.agent_traces,
            human_review=result.human_review,
        )
    except Exception as exc:
        logger.exception("POST /api/scenario/run failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
