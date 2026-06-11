"""SQLAlchemy 2.0 async ORM tables matching domain models."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuidpk() -> uuid.UUID:
    return uuid.uuid4()


class FarmRow(Base):
    __tablename__ = "farms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    crop_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    acreage: Mapped[float] = mapped_column(Float, nullable=False)
    typical_yield_kg: Mapped[float] = mapped_column(Float, nullable=False)
    harvest_window_start: Mapped[date] = mapped_column(Date, nullable=False)
    harvest_window_end: Mapped[date] = mapped_column(Date, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        insert_default="en",
    )
    notify_channel: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        insert_default="sms",
    )
    notify_opt_in: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        insert_default=False,
    )


class DemandPointRow(Base):
    __tablename__ = "demand_points"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    point_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    base_demand_per_day: Mapped[float] = mapped_column(Float, nullable=False)


class TruckRow(Base):
    __tablename__ = "trucks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    capacity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    cost_per_km: Mapped[float] = mapped_column(Float, nullable=False)
    availability_start: Mapped[time] = mapped_column(Time, nullable=False)
    availability_end: Mapped[time] = mapped_column(Time, nullable=False)
    driver_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)


class PlanTable(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=_uuidpk,
    )
    external_ref: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
        index=True,
    )
    run_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    route_plan_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        insert_default=lambda: {},
    )
    validation_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notifications_dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    run_logs: Mapped[list[RunLogRow]] = relationship(
        "RunLogRow",
        back_populates="plan",
        cascade="all, delete-orphan",
    )
    outcomes: Mapped[list[PlanOutcomeRow]] = relationship(
        "PlanOutcomeRow",
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class RunLogRow(Base):
    __tablename__ = "run_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=_uuidpk,
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        insert_default="info",
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    plan: Mapped[PlanTable | None] = relationship("PlanTable", back_populates="run_logs")


class PlanOutcomeRow(Base):
    __tablename__ = "plan_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=_uuidpk,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    waste_kg_predicted: Mapped[float] = mapped_column(Float, nullable=False)
    waste_kg_actual: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_time_predicted_hours: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_time_actual_hours: Mapped[float] = mapped_column(Float, nullable=False)
    demand_predicted: Mapped[float] = mapped_column(Float, nullable=False)
    demand_actual: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    demand_point_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    crop_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    day_of_week: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    road_segment: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    plan: Mapped[PlanTable] = relationship("PlanTable", back_populates="outcomes")


class NotificationLogRow(Base):
    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=_uuidpk,
    )
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    farm_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    message_body: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
