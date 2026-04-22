"""Pydantic v2 schemas used for API I/O."""

from .farm_schema import FarmCreate, FarmRead, FarmUpdate
from .demand_point_schema import DemandPointCreate, DemandPointRead, DemandPointUpdate
from .truck_schema import TruckCreate, TruckRead, TruckUpdate
from .scenario_schema import (
    ScenarioRequest,
    ScenarioResponse,
    ScenarioConstraints,
    KPISummary,
)
from .plan_schema import (
    PlanSchema,
    RouteStop,
    Route,
    RoutePlan,
    ValidationResult,
    WeatherEventSchema,
    AtRiskStock,
    DemandForecast,
    OutcomeLogRequest,
    OutcomeRecord,
)
from .advisor_schema import AdvisorRequest, AdvisorResponse

__all__ = [
    "FarmCreate",
    "FarmRead",
    "FarmUpdate",
    "DemandPointCreate",
    "DemandPointRead",
    "DemandPointUpdate",
    "TruckCreate",
    "TruckRead",
    "TruckUpdate",
    "ScenarioRequest",
    "ScenarioResponse",
    "ScenarioConstraints",
    "KPISummary",
    "PlanSchema",
    "RouteStop",
    "Route",
    "RoutePlan",
    "ValidationResult",
    "WeatherEventSchema",
    "AtRiskStock",
    "DemandForecast",
    "OutcomeLogRequest",
    "OutcomeRecord",
    "AdvisorRequest",
    "AdvisorResponse",
]
