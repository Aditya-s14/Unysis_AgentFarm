"""Truck ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Truck(Base):
    """Fleet vehicle usable for pick-ups / drop-offs."""

    __tablename__ = "trucks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    cost_per_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    availability_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    availability_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    depot_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    depot_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
