"""Data CRUD endpoints — farms, demand points, trucks."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, HTTPException, status

from ...schemas.demand_point_schema import DemandPointCreate, DemandPointRead
from ...schemas.farm_schema import FarmCreate, FarmRead
from ...schemas.truck_schema import TruckCreate, TruckRead

router = APIRouter(prefix="/data", tags=["data"])


# ----- Farms ----- #


@router.get("/farms", response_model=List[FarmRead])
async def list_farms() -> List[FarmRead]:
    """List farms. TODO: read from DB."""

    return []


@router.post("/farms", response_model=FarmRead, status_code=status.HTTP_201_CREATED)
async def create_farm(payload: FarmCreate) -> FarmRead:
    """Create a farm. TODO: persist to DB."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Farm creation not yet implemented (name={payload.name}).",
    )


# ----- Demand points ----- #


@router.get("/demand-points", response_model=List[DemandPointRead])
async def list_demand_points() -> List[DemandPointRead]:
    """List demand points. TODO: read from DB."""

    return []


@router.post(
    "/demand-points",
    response_model=DemandPointRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_demand_point(payload: DemandPointCreate) -> DemandPointRead:
    """Create a demand point. TODO: persist to DB."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"DemandPoint creation not yet implemented (name={payload.name}).",
    )


# ----- Trucks ----- #


@router.get("/trucks", response_model=List[TruckRead])
async def list_trucks() -> List[TruckRead]:
    """List trucks. TODO: read from DB."""

    return []


@router.post("/trucks", response_model=TruckRead, status_code=status.HTTP_201_CREATED)
async def create_truck(payload: TruckCreate) -> TruckRead:
    """Create a truck. TODO: persist to DB."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Truck creation not yet implemented (name={payload.name}).",
    )


# Placeholder for deletions to round out CRUD surface.
@router.delete("/farms/{farm_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def delete_farm(farm_id: uuid.UUID) -> None:
    """Delete a farm by id. TODO."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Farm deletion not yet implemented (farm_id={farm_id}).",
    )
