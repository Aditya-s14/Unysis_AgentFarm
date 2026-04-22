"""WeatherEvent ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .farm import Farm


class WeatherRiskLevel(str, enum.Enum):
    """Weather risk classification for a farm on a given date."""

    NORMAL = "normal"
    WARNING = "warning"
    SEVERE = "severe"


class WeatherEvent(Base):
    """A weather forecast record attached to a farm."""

    __tablename__ = "weather_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    rain_mm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[WeatherRiskLevel] = mapped_column(
        Enum(WeatherRiskLevel, name="weather_risk_level"),
        nullable=False,
        default=WeatherRiskLevel.NORMAL,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    farm: Mapped["Farm"] = relationship(back_populates="weather_events")

    __table_args__ = (
        Index("ix_weather_farm_date", "farm_id", "event_date"),
    )
