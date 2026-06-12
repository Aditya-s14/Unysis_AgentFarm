"""Rebuild pipeline state from persisted run_log snapshot for FPO approval dispatch."""

from __future__ import annotations

from typing import Any

from memory.state import AgentFarmState
from models.db_models import PlanTable
from models.schemas import (
    AtRiskStock,
    DemandPoint,
    Farm,
    RoutePlan,
    Truck,
    ValidationResult,
)


def _parse_farms(raw: list[Any]) -> list[Farm]:
    return [Farm.model_validate(item) for item in raw]


def _parse_demand_points(raw: list[Any]) -> list[DemandPoint]:
    out: list[DemandPoint] = []
    for item in raw:
        data = dict(item)
        if "type" not in data and "point_type" in data:
            data["type"] = data.pop("point_type")
        out.append(DemandPoint.model_validate(data))
    return out


def _parse_trucks(raw: list[Any]) -> list[Truck]:
    return [Truck.model_validate(item) for item in raw]


def _parse_at_risk(raw: list[Any]) -> list[AtRiskStock]:
    return [AtRiskStock.model_validate(item) for item in raw]


def get_scenario_snapshot_from_detail(detail: dict[str, Any]) -> dict[str, Any] | None:
    snap = detail.get("scenario_snapshot")
    return snap if isinstance(snap, dict) else None


def rebuild_state_from_snapshot(
    *,
    run_id: str,
    plan: PlanTable,
    detail: dict[str, Any],
) -> AgentFarmState:
    """Construct AgentFarmState for notification dispatch after FPO approval."""
    snap = get_scenario_snapshot_from_detail(detail)
    if snap is None:
        raise ValueError(
            "Run has no scenario_snapshot; re-run the scenario with an updated backend"
        )

    route_plan_data = snap.get("route_plan") or plan.route_plan_json or {}
    validation_data = snap.get("validation_result") or plan.validation_json

    state: AgentFarmState = {
        "run_id": run_id,
        "scenario_type": str(snap.get("scenario_type") or "normal"),
        "farms": _parse_farms(snap.get("farms") or []),
        "demand_points": _parse_demand_points(snap.get("demand_points") or []),
        "trucks": _parse_trucks(snap.get("trucks") or []),
        "at_risk_stock": _parse_at_risk(detail.get("at_risk_stock") or []),
        "route_plan": RoutePlan.model_validate(route_plan_data),
        "validation_result": (
            ValidationResult.model_validate(validation_data)
            if validation_data
            else ValidationResult(valid=True, errors=[])
        ),
        "retry_count": int(snap.get("retry_count") or 0),
        "weather_fetch_meta": dict(snap.get("weather_fetch_meta") or {}),
        "weather_risk_summary": dict(
            detail.get("weather_risk_summary") or snap.get("weather_risk_summary") or {},
        ),
        "demand_forecast": dict(detail.get("demand_forecast") or {}),
    }
    return state


def approval_status_for_plan(plan: PlanTable | None) -> str:
    """Return pending | approved | dispatched for API consumers."""
    if plan is None:
        return "pending"
    if plan.notifications_dispatched_at is not None:
        return "dispatched"
    if plan.approved_at is not None:
        return "approved"
    return "pending"
