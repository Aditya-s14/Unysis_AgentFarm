"""PlanOutcome ORM model — real-world results of an executed plan."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .plan import Plan


class PlanOutcome(Base):
    """Actual outcomes used for cross-run learning (Tier-2 memory)."""

    __tablename__ = "plan_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    plan_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    farm_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    demand_point_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    predicted_waste_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_waste_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    predicted_delivery_minutes: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    actual_delivery_minutes: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    demand_predicted_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    demand_actual_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plan: Mapped["Plan"] = relationship(back_populates="outcomes")

    __table_args__ = (
        Index("ix_outcomes_run_farm", "run_id", "farm_id"),
    )
