"""Advisor Agent — decoupled on-demand Q&A service (NOT in the main LangGraph graph).

Entry point:
    response = await answer_query(run_id, session_id, question)

Memory tiers used:
  Tier 2 (Postgres): load Plan + RunLog by run_id for rich context.
  Tier 3 (Redis session buffer): load conversation history, push new turns.

One LLM call per query (OpenAI / OpenRouter, temp=0.3).
Persona: "Kisan Mitra" — a friendly field officer who answers in plain language.
Falls back to a canned message if LLM is unavailable.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from config import get_settings
from memory.session_buffer import get_history, push_message
from models.schemas import AdvisorResponse

logger = logging.getLogger(__name__)

_FALLBACK_REPLY = (
    "I'm having trouble connecting right now. "
    "Please try again in a moment, or contact your field supervisor directly."
)

# ── Data loading helpers ───────────────────────────────────────────────────────


async def _load_plan_row(run_id: str) -> object | None:
    """Return PlanTable row for run_id, or None on any failure."""
    try:
        from tools.db import get_plan_by_run_id

        return await get_plan_by_run_id(run_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("advisor: plan load failed run_id=%s: %s", run_id, exc)
        return None


async def _resolve_plan_and_run(run_id: str) -> tuple[object | None, dict[str, Any], str]:
    """Load plan row and run detail; fall back to the latest plan when run_id is stale."""
    plan_row = await _load_plan_row(run_id)
    effective_run_id = run_id
    if plan_row is None:
        try:
            from tools.db import get_latest_plan

            latest = await get_latest_plan()
            if latest is not None and getattr(latest, "run_id", None):
                plan_row = latest
                effective_run_id = str(latest.run_id)
                logger.info(
                    "advisor: run %s not found — using latest plan run_id=%s",
                    run_id,
                    effective_run_id,
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("advisor: latest plan lookup failed: %s", exc)
    run_detail = await _load_run_detail(effective_run_id)
    return plan_row, run_detail, effective_run_id


async def _load_run_detail(run_id: str) -> dict[str, Any]:
    """Return plan_run_complete detail_json for run_id (KPIs + plan snapshot), or {}."""
    try:
        from tools.weather_store import get_run_weather_snapshot

        cached_weather = await get_run_weather_snapshot(run_id)
        from tools.db import list_run_logs_for_run

        logs = await list_run_logs_for_run(run_id)
        for log in reversed(logs):
            if log.message == "plan_run_complete" and log.detail_json:
                detail = dict(log.detail_json)
                if cached_weather and not detail.get("weather_snapshot"):
                    detail["weather_snapshot"] = cached_weather
                return detail
        if cached_weather:
            return {"weather_snapshot": cached_weather}
    except Exception as exc:  # noqa: BLE001
        logger.debug("advisor: run detail load failed run_id=%s: %s", run_id, exc)
    return {}


async def _load_name_maps() -> tuple[dict[str, str], dict[str, tuple[str, float]]]:
    """Return (farm_id → name, dp_id → (name, base_demand_per_day)) from DB."""
    farm_names: dict[str, str] = {}
    dp_info: dict[str, tuple[str, float]] = {}
    try:
        from sqlalchemy import select

        from models.db_models import DemandPointRow, FarmRow
        from tools.db import get_session_maker

        async with get_session_maker()() as session:
            for row in await session.scalars(select(FarmRow)):
                farm_names[row.id] = row.name
            for row in await session.scalars(select(DemandPointRow)):
                dp_info[row.id] = (row.name, row.base_demand_per_day)
    except Exception as exc:  # noqa: BLE001
        logger.debug("advisor: name maps load failed: %s", exc)
    return farm_names, dp_info


# ── Plan analytics ─────────────────────────────────────────────────────────────


def _compute_incoming_by_mandi(
    routes: list[dict],
    at_risk_lookup: dict[str, float],
) -> dict[str, float]:
    """Sum incoming kg per mandi from route stops (mirrors dashboard mandi logic)."""
    incoming: dict[str, float] = defaultdict(float)
    for route in routes:
        stops = route.get("stops") or []
        farm_stops = [s for s in stops if not s.get("demand_point_id") and s.get("label")]
        dp_stops = [s for s in stops if s.get("demand_point_id")]

        farm_load_stops = sum(
            float(s["load_kg"]) for s in farm_stops
            if s.get("load_kg") is not None and float(s["load_kg"]) > 0
        )
        farm_load_risk = sum(at_risk_lookup.get(s.get("label") or "", 0.0) for s in farm_stops)
        route_farm_load = farm_load_stops if farm_load_stops > 0 else farm_load_risk

        n_dp = len(dp_stops)
        for stop in dp_stops:
            dp_id = stop.get("demand_point_id")
            if not dp_id:
                continue
            if stop.get("load_kg") is not None and float(stop["load_kg"]) > 0:
                load_kg = float(stop["load_kg"])
            elif n_dp > 0:
                load_kg = route_farm_load / n_dp
            else:
                load_kg = 0.0
            incoming[dp_id] += load_kg
    return dict(incoming)


def _expected_demand_kg(
    dp_id: str,
    dp_info: dict[str, tuple[str, float]],
    demand_forecast: dict[str, list[float]],
) -> float:
    series = demand_forecast.get(dp_id)
    if isinstance(series, list) and series:
        return float(series[0])
    info = dp_info.get(dp_id)
    return float(info[1]) if info else 0.0


def _build_mandi_rows(
    dp_info: dict[str, tuple[str, float]],
    routes: list[dict],
    at_risk_stock: list[dict],
    demand_forecast: dict[str, list[float]],
) -> list[dict[str, Any]]:
    at_risk_lookup = {
        s.get("farm_id"): float(s.get("kg_at_risk") or 0)
        for s in at_risk_stock
        if s.get("farm_id")
    }
    incoming_map = _compute_incoming_by_mandi(routes, at_risk_lookup)

    rows: list[dict[str, Any]] = []
    for dp_id, (name, _base) in dp_info.items():
        expected = _expected_demand_kg(dp_id, dp_info, demand_forecast)
        incoming = round(incoming_map.get(dp_id, 0.0), 1)
        total_available = incoming
        net_balance = total_available - expected
        fulfilment_pct = (
            min(200.0, max(0.0, (total_available / expected) * 100.0)) if expected > 0 else 0.0
        )
        shortage_kg = max(0.0, -net_balance)
        if fulfilment_pct < 50:
            status = "CRITICAL SHORTAGE"
        elif fulfilment_pct < 80:
            status = "SHORTAGE"
        elif fulfilment_pct < 100:
            status = "NEARLY MET"
        else:
            status = "SUPPLY MET"
        rows.append({
            "id": dp_id,
            "name": name,
            "expected_demand_kg": round(expected, 1),
            "incoming_supply_kg": incoming,
            "shortage_kg": round(shortage_kg, 1),
            "fulfilment_pct": round(fulfilment_pct, 1),
            "status": status,
        })
    rows.sort(key=lambda r: r["shortage_kg"], reverse=True)
    return rows


def _build_farm_lines(
    at_risk_stock: list[dict],
    farm_names: dict[str, str],
    routes: list[dict],
) -> list[str]:
    """Farm lines with spoilage windows; include routed farms even if not in at_risk."""
    seen: set[str] = set()
    lines: list[str] = []

    for stock in sorted(
        at_risk_stock,
        key=lambda s: s.get("hours_until_spoilage")
        if s.get("hours_until_spoilage") is not None
        else 9999.0,
    ):
        fid = stock.get("farm_id")
        if not fid or fid in seen:
            continue
        seen.add(fid)
        name = farm_names.get(fid, fid)
        hours = stock.get("hours_until_spoilage")
        kg = stock.get("kg_at_risk")
        spoil = f"{round(hours)}h spoilage window" if hours is not None else "spoilage window n/a"
        kg_str = f", {round(kg)} kg at risk" if kg is not None else ""
        lines.append(f"{name} ({fid}): {spoil}{kg_str}")

    for route in routes:
        for stop in route.get("stops") or []:
            if stop.get("demand_point_id"):
                continue
            fid = stop.get("label")
            if not fid or fid in seen:
                continue
            seen.add(fid)
            name = farm_names.get(fid, fid)
            lines.append(f"{name} ({fid}): on route (spoilage data not in this run)")

    return lines


def _build_route_summary_lines(
    routes: list[dict],
    farm_names: dict[str, str],
    dp_info: dict[str, tuple[str, float]],
) -> list[str]:
    lines: list[str] = []
    for route in routes:
        truck_id = route.get("truck_id", "?")
        stops = sorted(route.get("stops") or [], key=lambda s: s.get("sequence", 0))
        destinations: list[str] = []
        for stop in stops:
            dp_id = stop.get("demand_point_id")
            if dp_id:
                info = dp_info.get(dp_id)
                destinations.append(info[0] if info else dp_id)
            else:
                fid = stop.get("label")
                if fid:
                    destinations.append(farm_names.get(fid, fid))
        dest_str = " → ".join(destinations) if destinations else "no stops"
        dist = route.get("distance_km")
        dist_str = f", {max(0, float(dist)):.0f} km" if dist is not None else ""
        lines.append(f"{truck_id} → {dest_str}{dist_str}")
    return lines


def _format_weather_line(
    weather_summary: dict,
    weather_risk: dict[str, str],
    weather_snapshot: dict | None = None,
) -> str:
    if weather_snapshot and weather_snapshot.get("farm_readings"):
        src = weather_snapshot.get("weather_source") or "recorded"
        fetched = weather_snapshot.get("fetched_at") or ""
        parts = [f"OpenWeather ({src})"]
        if fetched:
            parts.append(f"fetched {fetched[:19]}Z")
        summary = weather_snapshot.get("summary") or weather_summary
        if summary.get("temperature_c") is not None:
            parts.append(f"avg {summary['temperature_c']}°C")
        if summary.get("rainfall_mm") is not None:
            parts.append(f"max rain {summary['rainfall_mm']} mm")
        if summary.get("risk_level"):
            parts.append(f"risk {summary['risk_level']}")
        elevated = [
            r for r in weather_snapshot["farm_readings"]
            if r.get("severity") in ("warning", "severe")
        ]
        if elevated:
            names = [r.get("farm_name") or r.get("farm_id") for r in elevated[:5]]
            parts.append(f"{len(elevated)} farms elevated: {', '.join(n for n in names if n)}")
        return "; ".join(parts)

    if not weather_summary and not weather_risk:
        return "Not recorded for this run."
    parts: list[str] = []
    if weather_summary:
        cond = weather_summary.get("condition") or weather_summary.get("scenario_type")
        temp = weather_summary.get("temperature_c")
        rain = weather_summary.get("rainfall_mm")
        risk = weather_summary.get("risk_level")
        if cond:
            parts.append(str(cond))
        if temp is not None:
            parts.append(f"{temp}°C")
        if rain is not None:
            parts.append(f"rain {rain} mm")
        if risk:
            parts.append(f"risk {risk}")
        affected = weather_summary.get("affected_farms") or []
        if affected:
            parts.append(f"affected farms: {', '.join(affected[:5])}")
        advisory = weather_summary.get("transport_advisory")
        if advisory:
            parts.append(f"transport: {advisory}")
    severe = [k for k, v in weather_risk.items() if v in ("severe", "warning")]
    if severe and not parts:
        parts.append(f"{len(severe)} farms with elevated weather risk")
    return "; ".join(parts) if parts else "Weather data present (see run logs)."


def _format_farm_weather_lines(
    weather_snapshot: dict | None,
    *,
    limit: int = 12,
) -> str:
    """Compact per-farm OpenWeather lines for the advisor system prompt."""
    if not weather_snapshot:
        return "No per-farm weather readings stored for this run."
    readings = weather_snapshot.get("farm_readings") or []
    if not readings:
        return "No per-farm weather readings stored for this run."

    def _line(r: dict) -> str:
        name = r.get("farm_name") or r.get("farm_id") or "?"
        sev = r.get("severity") or "normal"
        temp = r.get("temp_c")
        rain = r.get("rain_mm")
        bits = [f"{name} ({sev})"]
        if temp is not None:
            bits.append(f"{temp}°C")
        if rain is not None:
            bits.append(f"rain {rain} mm")
        if r.get("humidity_pct") is not None:
            bits.append(f"humidity {int(r['humidity_pct'])}%")
        if r.get("wind_speed_ms") is not None:
            bits.append(f"wind {r['wind_speed_ms']} m/s")
        return ", ".join(bits)

    sorted_readings = sorted(
        readings,
        key=lambda r: {"severe": 0, "warning": 1, "normal": 2}.get(
            str(r.get("severity") or "normal"), 3
        ),
    )
    lines = [_line(r) for r in sorted_readings[:limit]]
    if len(readings) > limit:
        lines.append(f"... and {len(readings) - limit} more farms")
    return "; ".join(lines)


def _build_system_prompt(
    run_id: str,
    farm_list: str,
    mandi_list: str,
    route_summary: str,
    waste_reduction_pct: float | None,
    weather_line: str,
    farm_weather_line: str,
    validation_line: str,
) -> str:
    waste_str = (
        f"{waste_reduction_pct:.1f}%"
        if waste_reduction_pct is not None
        else "not available for this run"
    )
    return f"""You are Kisan Mitra, advisor for AgentFarm Optimizer.
