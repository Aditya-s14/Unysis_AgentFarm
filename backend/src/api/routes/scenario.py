"""``POST /api/scenario/run`` — kicks off a full pipeline execution."""

from __future__ import annotations

from fastapi import APIRouter, status

from ...orchestrator.langgraph_orchestrator import run_scenario
from ...schemas.scenario_schema import ScenarioRequest, ScenarioResponse

router = APIRouter(prefix="/scenario", tags=["scenario"])


@router.post("/run", response_model=ScenarioResponse, status_code=status.HTTP_200_OK)
async def post_scenario_run(request: ScenarioRequest) -> ScenarioResponse:
    """Run the 6-agent pipeline for the supplied scenario payload."""

    return await run_scenario(request)
