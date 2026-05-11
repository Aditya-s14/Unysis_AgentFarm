"""Advisor Agent — decoupled on-demand Q&A service (NOT in the main LangGraph graph).

Entry point:
    response = await answer_query(run_id, session_id, question)

Memory tiers used:
  Tier 2 (Postgres): load Plan by run_id for context.
  Tier 3 (Redis session buffer): load conversation history, push new turns.

One LLM call per query (OpenAI / OpenRouter, temp=0.3).
Persona: "Kisan Mitra" — a friendly field officer who answers in plain language.
Falls back to a canned message if LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from config import get_settings
from memory.session_buffer import get_history, push_message
from models.schemas import AdvisorResponse

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are Kisan Mitra (Farmer's Friend), an agricultural logistics advisor for Indian farmers.
Speak in simple, warm, plain language — no jargon, no bullet lists unless asked.
You have access to the current optimized dispatch plan for this farm cluster.
Answer in 2–4 sentences. Be specific and actionable.
If you don't have enough information, say so honestly and suggest what to do next.\
"""

# Shown when the LLM call itself throws (network/auth error mid-request).
_FALLBACK_REPLY = (
    "I'm having trouble connecting right now. "
    "Please try again in a moment, or contact your field supervisor directly."
)

# Shown during the demo when no API key is configured — always gives useful context.
_DEMO_REPLY = (
    "Based on the current plan: Farm Nandi Valley has tomatoes with 72h until spoilage "
    "— highest priority for dispatch. Truck tr-004 is assigned. "
    "Recommend harvesting before 6AM tomorrow."
)


def _plan_summary(plan_row: object | None) -> str:
    """Convert a PlanTable row to a concise text summary for the LLM context."""
    if plan_row is None:
        return "No plan available for this run."

    rp = getattr(plan_row, "route_plan_json", {}) or {}
    routes = rp.get("routes", [])
    val = getattr(plan_row, "validation_json", {}) or {}
    valid = val.get("valid", True)
    n_routes = len(routes)
    total_stops = sum(len(r.get("stops", [])) for r in routes)
    plan_date = getattr(plan_row, "created_at", None)
    date_str = plan_date.strftime("%d %b %Y") if plan_date else "unknown date"

    return (
        f"Plan created {date_str}. "
        f"{n_routes} truck route(s) covering {total_stops} pickup/delivery stops. "
        f"Feasibility check: {'passed' if valid else 'FAILED — human review needed'}."
    )


async def _load_plan(run_id: str) -> object | None:
    """Load PlanTable row by run_id from Postgres. Returns None gracefully."""
    try:
        from tools.db import get_session_maker
        from models.db_models import PlanTable
        from sqlalchemy import select

        async with get_session_maker()() as session:
            q = await session.execute(
                select(PlanTable).where(PlanTable.run_id == run_id)
            )
            return q.scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001
        logger.debug("advisor: plan load failed for run_id=%s: %s", run_id, exc)
        return None


async def _llm_answer(
    question: str,
    plan_summary: str,
    history: list[dict],
    run_id: str,
) -> tuple[str, int | None]:
    """Call OpenAI / OpenRouter (temp=0.3) and return (reply, token_count)."""
    settings = get_settings()
    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        logger.warning(
            "advisor: OPENAI_API_KEY missing/empty — returning demo static answer. "
            "Set OPENAI_API_KEY in .env to enable live LLM responses. "
            "OPENAI_BASE_URL=%s",
            settings.OPENAI_BASE_URL,
        )
        return _DEMO_REPLY, None

    try:
        import openai

        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

        # Inject plan context as a system-level assistant turn
        messages.append({
            "role": "assistant",
            "content": f"[Context — current plan for run {run_id}]\n{plan_summary}",
        })

        # Inject conversation history (Tier-3 memory, last 10 messages)
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": question})

        client = openai.AsyncOpenAI(api_key=api_key, base_url=settings.OPENAI_BASE_URL)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=settings.advisor_temp,
            messages=messages,
        )
        reply = (resp.choices[0].message.content or "").strip() or _FALLBACK_REPLY
        tokens = resp.usage.total_tokens if resp.usage else None
        return reply, tokens

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "advisor LLM call failed (base_url=%s, model=gpt-4o-mini): %r",
            settings.OPENAI_BASE_URL, exc,
            exc_info=True,
        )
        return _FALLBACK_REPLY, None


async def answer_query(
    run_id: str,
    session_id: str,
    question: str,
) -> AdvisorResponse:
    """Answer a farmer's plain-language question about a run's plan.

    Args:
        run_id:     The pipeline run whose plan to use as context.
        session_id: Redis session key for conversation history (Tier-3).
        question:   The farmer's question.

    Returns:
        AdvisorResponse with reply, run_id, session_id, and sources.
    """
    t0 = datetime.now(timezone.utc)

    # Tier-2: load plan context
    plan_row = await _load_plan(run_id)
    summary = _plan_summary(plan_row)

    # Tier-3: load conversation history
    history = await get_history(session_id)

    # LLM call (temp=0.3 for friendly, slightly creative tone)
    reply, tokens = await _llm_answer(question, summary, history, run_id)

    # Tier-3: persist this turn to session buffer
    await push_message(session_id, "user", question)
    await push_message(session_id, "assistant", reply)

    elapsed_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    sources = [f"plan:{run_id}"]
    if plan_row is not None:
        sources.append(f"db_plan_id:{getattr(plan_row, 'id', 'unknown')}")

    logger.info(
        "advisor_agent: run=%s session=%s tokens=%s elapsed=%dms",
        run_id, session_id, tokens, elapsed_ms,
    )

    return AdvisorResponse(
        reply=reply,
        sources=sources,
        run_id=run_id,
        session_id=session_id,
    )
