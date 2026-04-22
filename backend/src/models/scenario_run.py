"""ScenarioRun ORM model — one pipeline invocation."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Enum, Index, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .plan import Plan
    from .run_log import RunLog


class ScenarioType(str, enum.Enum):
    """Supported scenario templates."""

    MONSOON = "monsoon"
    HEATWAVE = "heatwave"
    BASELINE = "baseline"
    CUSTOM = "custom"


class RunStatus(str, enum.Enum):
    """Lifecycle status of a scenario run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    HUMAN_REVIEW = "human_review"


class ScenarioRun(Base):
    """Top-level record for a single pipeline execution."""

    __tablename__ = "scenario_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scenario_type: Mapped[ScenarioType] = mapped_column(
        Enum(ScenarioType, name="scenario_type"),
        nullable=False,
        default=ScenarioType.CUSTOM,
        index=True,
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"),
        nullable=False,
        default=RunStatus.PENDING,
        index=True,
    )
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    constraints: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plans: Mapped[List["Plan"]] = relationship(
        back_populates="scenario_run", cascade="all, delete-orphan"
    )
    run_logs: Mapped[List["RunLog"]] = relationship(
        back_populates="scenario_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_scenario_runs_created", "created_at"),
    )
