"""Zero trucks — API rejects; graph short-circuits when invoked directly."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from graph import PipelineRequest, run_scenario
from tests.test_resilience.conftest import mini_demand_points, mini_farms


@pytest.mark.asyncio
async def test_graph_blocked_with_zero_trucks(pipeline_patches) -> None:
    with patch("agents.weather_agent.fetch_weather", new=AsyncMock(return_value={"events": [], "meta": {}})):
        result = await run_scenario(
            PipelineRequest(
                farms=mini_farms(),
                demand_points=mini_demand_points(),
                trucks=[],
                scenario_type="normal_day",
            ),
        )

    assert result.human_review is True
    assert result.plan is not None
    assert result.plan.route_plan.routes == []
    trace_names = [t.get("agent_name") for t in result.agent_traces]
    assert "blocked_plan" in trace_names


def test_api_validate_rejects_zero_trucks() -> None:
    import pytest
    from fastapi import HTTPException

    from routes.scenario import RunScenarioRequest, _DemandPointIn, _validate_scenario_inputs

    dp = mini_demand_points()[0]
    body = RunScenarioRequest(
        scenario_type="normal_day",
        farms=mini_farms(),
        demand_points=[
            _DemandPointIn(
                id=dp.id,
                name=dp.name,
                lat=dp.lat,
                lng=dp.lng,
                type=dp.type,
                base_demand_per_day=dp.base_demand_per_day,
            ),
        ],
        trucks=[],
    )
    with pytest.raises(HTTPException) as exc_info:
        _validate_scenario_inputs(body)
    assert exc_info.value.status_code == 422
    assert "trucks list is empty" in str(exc_info.value.detail)
