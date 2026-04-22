"""LangGraph orchestrator — builds the AgentFarm pipeline graph.

Graph shape::

    START
      -> orchestrator_entry
      -> fan-out: [weather_agent, demand_agent]
      -> merge
      -> inventory_agent
      -> logistics_agent
      -> validator
            (valid)        -> orchestrator_exit
            (invalid,
             retries<MAX)  -> logistics_agent
            (invalid,
             retries>=MAX) -> orchestrator_exit (flagged)
      -> persist
      -> END
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

from ..agents.demand_agent import DemandAgent
from ..agents.inventory_agent import InventoryAgent
from ..agents.logistics_agent import LogisticsAgent
from ..agents.validator_agent import ValidatorAgent
from ..agents.weather_agent import WeatherAgent
from ..config.logging_config import get_logger
from ..config.settings import get_settings
from ..schemas.plan_schema import PlanSchema
from ..schemas.scenario_schema import (
    KPISummary,
    ScenarioRequest,
    ScenarioResponse,
)
from ..utils.formatters import traces_summary
from .state_manager import AgentFarmState, new_state

logger = get_logger(__name__)


# ---------- Node implementations (thin wrappers around agents) ---------- #


async def orchestrator_entry(state: AgentFarmState) -> AgentFarmState:
    """Validate inputs, assign a run_id, attach context (past outcomes)."""

    logger.info("orchestrator_entry", farms=len(state.get("farms", [])))
    state.setdefault("run_id", str(uuid.uuid4()))
    state.setdefault("retry_count", 0)
    state.setdefault("agent_traces", []).append(
        {"agent": "orchestrator", "step": "entry", "data": {"run_id": state["run_id"]}}
    )
    return state


async def merge_node(state: AgentFarmState) -> AgentFarmState:
    """Join point after the Weather / Demand fan-out."""

    state.setdefault("agent_traces", []).append(
        {
            "agent": "orchestrator",
            "step": "merge",
            "data": {
                "weather_events": len(state.get("weather_events", [])),
                "demand_forecast_keys": len(state.get("demand_forecast", {})),
            },
        }
    )
    return state


async def orchestrator_exit(state: AgentFarmState) -> AgentFarmState:
    """Resolve inter-agent conflicts and package the final plan."""

    logger.info("orchestrator_exit", run_id=state.get("run_id"))
    state["final_plan"] = state.get("final_plan") or {
        "run_id": state.get("run_id"),
        "assignments": state.get("route_plan", {}).get("routes", []),
        "expected_waste_kg": 0.0,
        "expected_cost": 0.0,
    }
    state.setdefault("kpis", {})
    state.setdefault("agent_traces", []).append(
        {"agent": "orchestrator", "step": "exit", "data": {"retries": state.get("retry_count", 0)}}
    )
    return state


async def persist_node(state: AgentFarmState) -> AgentFarmState:
    """Write plan + run log to Postgres.

    TODO: inject an ``AsyncSession`` and persist the ``ScenarioRun``,
    ``Plan``, and ``RunLog`` rows here.
    """

    logger.info("persist_stub", run_id=state.get("run_id"))
    return state


# ---------- Conditional router ---------- #


def _after_validator(state: AgentFarmState) -> str:
    """Decide whether to retry logistics or proceed to exit."""

    result = state.get("validation_result", {}) or {}
    is_valid = bool(result.get("is_valid", True))
    retries = int(state.get("retry_count", 0))
    max_retries = get_settings().MAX_RETRIES

    if is_valid:
        return "orchestrator_exit"
    if retries < max_retries:
        state["retry_count"] = retries + 1
        return "logistics_agent"
    return "orchestrator_exit"  # flagged for human review


# ---------- Graph builder ---------- #


def build_graph() -> Any:
    """Construct and compile the LangGraph ``StateGraph``.

    Imported lazily to avoid a hard dependency at module import time.
    """

    from langgraph.graph import END, START, StateGraph  # type: ignore

    weather = WeatherAgent()
    demand = DemandAgent()
    inventory = InventoryAgent()
    logistics = LogisticsAgent()
    validator = ValidatorAgent()

    graph: StateGraph = StateGraph(AgentFarmState)

    graph.add_node("orchestrator_entry", orchestrator_entry)
    graph.add_node("weather_agent", weather.execute)
    graph.add_node("demand_agent", demand.execute)
    graph.add_node("merge", merge_node)
    graph.add_node("inventory_agent", inventory.execute)
    graph.add_node("logistics_agent", logistics.execute)
    graph.add_node("validator", validator.execute)
    graph.add_node("orchestrator_exit", orchestrator_exit)
    graph.add_node("persist", persist_node)

    graph.add_edge(START, "orchestrator_entry")

    # Fan-out: entry -> [weather, demand]
    graph.add_edge("orchestrator_entry", "weather_agent")
    graph.add_edge("orchestrator_entry", "demand_agent")

    # Fan-in into merge
    graph.add_edge("weather_agent", "merge")
    graph.add_edge("demand_agent", "merge")

    graph.add_edge("merge", "inventory_agent")
    graph.add_edge("inventory_agent", "logistics_agent")
    graph.add_edge("logistics_agent", "validator")

    graph.add_conditional_edges(
        "validator",
        _after_validator,
        {
            "logistics_agent": "logistics_agent",
            "orchestrator_exit": "orchestrator_exit",
        },
    )

    graph.add_edge("orchestrator_exit", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


# ---------- Public entrypoint ---------- #


async def run_scenario(request: ScenarioRequest) -> ScenarioResponse:
    """Run the full pipeline for a :class:`ScenarioRequest`.

    Currently returns a skeleton response — wiring to the compiled graph
    is guarded so the app boots even if ``langgraph`` is not installed in
    the dev environment.
    """

    state = new_state(
        farms=[f.model_dump() for f in request.farms],
        demand_points=[d.model_dump() for d in request.demand_points],
        trucks=[t.model_dump() for t in request.trucks],
        scenario_type=request.scenario_type.value,
        constraints=request.constraints.model_dump(),
    )

    try:
        graph = build_graph()
        state = await graph.ainvoke(state)  # type: ignore[assignment]
    except Exception as exc:  # pragma: no cover - stub path
        logger.warning("graph_invoke_failed", error=str(exc))

    run_id = uuid.UUID(state["run_id"]) if isinstance(state.get("run_id"), str) else uuid.uuid4()
    plan = PlanSchema(
        run_id=run_id,
        plan_date=__import__("datetime").date.today(),
        assignments=[],
        expected_waste_kg=0.0,
        expected_cost=0.0,
        kpis={},
    )
    return ScenarioResponse(
        runId=run_id,
        plan=plan,
        kpis=KPISummary(),
        farms=[],
        demandPoints=[],
        trucks=[],
        traces_summary=traces_summary(state.get("agent_traces", [])),
    )
