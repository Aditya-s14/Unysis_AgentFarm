"""Weather Agent — fetches forecasts for every farm and classifies risk.

No LLM. Pure API + classification logic (risk thresholds live in weather_api).

Tier-1 memory (AgentFarmState) keys written:
  - weather_events        : list[WeatherEvent]  one per farm, same order as state["farms"]
  - weather_risk_summary  : dict[farm_id -> "normal" | "warning" | "severe"]
  - weather_fetch_meta    : source / overlay metadata for dashboard transparency
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from memory.state import AgentFarmState, AgentTrace
from tools.scenario_effects import (
    LIVE,
    normalize_scenario_type,
    scenario_adjustment_details,
    scenario_trace_note,
)
from tools.weather_api import fetch_weather

logger = logging.getLogger(__name__)


async def run(state: AgentFarmState) -> AgentFarmState:
    """Populate weather_events and weather_risk_summary; append AgentTrace."""
    t0 = datetime.now(timezone.utc)
    farms = state.get("farms", [])
    raw_scenario = state.get("scenario_type_raw") or state.get("scenario_type", "")
    scenario_type = normalize_scenario_type(raw_scenario)
    state["scenario_type"] = scenario_type

    result = await fetch_weather(farms, scenario_type=scenario_type)
    events = result["events"]
    meta = result.get("meta") or {}

    risk_summary: dict[str, str] = {
        farm.id: event.severity for farm, event in zip(farms, events)
    }

    state["weather_events"] = events
    state["weather_risk_summary"] = risk_summary
    state["weather_fetch_meta"] = meta

    weather_source = meta.get("weather_source", "synthetic_fallback")
    if weather_source == "synthetic_fallback":
        state["scenario_type"] = LIVE

    severe = sum(1 for v in risk_summary.values() if v == "severe")
    warning = sum(1 for v in risk_summary.values() if v == "warning")
    normal = len(risk_summary) - severe - warning

    scenario_mod = meta.get("scenario_modifier_applied", True)

    trace: AgentTrace = {
        "agent_name": "weather_agent",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": ["weather_api.fetch_weather (current+forecast)"],
        "notes": (
            f"{len(farms)} farms — severe={severe}, warning={warning}, normal={normal}; "
            f"weather_source={weather_source}; "
            f"scenario_modifier_applied={str(scenario_mod).lower()}; "
            f"fallback_mode={meta.get('fallback_mode', 'none')}; "
            + scenario_trace_note(
                state.get("scenario_type") if weather_source == "synthetic_fallback" else raw_scenario
            )
        ),
        "token_count": None,
        "details": {
            "scenario_adjustments": scenario_adjustment_details(
                scenario_type=state.get("scenario_type") or raw_scenario,
                weather_fetch_meta=meta,
            ),
        },
    }
    state["agent_traces"] = [*state.get("agent_traces", []), trace]

    logger.info(
        "weather_agent: %d events (severe=%d, warning=%d, normal=%d) source=%s",
        len(events),
        severe,
        warning,
        normal,
        weather_source,
    )
    return state
