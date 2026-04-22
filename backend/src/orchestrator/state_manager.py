"""Tier-1 (intra-run) shared state passed between LangGraph nodes."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, TypedDict


class AgentFarmState(TypedDict, total=False):
    """Typed dictionary carrying every agent's input and output within one run.

    Populated by the orchestrator entry node; each agent reads its inputs
    and writes to its designated output fields. All free-form strings are
    forbidden — everything here is typed or a JSON-serialisable structure.
    """

    # --- Run metadata ---
    run_id: str
    scenario_type: str
    retry_count: int
    agent_traces: List[Dict[str, Any]]

    # --- Inputs ---
    farms: List[Dict[str, Any]]
    demand_points: List[Dict[str, Any]]
    trucks: List[Dict[str, Any]]
    constraints: Dict[str, Any]

    # --- Weather Agent output ---
    weather_events: List[Dict[str, Any]]
    weather_risk_summary: Dict[str, str]

    # --- Demand Agent output ---
    demand_forecast: Dict[str, List[float]]

    # --- Inventory Agent output ---
    at_risk_stock: List[Dict[str, Any]]

    # --- Logistics Agent output ---
    route_plan: Dict[str, Any]

    # --- Validator output ---
    validation_result: Dict[str, Any]

    # --- Orchestrator output ---
    final_plan: Dict[str, Any]
    kpis: Dict[str, float]


def new_state(
    *,
    farms: List[Dict[str, Any]] | None = None,
    demand_points: List[Dict[str, Any]] | None = None,
    trucks: List[Dict[str, Any]] | None = None,
    scenario_type: str = "custom",
    constraints: Dict[str, Any] | None = None,
) -> AgentFarmState:
    """Construct a fresh :class:`AgentFarmState` with empty outputs."""

    return AgentFarmState(
        run_id=str(uuid.uuid4()),
        scenario_type=scenario_type,
        retry_count=0,
        agent_traces=[],
        farms=farms or [],
        demand_points=demand_points or [],
        trucks=trucks or [],
        constraints=constraints or {},
        weather_events=[],
        weather_risk_summary={},
        demand_forecast={},
        at_risk_stock=[],
        route_plan={},
        validation_result={},
        final_plan={},
        kpis={},
    )
