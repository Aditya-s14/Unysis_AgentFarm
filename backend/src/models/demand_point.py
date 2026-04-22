"""DemandPoint ORM model (APMC mandi, private mandi, or retailer)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class DemandPointType(str, enum.Enum):
    """Classification for a demand endpoint."""

    APMC = "apmc"
    PRIVATE = "private"
    RETAILER = "retailer"


class DemandPoint(Base):
    """A buyer / market endpoint in the supply chain."""

    __tablename__ = "demand_points"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[DemandPointType] = mapped_column(
        Enum(DemandPointType, name="demand_point_type"),
        nullable=False,
        default=DemandPointType.APMC,
        index=True,
    )
    base_demand_per_day_kg: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
