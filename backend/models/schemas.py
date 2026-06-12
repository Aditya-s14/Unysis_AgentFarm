"""Pydantic v2 domain and API models for AgentFarm Optimizer."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, RootModel


# --- Inputs ---


NotifyChannel = Literal["sms", "voice", "both", "none"]


class Farm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    lat: float
    lng: float
    crop_type: str
    acreage: float = Field(ge=0)
    typical_yield_kg: float = Field(ge=0)
    harvest_window_start: date
    harvest_window_end: date
    phone: str | None = None
    preferred_language: str = "en"
    notify_channel: NotifyChannel = "sms"
    notify_opt_in: bool = False


class DemandPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    lat: float
    lng: float
    type: Literal["apmc", "private", "retail"]
    base_demand_per_day: float = Field(ge=0)


class Truck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    capacity_kg: float = Field(gt=0)
    cost_per_km: float = Field(ge=0)
    availability_start: time
    availability_end: time
    driver_phone: str | None = None


# --- Agent outputs ---


class WeatherEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    event_date: date
    region: str | None = None
    description: str = ""
    severity: str = "moderate"
    precipitation_mm: float | None = None


class DemandForecast(RootModel[dict[str, list[float]]]):
    """Per-key demand series (e.g. mandi id -> daily forecasts)."""

    pass


class AtRiskStock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    farm_id: str
    crop_type: str
    kg_at_risk: float = Field(ge=0)
    reason: str = ""
    risk_until: date | None = None
    hours_until_spoilage: float | None = Field(default=None, ge=0)


class RouteStop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=0)
    lat: float
    lng: float
    demand_point_id: str | None = None
    load_kg: float | None = Field(default=None, ge=0)
    eta_minutes_from_start: int | None = Field(default=None, ge=0)
    label: str | None = None


class Route(BaseModel):
    model_config = ConfigDict(extra="forbid")

    truck_id: str
    stops: list[RouteStop] = Field(default_factory=list)
    distance_km: float | None = Field(default=None, ge=0)
    duration_minutes: float | None = Field(default=None, ge=0)
    # Road-snapped polyline [[lat, lng], ...] through the stops (T7).
    # None → no routing provider available; renderers draw straight lines.
    geometry: list[list[float]] | None = None


class RoutePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    routes: list[Route] = Field(default_factory=list)
    objective_value: float | None = None
    notes: str | None = None


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# --- Plan / logs / outcomes ---


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | str | None = None
    run_id: str | None = None
    external_ref: str | None = None
    route_plan: RoutePlan = Field(default_factory=RoutePlan)
    created_at: datetime | None = None
    validation: ValidationResult | None = None


class RunLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | str | None = None
    plan_id: UUID | str | None = None
    run_id: str
    level: str = "info"
    message: str
    detail: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None


class PlanOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | str | None = None
    plan_id: UUID | str
    waste_kg_predicted: float
    waste_kg_actual: float
    delivery_time_predicted_hours: float
    delivery_time_actual_hours: float
    demand_predicted: float
    demand_actual: float
    notes: str | None = None
    # Tier-2 outcome store dimensions (optional; populated from DB / CSV seed)
    demand_point_id: str | None = None
    crop_type: str | None = None
    day_of_week: str | None = None
    road_segment: str | None = None


# --- API ---


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "scenario"
    description: str | None = None
    farm_ids: list[str] = Field(default_factory=list)
    demand_point_ids: list[str] = Field(default_factory=list)
    truck_ids: list[str] = Field(default_factory=list)
    horizon_days: int = Field(default=7, ge=1, le=90)
    params: dict[str, object] = Field(default_factory=dict)


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str = "accepted"
    message: str | None = None


class AdvisorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    context: dict[str, object] = Field(default_factory=dict)


class AdvisorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str
    sources: list[str] = Field(default_factory=list)
    run_id: str | None = None
    session_id: str | None = None


# --- Breakdown assistance ---


BreakdownReason = Literal[
    "engine_failure",
    "flat_tire",
    "accident",
    "fuel_empty",
    "other",
]

BreakdownIncidentStatus = Literal["pending_approval", "approved", "failed"]


class BreakdownReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    truck_id: str
    reported_by: str = "fpo"
    reason: BreakdownReason = "engine_failure"
    completed_farm_ids: list[str] = Field(default_factory=list)
    spare_truck_id: str | None = None


class BreakdownIncident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str
    run_id: str
    truck_id: str
    reported_by: str
    reason: BreakdownReason
    status: BreakdownIncidentStatus
    completed_farm_ids: list[str] = Field(default_factory=list)
    pending_farm_ids: list[str] = Field(default_factory=list)
    spare_truck_id: str | None = None
    route_plan_before: dict[str, object] = Field(default_factory=dict)
    route_plan_after: dict[str, object] = Field(default_factory=dict)
    validation: ValidationResult | None = None
    created_at: str | None = None
    approved_at: str | None = None
    notifications: dict[str, int] | None = None


class ReplanPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident: BreakdownIncident
    affected_farms: list[str] = Field(default_factory=list)
    spare_truck_id: str | None = None
    validation_valid: bool = True
    validation_errors: list[str] = Field(default_factory=list)


# --- Live truck GPS tracking ---


TruckTrackingStatus = Literal["on_route", "deviating", "stale", "unknown"]
DeviationAlertStatus = Literal["open", "resolved"]


class PositionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    reported_at: datetime | None = None
    accuracy_m: float | None = Field(default=None, ge=0)
    reported_by: str = "driver"


class TruckPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    truck_id: str
    lat: float
    lng: float
    reported_at: str
    on_route: bool
    deviation_km: float = Field(ge=0)
    status: TruckTrackingStatus


class RouteDeviationAlert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    run_id: str
    truck_id: str
    deviation_km: float
    threshold_km: float
    lat: float
    lng: float
    status: DeviationAlertStatus
    notified_at: str | None = None
    notifications: dict[str, int] | None = None
    created_at: str | None = None


class PositionIngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: TruckPosition
    alert_triggered: bool = False
    alert: RouteDeviationAlert | None = None
