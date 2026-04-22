"""RunLog ORM model — per-agent traces within a scenario run."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .scenario_run import ScenarioRun


class RunLog(Base):
    """Individual agent step log captured during a run."""

    __tablename__ = "run_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenario_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_called: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metrics_before: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metrics_after: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    trace_link: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    scenario_run: Mapped["ScenarioRun"] = relationship(back_populates="run_logs")

    __table_args__ = (
        Index("ix_run_logs_run_agent", "run_id", "agent_name"),
    )
