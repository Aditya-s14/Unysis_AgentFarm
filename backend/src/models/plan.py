"""Plan ORM model — optimized output of a scenario run."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .scenario_run import ScenarioRun
    from .plan_outcome import PlanOutcome


class Plan(Base):
    """Persisted plan produced by the orchestrator."""

    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenario_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    assignments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expected_waste_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    kpis: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    scenario_run: Mapped["ScenarioRun"] = relationship(back_populates="plans")
    outcomes: Mapped[List["PlanOutcome"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_plans_run_date", "run_id", "plan_date"),
    )
