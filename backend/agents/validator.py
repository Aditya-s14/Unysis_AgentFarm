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

from memory.state import AgentFarmState, AgentTrace
from models.schemas import Farm, Truck, ValidationResult

logger = logging.getLogger(__name__)

_AVG_SPEED_KMH = 50.0     # conservative truck speed estimate
_MAX_DRIVE_HOURS = 14.0   # legal maximum driving hours per truck per day
_URGENT_THRESHOLD_H = 12.0  # at-risk items below this are "must-cover"


def _farm_map(farms: list[Farm]) -> dict[str, Farm]:
    return {f.id: f for f in farms}


def _truck_map(trucks: list[Truck]) -> dict[str, Truck]:
    return {t.id: t for t in trucks}


def _check_capacity(state: AgentFarmState, errors: list[str]) -> None:
    """(a) No truck's cumulative pickup load exceeds capacity_kg."""
    at_risk_lookup = {s.farm_id: s.kg_at_risk for s in (state.get("at_risk_stock") or [])}
    truck_by_id = _truck_map(state.get("trucks") or [])
    route_plan = state.get("route_plan")
    if not route_plan:
        return

    for route in route_plan.routes:
        truck = truck_by_id.get(route.truck_id)
        if not truck:
            continue
        total_pickup = sum(
            at_risk_lookup.get(stop.label or "", 0.0)
            for stop in route.stops
            if stop.demand_point_id is None  # farm pickups
        )
        if total_pickup > truck.capacity_kg:
            errors.append(
                f"CAPACITY: truck {route.truck_id} load {total_pickup:.0f} kg "
                f"> capacity {truck.capacity_kg:.0f} kg"
            )


def _check_availability(state: AgentFarmState, errors: list[str], warnings: list[str]) -> None:
    """(b) Estimated route duration fits inside truck availability window."""
    truck_by_id = _truck_map(state.get("trucks") or [])
    route_plan = state.get("route_plan")
    if not route_plan:
        return

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
            errors.append(
                f"AVAIL_WINDOW: truck {route.truck_id} estimated {duration_h:.1f} h "
                f"> availability {avail_h:.1f} h "
                f"({truck.availability_start}–{truck.availability_end})"
            )


def _check_severe_weather(state: AgentFarmState, errors: list[str], warnings: list[str]) -> None:
    """(c) Routes avoid severe-risk farms when non-severe alternatives exist for the same crop."""
    risk_summary = state.get("weather_risk_summary") or {}
    farms = state.get("farms") or []
    route_plan = state.get("route_plan")
    if not route_plan or not risk_summary:
        return

    farm_by_id = _farm_map(farms)
    severe_ids = {fid for fid, r in risk_summary.items() if r == "severe"}
    if not severe_ids:
        return

    for route in route_plan.routes:
        for stop in route.stops:
            if stop.demand_point_id is not None or not stop.label:
                continue
            if stop.label not in severe_ids:
                continue
            farm = farm_by_id.get(stop.label)
            if not farm:
                continue
            # Is there a non-severe farm of the same crop type?
            safer_alternatives = [
                f for f in farms
                if f.crop_type == farm.crop_type
                and risk_summary.get(f.id, "normal") != "severe"
                and f.id != farm.id
            ]
            if safer_alternatives:
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


def _check_drive_time(state: AgentFarmState, errors: list[str]) -> None:
    """(d) Total estimated driving time <= 14 h per truck."""
    route_plan = state.get("route_plan")
    if not route_plan:
        return

    for route in route_plan.routes:
        if not route.distance_km:
            continue
        duration_h = route.distance_km / _AVG_SPEED_KMH
        if duration_h > _MAX_DRIVE_HOURS:
            errors.append(
                f"DRIVE_TIME: truck {route.truck_id} estimated {duration_h:.1f} h "
                f"> legal max {_MAX_DRIVE_HOURS:.0f} h"
            )


def _check_urgent_coverage(state: AgentFarmState, errors: list[str]) -> None:
    """(e) Every at-risk item with < 12 h remaining is covered by some route stop."""
    at_risk = state.get("at_risk_stock") or []
    route_plan = state.get("route_plan")
    urgent = [
        s for s in at_risk
        if (s.hours_until_spoilage or 0.0) < _URGENT_THRESHOLD_H
    ]
    if not urgent:
        return

    visited_farm_ids: set[str] = set()
    if route_plan:
        for route in route_plan.routes:
            for stop in route.stops:
                if stop.demand_point_id is None and stop.label:
                    visited_farm_ids.add(stop.label)

    for item in urgent:
        if item.farm_id not in visited_farm_ids:
            errors.append(
                f"URGENT_UNCOVERED: farm {item.farm_id} ({item.crop_type}) "
                f"has {item.hours_until_spoilage or 0:.1f} h remaining "
                f"but is not in any route"
            )


async def run(state: AgentFarmState) -> AgentFarmState:
    """Run all five rule checks; update validation_result and retry_count."""
    t0 = datetime.now(timezone.utc)

    errors: list[str] = []
    warnings: list[str] = []

    _check_capacity(state, errors)
    _check_availability(state, errors, warnings)
    _check_severe_weather(state, errors, warnings)
    _check_drive_time(state, errors)
    _check_urgent_coverage(state, errors)

    passed = len(errors) == 0
    state["validation_result"] = ValidationResult(
        valid=passed,
        errors=errors,
        warnings=warnings,
    )

    if not passed:
        state["retry_count"] = (state.get("retry_count") or 0) + 1

    trace: AgentTrace = {
        "agent_name": "validator",
        "start_time": t0.isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "tools_used": [],
        "notes": (
            f"valid={passed}; errors={len(errors)}; warnings={len(warnings)}; "
            f"retry_count={state.get('retry_count', 0)}"
        ),
        "token_count": None,
    }
    state["agent_traces"] = [*state.get("agent_traces", []), trace]

    if passed:
        logger.info("validator: PASS (warnings=%d)", len(warnings))
    else:
        logger.warning("validator: FAIL errors=%d: %s", len(errors), errors)

    return state
