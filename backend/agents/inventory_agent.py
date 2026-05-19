"""Inventory Agent — spoilage-window calculation and at-risk stock prioritisation.

Memory tiers used:
  Tier 1 (state): reads farms, weather_events, weather_risk_summary; writes at_risk_stock.

Shelf-life table (base days at ambient temperature):
  tomato=4, onion=14, banana=3, mango=5, potato=21, grape=7,
  orange=10, apple=21, corn=5, rice/wheat=180, default=7

Scenario shelf-life adjustment (via scenario_effects.shelf_life_factor):
  heat_wave          → 40% reduction (factor 0.60)
  monsoon_disruption → 20% humidity reduction (factor 0.80)
  normal_day         → no reduction

days_since_harvest:
  Derived from Farm.harvest_window_start; 0 if harvest hasn't started yet.

At-risk threshold:
  A farm is flagged when remaining shelf days ≤ 5 (configurable via the constant below).

One LLM call (OpenAI gpt-4o-mini, temp=0) re-ranks the candidate list by dispatch urgency.
Falls back to ascending hours_until_spoilage sort when no key / call fails.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from config import get_settings
from memory.state import AgentFarmState, AgentTrace
from models.schemas import AtRiskStock, WeatherEvent
from tools.scenario_effects import (
    normalize_scenario_type,
    scenario_adjustment_details,
    scenario_trace_note,
    shelf_life_factor,
)

logger = logging.getLogger(__name__)

# ── Shelf-life table ─────────────────────────────────────────────────────────
_SHELF_LIFE_DAYS: dict[str, int] = {
    "tomato": 4,
    "onion": 14,
    "banana": 3,
    "mango": 5,
    "potato": 21,
    "grape": 7,
    "orange": 10,
    "apple": 21,
    "corn": 5,
    "rice": 180,
    "wheat": 180,
    "default": 7,
}

_AT_RISK_THRESHOLD_DAYS = 5  # flag farms within this many days of spoilage


def _base_shelf_days(crop_type: str) -> int:
    crop_lower = crop_type.lower()
    for key, days in _SHELF_LIFE_DAYS.items():
        if key != "default" and key in crop_lower:
            return days
    return _SHELF_LIFE_DAYS["default"]


def _is_heat_wave(event: WeatherEvent | None) -> bool:
    if event is None:
        return False
    return "heat_wave" in (event.description or "").lower()


def _effective_shelf_days(
    crop_type: str,
    scenario_type: str,
    event: WeatherEvent | None,
) -> float:
    base = _base_shelf_days(crop_type)
    factor = shelf_life_factor(scenario_type)
    return base * factor


async def _llm_rank(
    candidates: list[dict[str, Any]],
) -> tuple[list[str], int | None]:
    """Single OpenAI call (temp=0) to re-rank by dispatch urgency.

    Returns (ranked_farm_id_list, token_count).  Falls back to ([], None) on failure.
    """
    settings = get_settings()
    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key or not candidates:
        return [], None

    try:
        import openai  # lazy import

        prompt = (
            "You are an agricultural logistics prioritization system. "
            "Rank the produce items below by dispatch urgency (most urgent first). "
            "Criteria: hours_until_spoilage (lower = more urgent), kg_at_risk "
            "(higher volume = higher impact), crop perishability, and weather severity.\n\n"
            f"Items:\n{json.dumps(candidates, indent=2, ensure_ascii=False)}\n\n"
            'Return only valid JSON: {"ranked_farm_ids": ["farm_id_1", "farm_id_2", ...]}'
        )

        client = openai.AsyncOpenAI(api_key=api_key, base_url=settings.OPENAI_BASE_URL)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in perishable-goods logistics for Indian agriculture. "
                        "Output only valid JSON with no extra text or markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        raw = resp.choices[0].message.content or "{}"
        data: dict[str, Any] = json.loads(raw)
        ranked = data.get("ranked_farm_ids", [])
        tokens = resp.usage.total_tokens if resp.usage else None

        if isinstance(ranked, list):
            return [str(fid) for fid in ranked], tokens
        return [], tokens

    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM inventory rank call failed: %s", exc)
        return [], None


async def run(state: AgentFarmState) -> AgentFarmState:
    """Inventory Agent: compute spoilage windows, rank at-risk stock, write state."""
    t0 = datetime.now(timezone.utc)
    today = date.today()

    farms = state.get("farms", [])
    weather_events = state.get("weather_events", [])
    weather_risk_summary = state.get("weather_risk_summary", {})
    raw_scenario = state.get("scenario_type_raw") or state.get("scenario_type", "")
    scenario_type = normalize_scenario_type(raw_scenario)
    state["scenario_type"] = scenario_type
    shelf_factor = shelf_life_factor(scenario_type)

    # Build farm_id → WeatherEvent; events are in the same order as farms
    event_by_farm: dict[str, WeatherEvent] = {
        farm.id: event for farm, event in zip(farms, weather_events)
    }

    at_risk: list[AtRiskStock] = []
    candidates: list[dict[str, Any]] = []

    for farm in farms:
        days_since = max(0, (today - farm.harvest_window_start).days)
        if today < farm.harvest_window_start:
            continue  # not yet harvested

        event = event_by_farm.get(farm.id)
        shelf_days = _effective_shelf_days(farm.crop_type, scenario_type, event)
        remaining_days = shelf_days - days_since
        hours_until_spoilage = max(0.0, remaining_days * 24.0)

        if remaining_days > _AT_RISK_THRESHOLD_DAYS:
            continue  # comfortably within shelf life

        risk_level = weather_risk_summary.get(farm.id, "normal")

        # kg at risk scales with urgency: everything is at risk once shelf life passes
        if remaining_days <= 0:
            kg_fraction = 1.0
        elif remaining_days <= 2:
            kg_fraction = 0.85
        else:
            kg_fraction = 0.50
        kg_at_risk = round(farm.typical_yield_kg * kg_fraction, 1)

        reason_parts = [
            f"shelf_life={shelf_days:.1f}d",
            f"days_since_harvest={days_since}",
            f"weather={risk_level}",
        ]
        if shelf_factor < 1.0:
            pct = int(round((1.0 - shelf_factor) * 100))
            reason_parts.append(f"scenario_shelf_adjusted(-{pct}%)")

        risk_until = today + timedelta(days=max(0, int(remaining_days)))

        at_risk.append(
            AtRiskStock(
                farm_id=farm.id,
                crop_type=farm.crop_type,
                kg_at_risk=kg_at_risk,
                reason="; ".join(reason_parts),
                risk_until=risk_until,
                hours_until_spoilage=round(hours_until_spoilage, 1),
            )
        )
        candidates.append(
            {
                "farm_id": farm.id,
                "crop_type": farm.crop_type,
                "hours_until_spoilage": round(hours_until_spoilage, 1),
                "kg_at_risk": kg_at_risk,
                "weather_severity": risk_level,
                "heat_wave": _is_heat_wave(event),
            }
        )

    # LLM re-ranking (single call across all at-risk candidates)
    llm_order, llm_tokens = await _llm_rank(candidates)

    if llm_order:
        order_map = {fid: i for i, fid in enumerate(llm_order)}
        at_risk.sort(key=lambda s: order_map.get(s.farm_id, len(llm_order)))
    else:
        # Deterministic fallback: most urgent first
        at_risk.sort(key=lambda s: s.hours_until_spoilage if s.hours_until_spoilage is not None else float("inf"))

    state["at_risk_stock"] = at_risk

    trace: AgentTrace = {
        "agent_name": "inventory_agent",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": [
            "weather_events (state tier-1)",
            *(["openai.chat.completions"] if llm_tokens else []),
        ],
        "notes": (
            f"{len(farms)} farms evaluated; "
            f"{len(at_risk)} at-risk (threshold<={_AT_RISK_THRESHOLD_DAYS}d, shelf_factor={shelf_factor:.2f}); "
            f"llm_rank={'yes' if llm_order else 'no (sorted by hours_until_spoilage)'}. "
            + scenario_trace_note(raw_scenario)
        ),
        "token_count": llm_tokens,
        "details": {
            "scenario_adjustments": scenario_adjustment_details(
                scenario_type=raw_scenario,
            ),
        },
    }
    state["agent_traces"] = [*state.get("agent_traces", []), trace]

    logger.info(
        "inventory_agent: %d/%d farms at risk, llm_rank=%s",
        len(at_risk),
        len(farms),
        "yes" if llm_order else "no",
    )
    return state
