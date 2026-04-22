"""Pydantic schemas for scenario run requests and responses."""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..models.scenario_run import ScenarioType
from .demand_point_schema import DemandPointCreate, DemandPointRead
from .farm_schema import FarmCreate, FarmRead
from .plan_schema import PlanSchema
from .truck_schema import TruckCreate, TruckRead


class ScenarioConstraints(BaseModel):
    """Optional per-run constraints."""

    max_driver_hours: float = 14.0
    allow_partial_fulfilment: bool = True
    relaxation_factor: float = 1.0
    notes: Optional[str] = None


class ScenarioRequest(BaseModel):
    """Payload for ``POST /api/scenario/run``."""

    scenario_type: ScenarioType = ScenarioType.CUSTOM
    farms: List[FarmCreate] = Field(default_factory=list)
    demand_points: List[DemandPointCreate] = Field(
        default_factory=list, alias="demandPoints"
    )
    trucks: List[TruckCreate] = Field(default_factory=list)
    constraints: ScenarioConstraints = Field(default_factory=ScenarioConstraints)

    model_config = {"populate_by_name": True}


class KPISummary(BaseModel):
    """Headline KPIs for a run."""

    predicted_waste_kg: float = 0.0
    baseline_waste_kg: float = 0.0
    waste_reduction_pct: float = 0.0
    on_time_delivery_pct: float = 0.0
    baseline_on_time_pct: float = 0.0
    on_time_improvement_pct: float = 0.0
    total_cost: float = 0.0
    baseline_cost: float = 0.0
    cost_savings_pct: float = 0.0


class ScenarioResponse(BaseModel):
    """Response for ``POST /api/scenario/run``."""

    run_id: uuid.UUID = Field(..., alias="runId")
    plan: PlanSchema
    kpis: KPISummary
    farms: List[FarmRead] = Field(default_factory=list)
    demand_points: List[DemandPointRead] = Field(
        default_factory=list, alias="demandPoints"
    )
    trucks: List[TruckRead] = Field(default_factory=list)
    traces_summary: Dict[str, int] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}
