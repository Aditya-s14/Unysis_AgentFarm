"""Farm ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .weather_event import WeatherEvent


class Farm(Base):
    """A producer farm in the supply chain."""

    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    crop_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    acreage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    typical_yield_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    harvest_window_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    harvest_window_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    weather_events: Mapped[List["WeatherEvent"]] = relationship(
        back_populates="farm", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_farms_crop_type", "crop_type"),
    )
