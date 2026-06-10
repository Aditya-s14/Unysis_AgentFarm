"""Orchestrator — pipeline entry and exit bookends.

orchestrator_entry(state):
  - Generate run_id (uuid4) if not already set.
  - Validate that farms, demand_points, and trucks are all non-empty.
  - Load recent Tier-2 outcomes to surface any systematic bias in the current context.
  - Initialise agent_traces list and log an entry record.

orchestrator_exit(state):
  - Compute KPI deltas vs naive baseline via metrics.compute_kpi_delta().
  - If max retries exhausted and validation still fails, flag for human review (still persist).
  - Persist Plan + RunLog to Postgres via tools.db (graceful no-op if DB unavailable).
  - Set state["final_plan"].

Neither function calls an LLM; both are pure control flow.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from agents.metrics import compute_kpi_delta
from agents.review_flags import max_retries, needs_human_review
from memory.state import AgentFarmState, AgentTrace
from models.schemas import Plan, ValidationResult
from tools.scenario_effects import normalize_scenario_type, scenario_trace_note

logger = logging.getLogger(__name__)


async def orchestrator_entry(state: AgentFarmState) -> AgentFarmState:
    """Pipeline entry: generate run_id, validate inputs, seed initial trace."""
    t0 = datetime.now(timezone.utc)

    # Assign run_id if caller didn't supply one
    if not state.get("run_id"):
        state["run_id"] = str(uuid.uuid4())

    run_id = state["run_id"]
    raw_scenario = state.get("scenario_type", "")
    state["scenario_type_raw"] = raw_scenario
    scenario_type = normalize_scenario_type(raw_scenario)
    state["scenario_type"] = scenario_type

    # Ensure trace list exists
    state.setdefault("agent_traces", [])
    state.setdefault("retry_count", 0)

    farms = state.get("farms") or []
    demand_points = state.get("demand_points") or []
    trucks = state.get("trucks") or []

    input_errors: list[str] = []
    if not farms:
        input_errors.append("farms list is empty")
    if not demand_points:
        input_errors.append("demand_points list is empty")
    if not trucks:
        input_errors.append("trucks list is empty")

    # Load recent Tier-2 context to inform downstream agents (advisory only;
    # agents pull their own focused queries later).
    recent_outcomes_count = 0
    try:
        from tools.db import get_session_maker
        from models.db_models import PlanOutcomeRow
        from sqlalchemy import select, func

        async with get_session_maker()() as session:
            recent_outcomes_count = await session.scalar(
                select(func.count()).select_from(PlanOutcomeRow)
            ) or 0
    except Exception as exc:  # noqa: BLE001
        logger.debug("orchestrator_entry: could not count outcomes: %s", exc)

    notes = (
        f"run_id={run_id}; scenario_type={scenario_type}; "
        f"farms={len(farms)}, demand_points={len(demand_points)}, trucks={len(trucks)}; "
        f"historical_outcomes_available={recent_outcomes_count}; "
        f"input_errors={input_errors or 'none'}. "
        + scenario_trace_note(scenario_type)
    )
    trace: AgentTrace = {
        "agent_name": "orchestrator_entry",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": ["tools.db.count_outcomes"],
        "notes": notes,
        "token_count": None,
    }
    state["agent_traces"] = [*state["agent_traces"], trace]

    if input_errors:
        state["pipeline_blocked"] = True
        state["input_errors"] = input_errors
        logger.warning("orchestrator_entry validation errors: %s", input_errors)
    else:
        state["pipeline_blocked"] = False
        state["input_errors"] = []
        logger.info("orchestrator_entry OK run_id=%s", run_id)

    return state


async def orchestrator_exit(state: AgentFarmState) -> AgentFarmState:
    """Pipeline exit: compute KPIs, persist Plan + RunLog, set final_plan."""
    t0 = datetime.now(timezone.utc)
    run_id = state.get("run_id") or str(uuid.uuid4())

    # KPI computation
    kpi = compute_kpi_delta(state)

    retry_count = state.get("retry_count") or 0
    human_review_needed = needs_human_review(state)
    if human_review_needed:
        logger.warning(
            "orchestrator_exit: max retries (%d) exhausted with invalid plan for run %s",
            max_retries(), run_id,
        )

    validation = state.get("validation_result")
    route_plan = state.get("route_plan")

    # Persist to Postgres (graceful skip when DB is unavailable)
    plan_id: str | None = None
    try:
        from tools.db import create_plan, create_run_log

        plan_row = await create_plan(
            route_plan_json=route_plan.model_dump() if route_plan else {"routes": []},
            run_id=run_id,
            validation_json=validation.model_dump() if validation else None,
        )
        plan_id = str(plan_row.id)

        from tools.scenario_effects import coerce_weather_events
        from tools.weather_store import save_run_weather_snapshot
        from tools.weather_summary import build_weather_snapshot

        farms = state.get("farms") or []
        weather_events = coerce_weather_events(state.get("weather_events") or [])
        weather_risk = dict(state.get("weather_risk_summary") or {})
        weather_meta = dict(state.get("weather_fetch_meta") or {})
        weather_snapshot = build_weather_snapshot(
            run_id=run_id,
            scenario_type=state.get("scenario_type") or "normal",
            farms=farms,
            weather_events=weather_events,
            weather_risk_summary=weather_risk,
            weather_fetch_meta=weather_meta,
        )
        await save_run_weather_snapshot(run_id, weather_snapshot)

        at_risk_raw = state.get("at_risk_stock") or []
        kpi_detail = {
            **kpi,
            "human_review_needed": human_review_needed,
            "scenario_type": state.get("scenario_type") or "normal",
            "at_risk_stock": [
                s.model_dump() if hasattr(s, "model_dump") else s for s in at_risk_raw
            ],
            "weather_snapshot": weather_snapshot,
            "weather_summary": dict(weather_snapshot.get("summary") or {}),
            "weather_risk_summary": weather_risk,
            "demand_forecast": dict(state.get("demand_forecast") or {}),
        }
        if human_review_needed:
            kpi_detail["human_review_reason"] = (
                f"max_retries={max_retries()} exhausted with validation still failing"
            )
        # Store all agent traces so GET /api/run/{run_id}/traces can return them.
        kpi_detail["agent_traces"] = list(state.get("agent_traces") or [])

        await create_run_log(
            run_id=run_id,
            message="plan_run_complete",
            level="warning" if human_review_needed else "info",
            plan_id=plan_row.id,
            detail=kpi_detail,
        )
        logger.info("orchestrator_exit: persisted plan_id=%s run_id=%s", plan_id, run_id)

    except Exception as exc:  # noqa: BLE001
        logger.warning("orchestrator_exit: DB persist skipped (%s)", exc)

    # Assemble final_plan
    state["final_plan"] = Plan(
        id=plan_id,
        run_id=run_id,
        route_plan=route_plan or __import__("models.schemas", fromlist=["RoutePlan"]).RoutePlan(),
        validation=validation,
    )

    trace: AgentTrace = {
        "agent_name": "orchestrator_exit",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": ["metrics.compute_kpi_delta", "tools.db.create_plan", "tools.db.create_run_log"],
        "notes": (
            f"plan_id={plan_id or 'not persisted'}; "
            f"scenario_type={state.get('scenario_type', '')}; "
            f"waste_reduction={kpi['waste_reduction_pct']:.1f}%; "
            f"coverage={kpi['coverage_pct']:.1f}%; "
            f"human_review={'YES' if human_review_needed else 'no'}. "
            + scenario_trace_note(state.get("scenario_type", ""))
        ),
        "token_count": None,
    }
    state["agent_traces"] = [*state.get("agent_traces", []), trace]

    logger.info(
        "orchestrator_exit: run=%s waste_reduction=%.1f%% coverage=%.1f%%",
        run_id, kpi["waste_reduction_pct"], kpi["coverage_pct"],
    )
    return state
