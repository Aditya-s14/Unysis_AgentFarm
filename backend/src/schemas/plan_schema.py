"""Pydantic schemas for plans, routes, validation and outcomes."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.weather_event import WeatherRiskLevel


class RouteStop(BaseModel):
    """A single stop on a route (pick-up or drop-off)."""

    sequence: int = Field(..., ge=0)
    stop_type: str = Field(..., description="'pickup' or 'dropoff'")
    location_id: uuid.UUID
    location_name: Optional[str] = None
    latitude: float
    longitude: float
    load_kg: float = 0.0
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None


class Route(BaseModel):
    """A truck's ordered sequence of stops."""

    truck_id: uuid.UUID
    stops: List[RouteStop] = Field(default_factory=list)
    total_distance_km: float = 0.0
    total_load_kg: float = 0.0
    total_cost: float = 0.0


class RoutePlan(BaseModel):
    """Collection of all truck routes produced by the VRP solver."""

    routes: List[Route] = Field(default_factory=list)
    unassigned_farms: List[uuid.UUID] = Field(default_factory=list)
    solver_status: str = "unknown"
    solver_runtime_ms: float = 0.0


class ValidationResult(BaseModel):
    """Output of the Validator node."""

    is_valid: bool
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class WeatherEventSchema(BaseModel):
    """Weather forecast entry used in agent state."""

    farm_id: uuid.UUID
    event_date: date
    rain_mm: float = 0.0
    temperature_c: float = 0.0
    humidity_pct: float = 0.0
    risk_level: WeatherRiskLevel = WeatherRiskLevel.NORMAL


class AtRiskStock(BaseModel):
    """Produce at elevated spoilage risk."""

    farm_id: uuid.UUID
    crop_type: str
    quantity_kg: float
    days_until_spoilage: int
    priority_score: float = 0.0


class DemandForecast(BaseModel):
    """7-day demand forecast for a single demand point."""

    demand_point_id: uuid.UUID
    daily_demand_kg: List[float] = Field(..., min_length=1)
    adjustments_applied: List[str] = Field(default_factory=list)


class PlanSchema(BaseModel):
    """Full plan object returned to API clients."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[uuid.UUID] = None
    run_id: uuid.UUID
    plan_date: date
    assignments: List[Route] = Field(default_factory=list)
    expected_waste_kg: float = 0.0
    expected_cost: float = 0.0
    kpis: Dict[str, float] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class OutcomeRecord(BaseModel):
    """A single actual-vs-predicted outcome entry."""

    farm_id: Optional[uuid.UUID] = None
    demand_point_id: Optional[uuid.UUID] = None
    predicted_waste_kg: float = 0.0
    actual_waste_kg: float = 0.0
    predicted_delivery_minutes: float = 0.0
    actual_delivery_minutes: float = 0.0
    demand_predicted_kg: float = 0.0
    demand_actual_kg: float = 0.0
    notes: Optional[str] = None


class OutcomeLogRequest(BaseModel):
    """Payload for ``POST /api/outcome/log``."""

    run_id: uuid.UUID
    outcomes: List[OutcomeRecord] = Field(..., min_length=1)
