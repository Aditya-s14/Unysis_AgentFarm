"""Weather Agent — fetches forecasts for every farm and classifies risk.

No LLM. Pure API + classification logic (risk thresholds live in weather_api).

Tier-1 memory (AgentFarmState) keys written:
  - weather_events        : list[WeatherEvent]  one per farm, same order as state["farms"]
  - weather_risk_summary  : dict[farm_id -> "normal" | "warning" | "severe"]
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from memory.state import AgentFarmState, AgentTrace
from tools.weather_api import fetch_weather

logger = logging.getLogger(__name__)


async def run(state: AgentFarmState) -> AgentFarmState:
    """Populate weather_events and weather_risk_summary; append AgentTrace."""
    t0 = datetime.now(timezone.utc)
    farms = state.get("farms", [])

    events = await fetch_weather(farms)

    # fetch_weather returns one WeatherEvent per farm in the same order.
    # event.severity is the canonical risk level set by _classify_risk.
    risk_summary: dict[str, str] = {
        farm.id: event.severity for farm, event in zip(farms, events)
    }

    state["weather_events"] = events
    state["weather_risk_summary"] = risk_summary

    severe = sum(1 for v in risk_summary.values() if v == "severe")
    warning = sum(1 for v in risk_summary.values() if v == "warning")
    normal = len(risk_summary) - severe - warning

    trace: AgentTrace = {
        "agent_name": "weather_agent",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": ["weather_api.fetch_weather"],
        "notes": (
            f"{len(farms)} farms — "
            f"severe={severe}, warning={warning}, normal={normal}"
        ),
        "token_count": None,
    }
    state["agent_traces"] = [*state.get("agent_traces", []), trace]

    logger.info(
        "weather_agent: %d events (severe=%d, warning=%d, normal=%d)",
        len(events),
        severe,
        warning,
        normal,
    )
    return state
