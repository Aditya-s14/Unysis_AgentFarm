"""Pydantic schemas for Farm entities."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FarmBase(BaseModel):
    """Shared Farm attributes."""

    name: str = Field(..., max_length=255)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    crop_type: str = Field(..., max_length=100)
    acreage: float = Field(0.0, ge=0.0)
    typical_yield_kg: float = Field(0.0, ge=0.0)
    harvest_window_start: Optional[datetime] = None
    harvest_window_end: Optional[datetime] = None


class FarmCreate(FarmBase):
    """Payload for creating a farm."""


class FarmUpdate(BaseModel):
    """Partial update payload for a farm."""

    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    crop_type: Optional[str] = None
    acreage: Optional[float] = None
    typical_yield_kg: Optional[float] = None
    harvest_window_start: Optional[datetime] = None
    harvest_window_end: Optional[datetime] = None


class FarmRead(FarmBase):
    """Farm as returned from the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
