"""Validator Agent — rule-based plan feasibility checks. No LLM.

Checks (all deterministic):
  (a) Capacity   : no truck's total pickup load exceeds its capacity_kg.
  (b) Avail window: estimated route duration fits within truck's availability window.
  (c) Severe weather: routes don't visit severe-risk farms when safer alternatives exist.
  (d) Max drive time: total estimated driving time <= 14 h per truck.
  (e) Urgent coverage: every at-risk item with < 12 h remaining has a route covering it.

On failure:
  - state["validation_result"] = ValidationResult(valid=False, errors=[...])
  - state["retry_count"] incremented by 1

On pass:
  - state["validation_result"] = ValidationResult(valid=True)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from agents.review_flags import max_retries, needs_human_review
from memory.state import AgentFarmState, AgentTrace
from models.schemas import Farm, Truck, ValidationResult

logger = logging.getLogger(__name__)

_AVG_SPEED_KMH = 50.0     # conservative truck speed estimate
_MAX_DRIVE_HOURS = 14.0   # legal maximum driving hours per truck per day
_URGENT_THRESHOLD_H = 12.0  # at-risk items below this are "must-cover"
_RELAXATION_STEP = 0.15  # 15 % demand reduction per retry (logistics demand_scale)


def _relaxation_factor_applied(retry_count: int) -> float:
    """Constraint slack multiplier shown in traces (e.g. 1.15 after first failure)."""
    return round(1.0 + retry_count * _RELAXATION_STEP, 2)


def _demand_scale_for_retry(retry_count: int) -> float:
    """Demand scale logistics applies on the next solve after *retry_count* failures."""
    return round(max(0.65, 1.0 - retry_count * _RELAXATION_STEP), 2)


def _collect_violation_types(
    *,
    capacity_violations: int,
    time_window_violations: int,
    weather_blocked_routes: list[str],
    spoilage_priority_violations: int,
    driver_hours_violations: int,
) -> list[str]:
    types: list[str] = []
    if capacity_violations > 0:
        types.append("capacity")
    if time_window_violations > 0:
        types.append("time_window")
    if weather_blocked_routes:
        types.append("weather")
    if spoilage_priority_violations > 0:
        types.append("spoilage_priority")
    if driver_hours_violations > 0:
        types.append("driver_hours")
    return types


_VALIDATOR_TOOLS = [
    "check_capacity",
    "check_time_windows",
    "check_weather_routes",
    "check_spoilage_priority",
    "check_driver_hours",
]


def _farm_map(farms: list[Farm]) -> dict[str, Farm]:
    return {f.id: f for f in farms}


def _truck_map(trucks: list[Truck]) -> dict[str, Truck]:
    return {t.id: t for t in trucks}


def _check_capacity(state: AgentFarmState, errors: list[str]) -> int:
    """(a) No truck's cumulative pickup load exceeds capacity_kg."""
    violations = 0
    at_risk_lookup = {s.farm_id: s.kg_at_risk for s in (state.get("at_risk_stock") or [])}
    truck_by_id = _truck_map(state.get("trucks") or [])
    route_plan = state.get("route_plan")
    if not route_plan:
        return 0

    for route in route_plan.routes:
        truck = truck_by_id.get(route.truck_id)
        if not truck:
            continue
        total_pickup = sum(
            at_risk_lookup.get(stop.label or "", 0.0)
            for stop in route.stops
            if stop.demand_point_id is None
        )
        if total_pickup > truck.capacity_kg:
            violations += 1
            errors.append(
                f"CAPACITY: truck {route.truck_id} load {total_pickup:.0f} kg "
                f"> capacity {truck.capacity_kg:.0f} kg"
            )
    return violations


