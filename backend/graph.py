"""LangGraph StateGraph wiring for the AgentFarm Optimizer pipeline.

Graph topology
--------------

    START
      │
    entry (orchestrator_entry)
      ├──────────┐
    weather    demand          ← parallel fan-out
      └────┬───┘
         merge               ← fan-in: waits for both, no-op passthrough
           │
        inventory
           │
        logistics
           │
        validate ──(valid=True)──────────────────► exit
           │                                         │
         (valid=False, retry < 2)              persist
           │                                         │
        retry_prep (bumps retry metadata)          END
           │
        logistics  (cycle; logistics reads retry_count → higher relaxation_factor)
           │
        validate
           └── (valid=False, retry >= 2) ──► exit (human_review=True)

Node wrappers
-------------
All existing agent functions return the full mutated state dict (not partial updates).
Because ``agent_traces`` is annotated with ``operator.add``, returning the full list
from two parallel nodes would duplicate entries.  The ``_make_node`` wrapper solves
this by extracting *only the new traces* appended by each agent, keeping the
``operator.add`` semantic correct for both parallel and serial nodes.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

# agents/__init__.py re-exports each agent's `run` function under the agent name,
# so `weather_agent` IS the coroutine, not the module.  Import the module
# separately where we need sub-attributes (orchestrator_entry / exit).
import agents.orchestrator as _orchestrator_module
from agents import (
    demand_agent,
    inventory_agent,
    logistics_agent,
    validator,
    weather_agent,
)
from agents.metrics import compute_kpi_delta
from memory.state import AgentFarmState, AgentTrace, initial_agent_farm_state
from models.schemas import DemandPoint, Farm, Plan, Truck

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node wrapper factory
# ---------------------------------------------------------------------------

def _make_node(
    agent_fn: Callable,
    out_keys: list[str],
    *,
    name: str | None = None,
) -> Callable:
    """Return a LangGraph-safe node wrapper around *agent_fn*.

    The wrapper:
    1. Passes a shallow-copy snapshot of state to the agent (prevents mutation races).
    2. Extracts only the *new* traces appended by the agent (the delta since the call).
    3. Returns a partial-update dict containing only the keys the agent owns plus the
       trace delta — so ``operator.add`` on ``agent_traces`` accumulates correctly.
    """
    async def _wrapped(state: AgentFarmState) -> dict:
        snapshot: AgentFarmState = dict(state)  # type: ignore[assignment]
        prev_len = len(state.get("agent_traces") or [])
        result = await agent_fn(snapshot)
        new_traces: list[AgentTrace] = (result.get("agent_traces") or [])[prev_len:]
        out: dict = {"agent_traces": new_traces}
        for k in out_keys:
            if k in result:
                out[k] = result[k]
        return out

    _wrapped.__name__ = name or getattr(agent_fn, "__name__", "node")
    return _wrapped


# ---------------------------------------------------------------------------
# Inline graph nodes
# ---------------------------------------------------------------------------

async def merge_node(state: AgentFarmState) -> dict:  # noqa: ARG001
    """Fan-in join point after parallel weather + demand; pure pass-through."""
    return {}


async def _bump_relaxation_node(state: AgentFarmState) -> dict:  # noqa: ARG001
    """No-op pass-through before re-entering logistics on retry.

    The logistics agent derives its own relaxation_factor from ``retry_count``
    (which the validator already incremented), so no extra state mutation is
    needed here.  The node exists for graph clarity and future extension.
    """
    return {}


async def persist_node(state: AgentFarmState) -> dict:
    """Compute KPIs and store them in state; plan persistence is in orchestrator_exit."""
    kpis = compute_kpi_delta(state)
    human_review = (state.get("retry_count") or 0) >= 2
    return {"kpis": kpis, "human_review": human_review}


# ---------------------------------------------------------------------------
# Conditional edge router
# ---------------------------------------------------------------------------

def _validate_router(state: AgentFarmState) -> str:
    """Route after validate: pass → exit; first/second fail → retry_prep; max → exit."""
    vr = state.get("validation_result")
    retry = state.get("retry_count") or 0
    if vr and vr.valid:
        return "exit"
    if retry < 2:
        return "retry_prep"
    return "exit"


# ---------------------------------------------------------------------------
# Build the StateGraph
# ---------------------------------------------------------------------------

graph: StateGraph = StateGraph(AgentFarmState)

graph.add_node("entry",     _make_node(_orchestrator_module.orchestrator_entry, ["run_id", "retry_count"], name="entry"))
graph.add_node("weather",   _make_node(weather_agent,   ["weather_events", "weather_risk_summary"], name="weather"))
graph.add_node("demand",    _make_node(demand_agent,    ["demand_forecast"], name="demand"))
graph.add_node("merge",     merge_node)
graph.add_node("inventory", _make_node(inventory_agent, ["at_risk_stock"], name="inventory"))
graph.add_node("logistics", _make_node(logistics_agent, ["route_plan"], name="logistics"))
graph.add_node("validate",  _make_node(validator,       ["validation_result", "retry_count"], name="validate"))
graph.add_node("retry_prep", _bump_relaxation_node)
graph.add_node("exit",      _make_node(_orchestrator_module.orchestrator_exit, ["final_plan"], name="exit"))
graph.add_node("persist",   persist_node)

# --- Edge wiring ---
graph.add_edge(START, "entry")

# Parallel fan-out: both weather and demand receive the post-entry state
graph.add_edge("entry", "weather")
graph.add_edge("entry", "demand")

# Fan-in: merge waits for both branches
graph.add_edge("weather", "merge")
graph.add_edge("demand",  "merge")

# Linear pipeline
graph.add_edge("merge",     "inventory")
graph.add_edge("inventory", "logistics")
graph.add_edge("logistics", "validate")

# Conditional after validate
graph.add_conditional_edges(
    "validate",
    _validate_router,
    {"exit": "exit", "retry_prep": "retry_prep"},
)

# Retry cycle back into logistics
graph.add_edge("retry_prep", "logistics")

# Exit chain
graph.add_edge("exit",    "persist")
graph.add_edge("persist", END)

# ---------------------------------------------------------------------------
# Compile
# ---------------------------------------------------------------------------

compiled_graph = graph.compile()


# ---------------------------------------------------------------------------
# Public API types
# ---------------------------------------------------------------------------

@dataclass
class PipelineRequest:
    """Rich request object used internally by run_scenario (not the thin HTTP schema)."""

    farms: list[Farm]
    demand_points: list[DemandPoint]
    trucks: list[Truck]
    scenario_type: str = "default"
    run_id: str | None = None


@dataclass
class PipelineResult:
    """Return type of run_scenario."""

    run_id: str
    plan: Plan | None
    kpis: dict[str, float] = field(default_factory=dict)
    agent_traces: list[dict] = field(default_factory=list)
    human_review: bool = False


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

async def run_scenario(request: PipelineRequest) -> PipelineResult:
    """Invoke the compiled LangGraph pipeline and return a rich result.

    Args:
        request: Farms, demand points, trucks and scenario metadata.

    Returns:
        PipelineResult with plan, KPIs, per-agent traces and human_review flag.
    """
    run_id = request.run_id or str(uuid4())
    state = initial_agent_farm_state(run_id=run_id, scenario_type=request.scenario_type)
    state["farms"] = request.farms
    state["demand_points"] = request.demand_points
    state["trucks"] = request.trucks

    logger.info("run_scenario start run_id=%s scenario=%s", run_id, request.scenario_type)
    result: AgentFarmState = await compiled_graph.ainvoke(state)
    logger.info("run_scenario done run_id=%s traces=%d", run_id, len(result.get("agent_traces") or []))

    return PipelineResult(
        run_id=result.get("run_id", run_id),
        plan=result.get("final_plan"),
        kpis=result.get("kpis") or {},
        agent_traces=list(result.get("agent_traces") or []),
        human_review=result.get("human_review", False),
    )
