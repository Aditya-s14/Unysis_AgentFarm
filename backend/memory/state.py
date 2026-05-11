"""Tier 1 — intra-run LangGraph state (typed, shared across agents in one run)."""

from __future__ import annotations

import operator
from typing import Annotated, NotRequired, TypedDict

from models.schemas import (
    AtRiskStock,
    DemandPoint,
    Farm,
    Plan,
    RoutePlan,
    Truck,
    ValidationResult,
    WeatherEvent,
)


class AgentTrace(TypedDict, total=False):
    """Single agent execution record for dashboard / debugging."""

    agent_name: str
    start_time: str
    end_time: str
    tools_used: list[str]
    notes: str
    token_count: NotRequired[int | None]


class AgentFarmState(TypedDict, total=False):
    """Full cross-agent state for one scenario run (LangGraph channel)."""

    # Inputs
    farms: list[Farm]
    demand_points: list[DemandPoint]
    trucks: list[Truck]
    scenario_type: str

    # Weather agent
    weather_events: list[WeatherEvent]
    weather_risk_summary: dict[str, str]

    # Demand agent (series per demand point id)
    demand_forecast: dict[str, list[float]]

    # Inventory agent
    at_risk_stock: list[AtRiskStock]

    # Logistics agent
    route_plan: RoutePlan

    # Validator
    validation_result: ValidationResult
    retry_count: int

    # Orchestrator
    final_plan: Plan | None
    run_id: str
    # Annotated with operator.add so parallel nodes (weather + demand) can both
    # append their traces without the second overwriting the first.
    agent_traces: Annotated[list[AgentTrace], operator.add]

    # Derived / graph-level
    kpis: dict[str, float]       # populated by persist_node after orchestrator_exit
    human_review: bool           # True when max retries exhausted


def initial_agent_farm_state(
    *,
    run_id: str,
    scenario_type: str = "default",
) -> AgentFarmState:
    """Return a valid initial state dict (empty collections, neutral defaults)."""

    return {
        "run_id": run_id,
        "scenario_type": scenario_type,
        "farms": [],
        "demand_points": [],
        "trucks": [],
        "weather_events": [],
        "weather_risk_summary": {},
        "demand_forecast": {},
        "at_risk_stock": [],
        "route_plan": RoutePlan(),
        "validation_result": ValidationResult(valid=True, errors=[]),
        "retry_count": 0,
        "final_plan": None,
        "agent_traces": [],
        "kpis": {},
        "human_review": False,
    }