def _check_availability(state: AgentFarmState, errors: list[str], warnings: list[str]) -> int:
    """(b) Estimated route duration fits inside truck availability window."""
    violations = 0
    truck_by_id = _truck_map(state.get("trucks") or [])
    route_plan = state.get("route_plan")
    if not route_plan:
        return 0

    for route in route_plan.routes:
        truck = truck_by_id.get(route.truck_id)
        if not truck or not route.distance_km:
            continue

        duration_h = route.distance_km / _AVG_SPEED_KMH
        avail_start_min = truck.availability_start.hour * 60 + truck.availability_start.minute
        avail_end_min = truck.availability_end.hour * 60 + truck.availability_end.minute
        avail_h = (avail_end_min - avail_start_min) / 60.0

        if avail_h <= 0:
            warnings.append(f"Truck {route.truck_id} has zero availability window; skipping window check")
            continue

        if duration_h > avail_h:
            violations += 1
            errors.append(
                f"AVAIL_WINDOW: truck {route.truck_id} estimated {duration_h:.1f} h "
                f"> availability {avail_h:.1f} h "
                f"({truck.availability_start}–{truck.availability_end})"
            )
    return violations


def _all_severe_weather(risk_summary: dict[str, str]) -> bool:
    """True when every farm in the risk summary is severe."""
    if not risk_summary:
        return False
    return all(level == "severe" for level in risk_summary.values())


def _check_severe_weather(
    state: AgentFarmState,
    errors: list[str],
    warnings: list[str],
) -> list[str]:
    """(c) Routes avoid severe-risk farms when non-severe alternatives exist."""
    blocked_routes: list[str] = []
    risk_summary = state.get("weather_risk_summary") or {}
    farms = state.get("farms") or []
    route_plan = state.get("route_plan")
    if not route_plan or not risk_summary:
        return blocked_routes

    farm_by_id = _farm_map(farms)
    severe_ids = {fid for fid, r in risk_summary.items() if r == "severe"}
    if not severe_ids:
        return blocked_routes

    if _all_severe_weather(risk_summary):
        warnings.append(
            "ALL_SEVERE_WEATHER: every farm is severe-risk; routing through "
            "severe farms is unavoidable — prioritise urgent pickups only"
        )
        return blocked_routes

    for route in route_plan.routes:
        for stop in route.stops:
            if stop.demand_point_id is not None or not stop.label:
                continue
            if stop.label not in severe_ids:
                continue
            farm = farm_by_id.get(stop.label)
            if not farm:
                continue
            safer_alternatives = [
                f for f in farms
                if f.crop_type == farm.crop_type
                and risk_summary.get(f.id, "normal") != "severe"
                and f.id != farm.id
            ]
            if safer_alternatives:
                if route.truck_id not in blocked_routes:
                    blocked_routes.append(route.truck_id)
                errors.append(
                    f"SEVERE_WEATHER: truck {route.truck_id} routes through "
                    f"severe-risk farm {stop.label} ({farm.crop_type}) "
                    f"while {len(safer_alternatives)} safer alternative(s) exist"
                )
            else:
                warnings.append(
                    f"All {farm.crop_type} farms have severe weather risk; "
                    f"visit to {stop.label} is unavoidable"
                )
    return blocked_routes


def _check_drive_time(state: AgentFarmState, errors: list[str]) -> int:
    """(d) Total estimated driving time <= 14 h per truck."""
    violations = 0
    route_plan = state.get("route_plan")
    if not route_plan:
        return 0

    for route in route_plan.routes:
        if not route.distance_km:
            continue
        duration_h = route.distance_km / _AVG_SPEED_KMH
        if duration_h > _MAX_DRIVE_HOURS:
            violations += 1
            errors.append(
                f"DRIVE_TIME: truck {route.truck_id} estimated {duration_h:.1f} h "
                f"> legal max {_MAX_DRIVE_HOURS:.0f} h"
            )
    return violations


