"""Pydantic schemas for DemandPoint entities."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.demand_point import DemandPointType


class DemandPointBase(BaseModel):
    """Shared DemandPoint attributes."""

    name: str = Field(..., max_length=255)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    type: DemandPointType = DemandPointType.APMC
    base_demand_per_day_kg: float = Field(0.0, ge=0.0)


class DemandPointCreate(DemandPointBase):
    """Payload for creating a demand point."""


class DemandPointUpdate(BaseModel):
    """Partial update payload for a demand point."""

    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    type: Optional[DemandPointType] = None
    base_demand_per_day_kg: Optional[float] = None


class DemandPointRead(DemandPointBase):
    """DemandPoint returned from the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
