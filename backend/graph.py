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
        logistics  (cycle; logistics reads retry_count → lower demand_scale)
           │
        validate
           └── (valid=False, retry >= max) ──► exit (human_review if still invalid)

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
from datetime import datetime, timezone
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
from agents.review_flags import max_retries, needs_human_review
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


async def _bump_relaxation_node(state: AgentFarmState) -> dict:
    """Emit a trace before re-entering logistics on retry (observable retry loop)."""
    from agents.validator import _demand_scale_for_retry, _relaxation_factor_applied

    retry = state.get("retry_count") or 0
    demand_scale = _demand_scale_for_retry(retry)
    relaxation = _relaxation_factor_applied(retry)
    t0 = datetime.now(timezone.utc)

    vr = state.get("validation_result")
    violation_types: list[str] = []
    if vr and not vr.valid:
        for err in vr.errors or []:
            tag = (err.split(":", 1)[0] or "").lower()
            if tag == "capacity":
                violation_types.append("capacity")
            elif tag == "avail_window":
                violation_types.append("time_window")
            elif tag == "severe_weather":
                violation_types.append("weather")
            elif tag == "urgent_uncovered":
                violation_types.append("spoilage_priority")
            elif tag == "drive_time":
                violation_types.append("driver_hours")
        violation_types = list(dict.fromkeys(violation_types))

    trace: AgentTrace = {
        "agent_name": "retry_prep",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": ["apply_constraint_relaxation"],
        "execution_type": "deterministic retry coordinator",
        "notes": (
            f"retry_count={retry} demand_scale={demand_scale} "
            f"relaxation_factor={relaxation}"
        ),
        "details": {
            "retry_count": retry,
            "relaxation_factor_applied": relaxation,
            "demand_scale": demand_scale,
            "reason_for_retry": violation_types,
        },
        "token_count": 0,
    }
    return {"agent_traces": [trace]}


async def persist_node(state: AgentFarmState) -> dict:
    """Compute KPIs and store them in state; plan persistence is in orchestrator_exit."""
    kpis = compute_kpi_delta(state)
    return {"kpis": kpis, "human_review": needs_human_review(state)}


# ---------------------------------------------------------------------------
# Conditional edge router
# ---------------------------------------------------------------------------

def _validate_router(state: AgentFarmState) -> str:
    """Route after validate: pass → exit; first/second fail → retry_prep; max → exit."""
    vr = state.get("validation_result")
    retry = state.get("retry_count") or 0
    if vr and vr.valid:
        return "exit"
    if retry < max_retries():
        return "retry_prep"
    return "exit"


# ---------------------------------------------------------------------------
# Build the StateGraph
# ---------------------------------------------------------------------------

graph: StateGraph = StateGraph(AgentFarmState)

graph.add_node("entry",     _make_node(_orchestrator_module.orchestrator_entry, ["run_id", "retry_count"], name="entry"))
graph.add_node(
    "weather",
    _make_node(weather_agent, ["weather_events", "weather_risk_summary", "weather_fetch_meta"], name="weather"),
)
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
    demand_forecast: dict[str, list[float]] = field(default_factory=dict)
    at_risk_stock: list = field(default_factory=list)
    weather_summary: dict = field(default_factory=dict)
    weather_risk_summary: dict[str, str] = field(default_factory=dict)


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

    at_risk = result.get("at_risk_stock") or []
    weather_events = result.get("weather_events") or []
    weather_risk = dict(result.get("weather_risk_summary") or {})
    farms = result.get("farms") or request.farms

    from tools.weather_summary import build_weather_summary

    w_summary = build_weather_summary(
        scenario_type=result.get("scenario_type") or request.scenario_type,
        farms=farms,
        weather_events=[
            e.model_dump() if hasattr(e, "model_dump") else e for e in weather_events
        ],
        weather_risk_summary=weather_risk,
        weather_fetch_meta=dict(result.get("weather_fetch_meta") or {}),
    )

    return PipelineResult(
        run_id=result.get("run_id", run_id),
        plan=result.get("final_plan"),
        kpis=result.get("kpis") or {},
        agent_traces=list(result.get("agent_traces") or []),
        human_review=result.get("human_review", False),
        demand_forecast=dict(result.get("demand_forecast") or {}),
        at_risk_stock=[
            s.model_dump() if hasattr(s, "model_dump") else s for s in at_risk
        ],
        weather_summary=w_summary,
        weather_risk_summary=weather_risk,
    )