def _check_urgent_coverage(state: AgentFarmState, errors: list[str]) -> int:
    """(e) Every at-risk item with < 12 h remaining is covered by some route stop."""
    violations = 0
    at_risk = state.get("at_risk_stock") or []
    route_plan = state.get("route_plan")
    urgent = [
        s for s in at_risk
        if (s.hours_until_spoilage or 0.0) < _URGENT_THRESHOLD_H
    ]
    if not urgent:
        return 0

    visited_farm_ids: set[str] = set()
    if route_plan:
        for route in route_plan.routes:
            for stop in route.stops:
                if stop.demand_point_id is None and stop.label:
                    visited_farm_ids.add(stop.label)

    for item in urgent:
        if item.farm_id not in visited_farm_ids:
            violations += 1
            errors.append(
                f"URGENT_UNCOVERED: farm {item.farm_id} ({item.crop_type}) "
                f"has {item.hours_until_spoilage or 0:.1f} h remaining "
                f"but is not in any route"
            )
    return violations


async def run(state: AgentFarmState) -> AgentFarmState:
    """Run all five rule checks; update validation_result and retry_count."""
    t0 = datetime.now(timezone.utc)

    errors: list[str] = []
    warnings: list[str] = []

    capacity_violations = _check_capacity(state, errors)
    time_window_violations = _check_availability(state, errors, warnings)
    weather_blocked_routes = _check_severe_weather(state, errors, warnings)
    driver_hours_violations = _check_drive_time(state, errors)
    spoilage_priority_violations = _check_urgent_coverage(state, errors)

    passed = len(errors) == 0
    state["validation_result"] = ValidationResult(
        valid=passed,
        errors=errors,
        warnings=warnings,
    )

    if not passed:
        state["retry_count"] = (state.get("retry_count") or 0) + 1

    retry_count = state.get("retry_count") or 0
    cap = max_retries()
    human_review = needs_human_review(state)
    violation_types = _collect_violation_types(
        capacity_violations=capacity_violations,
        time_window_violations=time_window_violations,
        weather_blocked_routes=weather_blocked_routes,
        spoilage_priority_violations=spoilage_priority_violations,
        driver_hours_violations=driver_hours_violations,
    )
    will_retry = (not passed) and retry_count < cap
    max_retries_reached = (not passed) and retry_count >= cap

    risk_summary = state.get("weather_risk_summary") or {}
    all_severe = _all_severe_weather(risk_summary)

    details = {
        "all_severe_weather": all_severe,
        "capacity_violations": capacity_violations,
        "time_window_violations": time_window_violations,
        "weather_blocked_routes": weather_blocked_routes,
        "spoilage_priority_violations": spoilage_priority_violations,
        "driver_hours_violations": driver_hours_violations,
        "valid": passed,
        "errors_count": len(errors),
        "warnings_count": len(warnings),
        "retry_count": retry_count,
        "max_retries": cap,
        "human_review": human_review,
        "retry_triggered": will_retry,
        "max_retries_reached": max_retries_reached,
        "reason_for_retry": violation_types if will_retry else [],
        "relaxation_factor_applied": (
            _relaxation_factor_applied(retry_count) if will_retry else None
        ),
        "demand_scale_next": _demand_scale_for_retry(retry_count) if will_retry else None,
    }

    note_parts = [
        f"valid={passed}",
        f"errors={len(errors)}",
        f"warnings={len(warnings)}",
        f"retry_count={retry_count}",
        f"human_review={human_review}",
    ]
    if will_retry:
        note_parts.append(f"retry_triggered=true relaxation={details['relaxation_factor_applied']}")
        note_parts.append(f"violations={','.join(violation_types) or 'unknown'}")
    if max_retries_reached:
        note_parts.append("max_retries_reached=true")

    trace: AgentTrace = {
        "agent_name": "validator",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": list(_VALIDATOR_TOOLS),
        "execution_type": "deterministic validation engine",
        "notes": " ".join(note_parts),
        "details": details,
        "token_count": 0,
    }
    state["agent_traces"] = [*state.get("agent_traces", []), trace]

    if passed:
        logger.info("validator: PASS (warnings=%d)", len(warnings))
    else:
        logger.warning("validator: FAIL errors=%d: %s", len(errors), errors)

    return state