Speak in simple, warm, plain language — 2–4 sentences unless the user asks for a list.
Be specific and actionable using ONLY the current plan data below.

Current plan (run_id: {run_id}):
Farms: {farm_list}
Mandis: {mandi_list}
Routes: {route_summary}
Weather overview: {weather_line}
Per-farm OpenWeather readings: {farm_weather_line}
Validation: {validation_line}
Waste reduction: {waste_str}

Rules:
- Always answer using the data above. Quote mandi/farm names and numbers from the plan.
- For weather questions, use the per-farm OpenWeather readings (temperature, rain, severity) stored for this run.
- Never say "I don't have the specific requirements" or "I don't have specific information" when the answer is in the data above.
- If exact information is missing, say "This run does not contain X, but based on available data …" and use what you do have.
- For shortage questions, compare Mandis by shortage_kg and fulfilment_pct from the list above."""


# ── Context assembly ──────────────────────────────────────────────────────────


def _assemble_plan_context(
    run_id: str,
    plan_row: object | None,
    run_detail: dict[str, Any],
    farm_names: dict[str, str],
    dp_info: dict[str, tuple[str, float]],
) -> dict[str, Any]:
    rp: dict = {}
    val: dict = {}
    if plan_row is not None:
        rp = getattr(plan_row, "route_plan_json", {}) or {}
        val = getattr(plan_row, "validation_json", {}) or {}

    routes = rp.get("routes") or []
    at_risk_stock = run_detail.get("at_risk_stock") or []
    if not isinstance(at_risk_stock, list):
        at_risk_stock = []
    demand_forecast = run_detail.get("demand_forecast") or {}
    if not isinstance(demand_forecast, dict):
        demand_forecast = {}
    weather_summary = run_detail.get("weather_summary") or {}
    weather_risk = run_detail.get("weather_risk_summary") or {}
    weather_snapshot = run_detail.get("weather_snapshot") or {}
    if not weather_snapshot.get("farm_readings") and weather_summary:
        weather_snapshot = {"summary": weather_summary, "farm_readings": []}

    farm_lines = _build_farm_lines(at_risk_stock, farm_names, routes)
    mandi_rows = _build_mandi_rows(dp_info, routes, at_risk_stock, demand_forecast)
    route_lines = _build_route_summary_lines(routes, farm_names, dp_info)

    mandi_lines = [
        (
            f"{m['name']}: expected {m['expected_demand_kg']:.0f} kg/day, "
            f"incoming {m['incoming_supply_kg']:.0f} kg, "
            f"shortage {m['shortage_kg']:.0f} kg ({m['fulfilment_pct']:.0f}% fulfilment, {m['status']})"
        )
        for m in mandi_rows[:10]
    ]
    route_lines = route_lines[:8]
    farm_lines = farm_lines[:10]

    waste_reduction = run_detail.get("waste_reduction_pct")
    if waste_reduction is not None:
        try:
            waste_reduction = float(waste_reduction)
        except (TypeError, ValueError):
            waste_reduction = None

    valid = val.get("valid", True)
    errors = val.get("errors") or []
    validation_line = (
        "passed"
        if valid
        else f"failed — {'; '.join(str(e) for e in errors[:3])}"
    )

    farm_list = "; ".join(farm_lines) if farm_lines else "none listed"
    mandi_list = "; ".join(mandi_lines) if mandi_lines else "none listed"
    route_summary = "; ".join(route_lines) if route_lines else "no routes in plan"
    weather_line = _format_weather_line(weather_summary, weather_risk, weather_snapshot)
    farm_weather_line = _format_farm_weather_lines(weather_snapshot)

    system_prompt = _build_system_prompt(
        run_id=run_id,
        farm_list=farm_list,
        mandi_list=mandi_list,
        route_summary=route_summary,
        waste_reduction_pct=waste_reduction,
        weather_line=weather_line,
        farm_weather_line=farm_weather_line,
        validation_line=validation_line,
    )

    return {
        "system_prompt": system_prompt,
        "mandi_rows": mandi_rows,
        "farm_lines": farm_lines,
        "route_lines": route_lines,
        "waste_reduction_pct": waste_reduction,
        "weather_snapshot": weather_snapshot,
        "weather_line": weather_line,
    }


def _try_rule_based_answer(question: str, ctx: dict[str, Any]) -> str | None:
    """Answer common questions from structured context when LLM is unavailable."""
    q = question.lower()
    weather_snapshot: dict = ctx.get("weather_snapshot") or {}
    readings: list[dict] = weather_snapshot.get("farm_readings") or []

    if readings and re.search(
        r"\b(weather|rain|rainfall|temperature|temp|heat|humidity|wind|forecast)\b",
        q,
    ):
        if re.search(r"\b(severe|worst|highest risk|dangerous)\b", q):
            bad = [r for r in readings if r.get("severity") in ("severe", "warning")]
            if bad:
                top = sorted(
                    bad,
                    key=lambda r: {"severe": 0, "warning": 1}.get(str(r.get("severity")), 2),
                )[:3]
                names = ", ".join(
                    f"{r.get('farm_name', r.get('farm_id'))} ({r.get('temp_c')}°C, rain {r.get('rain_mm')} mm, {r.get('severity')})"
                    for r in top
                )
                return (
                    f"From the OpenWeather readings stored for this run, the highest-risk farms are: {names}."
                )
        if re.search(r"\b(rain|rainfall|wet)\b", q):
            wet = sorted(readings, key=lambda r: float(r.get("rain_mm") or 0), reverse=True)[:3]
            if wet and float(wet[0].get("rain_mm") or 0) > 0:
                names = ", ".join(
                    f"{r.get('farm_name', r.get('farm_id'))} ({r.get('rain_mm')} mm)"
                    for r in wet
                )
                return f"Heaviest rain in the stored OpenWeather data: {names}."
        if re.search(r"\b(hot|heat|temperature|temp)\b", q):
            hot = sorted(readings, key=lambda r: float(r.get("temp_c") or 0), reverse=True)[:3]
            names = ", ".join(
                f"{r.get('farm_name', r.get('farm_id'))} ({r.get('temp_c')}°C)"
                for r in hot
            )
            return f"Warmest farms in the stored OpenWeather readings: {names}."

    mandi_rows: list[dict] = ctx.get("mandi_rows") or []
    if mandi_rows and re.search(
        r"\b(demand|demands|volume|throughput)\b",
        q,
    ) and re.search(
        r"\b(mandi|market|apmc|which|highest|most|biggest|largest|top)\b",
        q,
    ):
        top = max(mandi_rows, key=lambda m: m["expected_demand_kg"])
        runners = sorted(
            mandi_rows,
            key=lambda m: m["expected_demand_kg"],
            reverse=True,
        )[1:3]
        msg = (
            f"{top['name']} has the highest expected demand in this plan — "
            f"about {top['expected_demand_kg']:.0f} kg/day. "
            f"Trucks are scheduled to deliver {top['incoming_supply_kg']:.0f} kg "
            f"({top['fulfilment_pct']:.0f}% fulfilment, {top['status']})."
        )
        if runners:
            msg += (
                f" Next: {runners[0]['name']} "
                f"({runners[0]['expected_demand_kg']:.0f} kg/day expected)."
            )
        return msg

    if not mandi_rows:
        return None

    if re.search(r"\b(shortage|shortages|deficit|under.?suppl)\b", q) and re.search(
        r"\b(mandi|market|apmc|which|biggest|largest|most)\b",
        q,
    ):
        worst = mandi_rows[0]
        runners = mandi_rows[1:3]
        msg = (
            f"Based on the current plan (run {ctx.get('run_id', '')[:8]}…), "
            f"{worst['name']} has the biggest shortage — about {worst['shortage_kg']:.0f} kg short "
            f"({worst['fulfilment_pct']:.0f}% fulfilment, {worst['status']}). "
            f"Expected demand is {worst['expected_demand_kg']:.0f} kg/day with "
            f"{worst['incoming_supply_kg']:.0f} kg incoming on assigned trucks."
        )
        if runners and runners[0]["shortage_kg"] > 0:
            msg += (
                f" Next highest: {runners[0]['name']} "
                f"({runners[0]['shortage_kg']:.0f} kg short)."
            )
        return msg

    route_lines: list[str] = ctx.get("route_lines") or []
    farm_lines: list[str] = ctx.get("farm_lines") or []
    if route_lines and re.search(r"\b(route|routes|monsoon|rain|weather|transport)\b", q):
        top_routes = "; ".join(route_lines[:3])
        weather = ctx.get("weather_line") or "Weather data not recorded."
        return (
            f"For this run, key truck routes are: {top_routes}. "
            f"Weather context: {weather}. "
            "In heavy rain, stick to the assigned route and allow extra time at farm pickups."
        )

    farm_match = re.search(r"farm\s*#?\s*(\d+)", q)
    if farm_match and farm_lines:
        num = farm_match.group(1)
        match_line = next(
            (line for line in farm_lines if f"#{num}" in line.lower() or f"farm {num}" in line.lower()),
            None,
        )
        if not match_line and len(farm_lines) >= int(num):
            match_line = farm_lines[int(num) - 1]
        if match_line:
            return (
                f"For Farm #{num} in this plan: {match_line}. "
                "Follow the assigned truck pickup window and send stock to the routed mandi."
            )

    return None


# ── LLM call ──────────────────────────────────────────────────────────────────


async def _llm_answer(
    question: str,
    system_prompt: str,
    history: list[dict],
) -> tuple[str, int | None]:
    """Call OpenAI / OpenRouter (temp=0.3) and return (reply, token_count)."""
    settings = get_settings()
    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        return "", None

    try:
        import openai

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
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
            max_tokens=settings.advisor_max_tokens,
            messages=messages,
        )
        reply = (resp.choices[0].message.content or "").strip()
        tokens = resp.usage.total_tokens if resp.usage else None
        return reply, tokens

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "advisor LLM call failed (base_url=%s, model=gpt-4o-mini): %r",
            settings.OPENAI_BASE_URL,
            exc,
            exc_info=True,
        )
        return "", None


# ── Public entry point ────────────────────────────────────────────────────────


async def answer_query(
    run_id: str,
    session_id: str,
    question: str,
) -> AdvisorResponse:
    """Answer a farmer's plain-language question about a run's plan."""
    t0 = datetime.now(timezone.utc)

    plan_row, run_detail, effective_run_id = await _resolve_plan_and_run(run_id)
    farm_names, dp_info = await _load_name_maps()

    ctx = _assemble_plan_context(effective_run_id, plan_row, run_detail, farm_names, dp_info)
    ctx["run_id"] = effective_run_id
    system_prompt = ctx["system_prompt"]
    logger.debug("advisor system_prompt:\n%s", system_prompt)

    history = await get_history(session_id)

    reply, tokens = await _llm_answer(question, system_prompt, history)
    if not reply:
        ruled = _try_rule_based_answer(question, ctx)
        if ruled:
            reply, tokens = ruled, None
        elif plan_row is None and not ctx.get("mandi_rows"):
            reply = (
                "I don't have plan data for this run yet. "
                "Run a scenario from the Scenario page, then ask again."
            )
            tokens = None
        elif not (get_settings().OPENAI_API_KEY or "").strip():
            logger.warning(
                "advisor: OPENAI_API_KEY missing and no rule match — generic demo hint.",
            )
            reply = (
                "I can answer plan questions once OPENAI_API_KEY is set. "
                "From the loaded plan data, check the Mandis line in the system context "
                "for shortage_kg per market."
            )
            tokens = None
        else:
            reply = _FALLBACK_REPLY
            tokens = None

    await push_message(session_id, "user", question)
    await push_message(session_id, "assistant", reply)

    elapsed_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    sources = [f"plan:{effective_run_id}"]
    if plan_row is not None:
        sources.append(f"db_plan_id:{getattr(plan_row, 'id', 'unknown')}")
    if run_detail:
        sources.append("run_log:plan_snapshot")

    logger.info(
        "advisor_agent: run=%s session=%s tokens=%s elapsed=%dms",
        run_id,
        session_id,
        tokens,
        elapsed_ms,
    )

    return AdvisorResponse(
        reply=reply,
        sources=sources,
        run_id=effective_run_id,
        session_id=session_id,
    )
