"""Pydantic schemas for Truck entities."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TruckBase(BaseModel):
    """Shared Truck attributes."""

    name: str = Field(..., max_length=255)
    capacity_kg: float = Field(..., gt=0.0)
    cost_per_km: float = Field(0.0, ge=0.0)
    availability_start: Optional[datetime] = None
    availability_end: Optional[datetime] = None
    depot_latitude: Optional[float] = None
    depot_longitude: Optional[float] = None


class TruckCreate(TruckBase):
    """Payload for creating a truck."""


class TruckUpdate(BaseModel):
    """Partial update payload for a truck."""

    name: Optional[str] = None
    capacity_kg: Optional[float] = None
    cost_per_km: Optional[float] = None
    availability_start: Optional[datetime] = None
    availability_end: Optional[datetime] = None
    depot_latitude: Optional[float] = None
    depot_longitude: Optional[float] = None


class TruckRead(TruckBase):
    """Truck returned from the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
