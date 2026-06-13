"""POST /api/economics/farm-margins — per-farm P&L after scenario run."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.schemas import (
    AtRiskStock,
    DemandPoint,
    Farm,
    FarmEconomicsRow,
    RoutePlan,
    Truck,
)
from tools.farm_economics import compute_farm_economics
from tools.price_accept_store import list_acceptances

router = APIRouter()
logger = logging.getLogger(__name__)


class _DemandPointIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    lat: float
    lng: float
    type: str | None = None
    point_type: str | None = None
    base_demand_per_day: float

    @model_validator(mode="after")
    def _coerce_type(self) -> "_DemandPointIn":
        if self.type is None:
            self.type = self.point_type or "apmc"
        return self

    def to_schema(self) -> DemandPoint:
        return DemandPoint(
            id=self.id,
            name=self.name,
            lat=self.lat,
            lng=self.lng,
            type=self.type,  # type: ignore[arg-type]
            base_demand_per_day=self.base_demand_per_day,
        )


class FarmMarginsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    farms: list[Farm]
    demand_points: list[_DemandPointIn]
    trucks: list[Truck]
    at_risk_stock: list[AtRiskStock]
    route_plan: RoutePlan = Field(default_factory=RoutePlan)


class FarmMarginsResponse(BaseModel):
    rows: list[FarmEconomicsRow] = Field(default_factory=list)


@router.post("/economics/farm-margins", response_model=FarmMarginsResponse)
async def post_farm_margins(body: FarmMarginsRequest) -> FarmMarginsResponse:
    """Compute per-farm net margin (APMC path vs direct buyer) from a completed run."""
    if not body.at_risk_stock:
        raise HTTPException(
            status_code=422,
            detail="at_risk_stock is required — run a scenario first",
        )
    if not body.farms or not body.demand_points or not body.trucks:
        raise HTTPException(
            status_code=422,
            detail="farms, demand_points, and trucks are required",
        )

    dps = [dp.to_schema() for dp in body.demand_points]
    farm_ids = [s.farm_id for s in body.at_risk_stock]
    acceptances = await list_acceptances(farm_ids)

    rows = compute_farm_economics(
        body.farms,
        dps,
        body.trucks,
        body.at_risk_stock,
        body.route_plan,
        acceptances=acceptances,
    )
    return FarmMarginsResponse(rows=rows)
