"""Demand Forecast Agent — 7-day demand forecast per demand point.

Memory tiers used:
  Tier 1 (state): reads farms, demand_points, weather_risk_summary; writes demand_forecast.
  Tier 2 (outcome_store): get_demand_history() for historical bias correction.

One LLM call (OpenAI, temp=0) reasons about festival/seasonal multipliers given the
current date, crop mix, and weather context.  Falls back to rule-based logic when the
key is absent or the call fails.

Festival rules (calendar-based, no hardcoded years):
  Diwali:    Oct 15 – Nov 5   → fruits/mangoes/bananas ×1.5, others ×1.2
  Pongal:    Jan 10 – Jan 17  → vegetables/tomatoes/onions ×1.3, others ×1.1
  Holi:      Mar 18 – Mar 30  → all ×1.15
  Navratri:  Sep 25 – Oct 5   → fruits/mangoes ×1.3, others ×1.2

Weather supply adjustment:
  >30% of farms severe → demand from those routes reduced 15% (supply squeeze).
  Any severe farms     → 5% reduction.

Bias correction:
  outcome_store.get_demand_history(demand_point_id, crop_type, day_of_week)
  → mean(actual / predicted) ratio applied per demand point per weekday.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from config import get_settings
from memory.outcome_store import get_demand_history
from memory.state import AgentFarmState, AgentTrace
from models.schemas import DemandPoint, FarmerCommitment, BuyerDemandPost, PlanOutcome
from tools.commitments import (
    COMMITMENT_WEIGHT,
    FORECAST_WEIGHT,
    aggregate_commitments_by_mandi,
)
from tools.buyer_demands import aggregate_buyer_demand_by_mandi
from tools.scenario_effects import scenario_trace_note

logger = logging.getLogger(__name__)

# ── Festival windows ──────────────────────────────────────────────────────────
# Each entry: (month_start, day_start), (month_end, day_end), {crop_keyword: mult, "default": mult}
_FESTIVALS: list[tuple[tuple[int, int], tuple[int, int], dict[str, float]]] = [
    ((10, 15), (11, 5),  {"fruit": 1.5, "mango": 1.5, "banana": 1.5, "default": 1.2}),
    ((1, 10),  (1, 17),  {"vegetable": 1.3, "tomato": 1.3, "onion": 1.3, "default": 1.1}),
    ((3, 18),  (3, 30),  {"default": 1.15}),
    ((9, 25),  (10, 5),  {"fruit": 1.3, "mango": 1.3, "default": 1.2}),
]


def _festival_multiplier(dt: date, crop_type: str) -> float:
    md = (dt.month, dt.day)
    crop_lower = crop_type.lower()
    for start, end, factors in _FESTIVALS:
        if start <= md <= end:
            for key, factor in factors.items():
                if key != "default" and key in crop_lower:
                    return factor
            return factors.get("default", 1.0)
    return 1.0


def _weather_supply_factor(weather_risk_summary: dict[str, str]) -> float:
    """Global supply-side reduction when severe-weather farms dominate."""
    total = max(len(weather_risk_summary), 1)
    severe = sum(1 for r in weather_risk_summary.values() if r == "severe")
    if severe / total > 0.3:
        return 0.85
    if severe > 0:
        return 0.95
    return 1.0


async def _bias_correction(
    demand_point_id: str,
    crop_types: list[str],
    day_of_week: str,
) -> float:
    """Mean actual/predicted ratio from outcome_store (Tier-2 memory).

    Queries the last N outcomes for this demand point × each crop type × weekday
    and returns the mean ratio.  Returns 1.0 when no history exists.
    """
    outcomes: list[PlanOutcome] = []
    for ct in set(crop_types):
        try:
            rows = await get_demand_history(demand_point_id, ct, day_of_week)
            outcomes.extend(rows)
        except Exception as exc:  # noqa: BLE001
            logger.warning("demand history query failed dp=%s crop=%s: %s", demand_point_id, ct, exc)

    ratios = [
        o.demand_actual / o.demand_predicted
        for o in outcomes
        if o.demand_predicted and o.demand_predicted > 0
    ]
    if not ratios:
        return 1.0
    return sum(ratios) / len(ratios)


async def _llm_multipliers(
    today: date,
    demand_points: list[DemandPoint],
    weather_risk_summary: dict[str, str],
    crop_types: list[str],
) -> tuple[dict[str, list[float]], int | None]:
    """Single OpenAI call (temp=0) → per-demand-point 7-day multiplier lists.

    Returns (multiplier_dict, token_count).  On any failure returns ({}, None).
    """
    settings = get_settings()
    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        return {}, None

    try:
        import openai  # lazy import; only needed when key is present

        severe_pct = round(
            100
            * sum(1 for r in weather_risk_summary.values() if r == "severe")
            / max(len(weather_risk_summary), 1)
        )
        dp_summaries = [
            {
                "id": dp.id,
                "name": dp.name,
                "type": dp.type,
                "base_demand_kg": dp.base_demand_per_day,
            }
            for dp in demand_points
        ]
        prompt = (
            f"Today is {today.isoformat()}. "
            f"Crops in supply: {', '.join(sorted(set(crop_types)))}. "
            f"{severe_pct}% of supply farms face severe weather disruption. "
            "For each demand point, return a JSON object with the demand point id as key "
            "and a list of exactly 7 daily demand multipliers (starting today) as value. "
            "Consider the Indian festival calendar, seasonal patterns, crop availability, "
            "and weather-driven supply disruptions. Multipliers must be between 0.5 and 2.5.\n\n"
            f"Demand points:\n{json.dumps(dp_summaries, ensure_ascii=False)}\n\n"
            'Return only valid JSON, e.g. {"dp-1": [1.0, 1.1, 1.0, 1.3, 1.0, 1.0, 1.2]}'
        )

        client = openai.AsyncOpenAI(api_key=api_key, base_url=settings.OPENAI_BASE_URL)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an agricultural market demand analyst for Indian mandis. "
                        "Output only valid JSON with no extra text or markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        raw = resp.choices[0].message.content or "{}"
        data: dict[str, Any] = json.loads(raw)
        tokens = resp.usage.total_tokens if resp.usage else None

        # Validate: keep only entries that look like 7-element float lists
        valid: dict[str, list[float]] = {}
        for k, v in data.items():
            if isinstance(v, list) and len(v) == 7:
                try:
                    valid[k] = [float(x) for x in v]
                except (TypeError, ValueError):
                    pass
        return valid, tokens

    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM demand multipliers failed: %s", exc)
        return {}, None


async def run(state: AgentFarmState) -> AgentFarmState:
    """Demand Forecast Agent: 7-day forecast per demand point."""
    t0 = datetime.now(timezone.utc)
    today = date.today()

    demand_points = state.get("demand_points", [])
    weather_risk_summary = state.get("weather_risk_summary", {})
    farms = state.get("farms", [])
    crop_types = [f.crop_type for f in farms]

    supply_factor = _weather_supply_factor(weather_risk_summary)

    # Single LLM call covers all demand points at once
    llm_data, llm_tokens = await _llm_multipliers(
        today, demand_points, weather_risk_summary, crop_types
    )

    forecast: dict[str, list[float]] = {}

    raw_commitments: list[FarmerCommitment] = list(state.get("farmer_commitments") or [])
    committed_by_dp = aggregate_commitments_by_mandi(raw_commitments, farms, demand_points)
    weighted_applied = bool(committed_by_dp)

    raw_buyer_demands: list[BuyerDemandPost] = list(state.get("buyer_demands") or [])
    buyer_by_dp = aggregate_buyer_demand_by_mandi(raw_buyer_demands)
    buyer_applied = bool(buyer_by_dp)

    for dp in demand_points:
        base = dp.base_demand_per_day
        today_dow = today.strftime("%A").lower()

        # Tier-2 bias correction for this demand point + today's weekday
        bias = await _bias_correction(dp.id, crop_types, today_dow)

        series: list[float] = []
        for offset in range(7):
            day = today + timedelta(days=offset)

            # Rule-based festival multiplier (average over all crop types in supply)
            rule_mult = (
                sum(_festival_multiplier(day, ct) for ct in crop_types) / len(crop_types)
                if crop_types
                else 1.0
            )

            # Blend LLM (60%) with rule-based (40%) when LLM returned a value
            if dp.id in llm_data:
                llm_mult = llm_data[dp.id][offset]
                combined = 0.6 * llm_mult + 0.4 * rule_mult
            else:
                combined = rule_mult

            day_forecast = round(base * combined * supply_factor * bias, 2)

            if offset == 0:
                committed_kg = committed_by_dp.get(dp.id, 0.0)
                if committed_kg > 0:
                    day_forecast = round(
                        FORECAST_WEIGHT * day_forecast + COMMITMENT_WEIGHT * committed_kg,
                        2,
                    )
                if dp.type == "private":
                    posted_kg = buyer_by_dp.get(dp.id, 0.0)
                    if posted_kg > 0:
                        day_forecast = round(max(day_forecast, posted_kg), 2)

            series.append(day_forecast)

        forecast[dp.id] = series

    state["demand_forecast"] = forecast

    severe_pct = round(
        100
        * sum(1 for r in weather_risk_summary.values() if r == "severe")
        / max(len(weather_risk_summary), 1)
    )
    trace: AgentTrace = {
        "agent_name": "demand_agent",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": [
            "outcome_store.get_demand_history",
            *(["openai.chat.completions"] if llm_tokens else []),
        ],
        "notes": (
            f"{len(demand_points)} demand points; 7-day forecast; "
            f"llm={'yes' if llm_tokens else 'no (rule-based fallback)'}; "
            f"supply_factor={supply_factor}; bias_correction=applied; "
            f"severe_pct={severe_pct}%; "
            f"commitments={len(raw_commitments)}"
            + ("; weighted_demand=applied" if weighted_applied else "")
            + (f"; buyer_demands={len(raw_buyer_demands)}" if raw_buyer_demands else "")
            + ("; buyer_demand_floor=applied" if buyer_applied else "")
            + ". "
            + scenario_trace_note(state.get("scenario_type", ""))
        ),
        "token_count": llm_tokens,
    }
    state["agent_traces"] = [*state.get("agent_traces", []), trace]

    logger.info(
        "demand_agent: %d demand points, llm=%s, supply_factor=%.2f",
        len(demand_points),
        "yes" if llm_tokens else "no",
        supply_factor,
    )
    return state
