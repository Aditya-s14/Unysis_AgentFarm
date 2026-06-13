"""Async SQLAlchemy engine, session factory, schema init, CSV seed, CRUD helpers."""

from __future__ import annotations

import csv
import uuid
from collections.abc import AsyncIterator
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import get_settings

DEFAULT_OUTCOME_SEASON = "Summer 2026"
from models.db_models import (
    Base,
    DemandPointRow,
    FarmRow,
    NotificationLogRow,
    PlanOutcomeRow,
    PlanTable,
    RunLogRow,
    TruckRow,
)

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def resolve_data_dir() -> Path:
    """Seed CSV directory: ``DATA_SEED_DIR`` env, else ``backend/data`` or repo ``data/``.

    With Docker ``./backend:/app``, the repo root is *not* under ``/app``, so we try
    ``<backend>/data`` first (mount ``./data:/app/data``), then ``<repo>/data`` for local dev.
    """
    s = get_settings()
    if getattr(s, "DATA_SEED_DIR", None) and str(s.DATA_SEED_DIR).strip():
        return Path(s.DATA_SEED_DIR).expanduser().resolve()

    here = Path(__file__).resolve()
    backend_root = here.parent.parent  # .../backend (``/app`` in Docker)
    repo_root = backend_root.parent
    candidates = [backend_root / "data", repo_root / "data"]
    for c in candidates:
        if (c / "sample_farms.csv").is_file():
            return c.resolve()
    for c in candidates:
        if c.is_dir():
            return c
    return repo_root / "data"


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database not initialized; call init_db() first.")
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    if _session_maker is None:
        raise RuntimeError("Database not initialized; call init_db() first.")
    return _session_maker


async def _backfill_outcome_dims_from_csv(conn: Any) -> None:
    """Populate Tier-2 filter columns from ``sample_outcomes.csv`` (existing DBs pre-migration)."""
    root = resolve_data_dir()
    path = root / "sample_outcomes.csv"
    if not path.is_file():
        return
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ext = row["plan_external_key"].strip()
            mandi = (row.get("mandi_id") or "").strip() or None
            dow = (row.get("weekday") or "").strip() or None
            crop = (row.get("crop_type") or "").strip() or None
            road = (row.get("road_segment") or "").strip() or None
            season = (row.get("season") or "").strip() or None
            await conn.execute(
                text(
                    """
                    UPDATE plan_outcomes AS o
                    SET demand_point_id = :dp,
                        crop_type = :crop,
                        day_of_week = :dow,
                        road_segment = :road,
                        season = :season
                    WHERE o.plan_id = (
                        SELECT p.id FROM plans AS p WHERE p.external_ref = :ext LIMIT 1
                    )
                    """,
                ),
                {"dp": mandi, "crop": crop, "dow": dow, "road": road, "season": season, "ext": ext},
            )


async def _ensure_plan_outcome_memory_columns(conn: Any) -> None:
    """Align existing DBs (``create_all`` does not add new columns). PostgreSQL only."""
    stmts = [
        "ALTER TABLE plan_outcomes ADD COLUMN IF NOT EXISTS demand_point_id VARCHAR(64)",
        "ALTER TABLE plan_outcomes ADD COLUMN IF NOT EXISTS crop_type VARCHAR(64)",
        "ALTER TABLE plan_outcomes ADD COLUMN IF NOT EXISTS day_of_week VARCHAR(32)",
        "ALTER TABLE plan_outcomes ADD COLUMN IF NOT EXISTS road_segment VARCHAR(128)",
        "CREATE INDEX IF NOT EXISTS ix_plan_outcomes_demand_point_id ON plan_outcomes (demand_point_id)",
        "CREATE INDEX IF NOT EXISTS ix_plan_outcomes_crop_type ON plan_outcomes (crop_type)",
        "CREATE INDEX IF NOT EXISTS ix_plan_outcomes_day_of_week ON plan_outcomes (day_of_week)",
        "CREATE INDEX IF NOT EXISTS ix_plan_outcomes_road_segment ON plan_outcomes (road_segment)",
        "ALTER TABLE plan_outcomes ADD COLUMN IF NOT EXISTS season VARCHAR(32)",
        "CREATE INDEX IF NOT EXISTS ix_plan_outcomes_season ON plan_outcomes (season)",
    ]
    for ddl in stmts:
        await conn.execute(text(ddl))


async def _ensure_farm_notification_columns(conn: Any) -> None:
    """Add optional farmer contact columns to existing ``farms`` tables."""
    stmts = [
        "ALTER TABLE farms ADD COLUMN IF NOT EXISTS phone VARCHAR(32)",
        "ALTER TABLE farms ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(8) DEFAULT 'en'",
        "ALTER TABLE farms ADD COLUMN IF NOT EXISTS notify_channel VARCHAR(16) DEFAULT 'sms'",
        "ALTER TABLE farms ADD COLUMN IF NOT EXISTS notify_opt_in BOOLEAN DEFAULT FALSE",
    ]
    for ddl in stmts:
        await conn.execute(text(ddl))


async def _ensure_truck_driver_phone_column(conn: Any) -> None:
    stmts = [
        "ALTER TABLE trucks ADD COLUMN IF NOT EXISTS driver_phone VARCHAR(32)",
    ]
    for ddl in stmts:
        await conn.execute(text(ddl))


async def _ensure_plan_approval_columns(conn: Any) -> None:
    stmts = [
        "ALTER TABLE plans ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ",
        "ALTER TABLE plans ADD COLUMN IF NOT EXISTS approved_by VARCHAR(64)",
        "ALTER TABLE plans ADD COLUMN IF NOT EXISTS notifications_dispatched_at TIMESTAMPTZ",
    ]
    for ddl in stmts:
        await conn.execute(text(ddl))


async def init_db() -> None:
    """Create async engine, session factory, and all tables."""
    global _engine, _session_maker
    settings = get_settings()
    _engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    _session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "postgresql" in settings.DATABASE_URL:
            await _ensure_plan_outcome_memory_columns(conn)
            await _ensure_farm_notification_columns(conn)
            await _ensure_truck_driver_phone_column(conn)
            await _ensure_plan_approval_columns(conn)


async def backfill_outcome_dims_from_csv() -> None:
    """Apply / refresh Tier-2 dimension columns from ``sample_outcomes.csv`` (run after seed)."""
    eng = get_engine()
    async with eng.begin() as conn:
        await _backfill_outcome_dims_from_csv(conn)


async def dispose_db() -> None:
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_maker = None


async def get_async_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_maker()
    async with factory() as session:
        yield session


def _parse_time(value: str) -> time:
    v = value.strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(v, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Invalid time: {value!r}")


def _parse_date(value: str) -> date:
    return date.fromisoformat(value.strip())


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None or not str(value).strip():
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y")


async def _seed_master_from_csv(session: AsyncSession, root: Path) -> None:
    farms_csv = root / "sample_farms.csv"
    demand_csv = root / "sample_demand.csv"
    trucks_csv = root / "sample_trucks.csv"

    if farms_csv.is_file():
        with farms_csv.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.add(
                    FarmRow(
                        id=row["id"].strip(),
                        name=row["name"].strip(),
                        lat=float(row["lat"]),
                        lng=float(row["lng"]),
                        crop_type=row["crop_type"].strip(),
                        acreage=float(row["acreage"]),
                        typical_yield_kg=float(row["typical_yield_kg"]),
                        harvest_window_start=_parse_date(row["harvest_window_start"]),
                        harvest_window_end=_parse_date(row["harvest_window_end"]),
                        phone=(row.get("phone") or "").strip() or None,
                        preferred_language=(row.get("preferred_language") or "en").strip(),
                        notify_channel=(row.get("notify_channel") or "sms").strip(),
                        notify_opt_in=_parse_bool(row.get("notify_opt_in")),
                    )
                )

    if demand_csv.is_file():
        with demand_csv.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.add(
                    DemandPointRow(
                        id=row["id"].strip(),
                        name=row["name"].strip(),
                        lat=float(row["lat"]),
                        lng=float(row["lng"]),
                        point_type=row["type"].strip().lower(),
                        base_demand_per_day=float(row["base_demand_per_day"]),
                    )
                )

    if trucks_csv.is_file():
        with trucks_csv.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.add(
                    TruckRow(
                        id=row["id"].strip(),
                        capacity_kg=float(row["capacity_kg"]),
                        cost_per_km=float(row["cost_per_km"]),
                        availability_start=_parse_time(row["availability_start"]),
                        availability_end=_parse_time(row["availability_end"]),
                        driver_phone=(row.get("driver_phone") or "").strip() or None,
                    )
                )


async def _seed_outcomes_from_csv(session: AsyncSession, root: Path) -> None:
    outcomes_csv = root / "sample_outcomes.csv"
    if not outcomes_csv.is_file():
        return
    with outcomes_csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ext = row["plan_external_key"].strip()
            plan = PlanTable(
                external_ref=ext,
                run_id=None,
                route_plan_json={"routes": []},
                validation_json=None,
            )
            session.add(plan)
            await session.flush()
            crop = (row.get("crop_type") or "").strip() or None
            road = (row.get("road_segment") or "").strip() or None
            mandi = (row.get("mandi_id") or "").strip() or None
            dow = (row.get("weekday") or "").strip() or None
            season = (row.get("season") or "").strip() or None
            session.add(
                PlanOutcomeRow(
                    plan_id=plan.id,
                    waste_kg_predicted=float(row["waste_kg_predicted"]),
                    waste_kg_actual=float(row["waste_kg_actual"]),
                    delivery_time_predicted_hours=float(
                        row["delivery_time_predicted_h"],
                    ),
                    delivery_time_actual_hours=float(row["delivery_time_actual_h"]),
                    demand_predicted=float(row["demand_predicted"]),
                    demand_actual=float(row["demand_actual"]),
                    notes=(row.get("notes") or "").strip() or None,
                    outcome_index=int(row["outcome_index"]),
                    demand_point_id=mandi,
                    crop_type=crop,
                    day_of_week=dow,
                    road_segment=road,
                    season=season,
                )
            )


async def seed_from_csv(session: AsyncSession) -> None:
    """Load all seed CSVs from ``resolve_data_dir()`` (master data + outcomes)."""
    root = resolve_data_dir()
    if not root.is_dir():
        return
    await _seed_master_from_csv(session, root)
    await _seed_outcomes_from_csv(session, root)


async def seed_if_empty(*, force_reseed: bool = False) -> None:
    """Seed from CSV when master or outcome tables are empty.

    Pass ``force_reseed=True`` to wipe and reload every seed-owned table
    (``farms``, ``demand_points``, ``trucks``, ``plans``, ``plan_outcomes``,
    ``run_logs``) before reseeding. Useful when CSVs change and you need the
    DB to reflect them without nuking the volume.
    """
    data_root = resolve_data_dir()
    if not data_root.is_dir():
        return

    factory = get_session_maker()
    async with factory() as session:
        if force_reseed:
            settings = get_settings()
            if "postgresql" in settings.DATABASE_URL:
                await session.execute(
                    text(
                        "TRUNCATE TABLE plan_outcomes, run_logs, plans, "
                        "farms, demand_points, trucks RESTART IDENTITY CASCADE",
                    ),
                )
            else:
                for tbl in (
                    "plan_outcomes",
                    "run_logs",
                    "plans",
                    "farms",
                    "demand_points",
                    "trucks",
                ):
                    await session.execute(text(f"DELETE FROM {tbl}"))
            await _seed_master_from_csv(session, data_root)
            await _seed_outcomes_from_csv(session, data_root)
            await session.commit()
            return

        n_farms = await session.scalar(select(func.count()).select_from(FarmRow))
        n_outcomes = await session.scalar(
            select(func.count()).select_from(PlanOutcomeRow),
        )

        if (n_farms or 0) == 0:
            await _seed_master_from_csv(session, data_root)
            await _seed_outcomes_from_csv(session, data_root)
            await session.commit()
        elif (n_outcomes or 0) == 0:
            await _seed_outcomes_from_csv(session, data_root)
            await session.commit()


# --- CRUD: Plan, RunLog, PlanOutcome ---


async def create_plan(
    *,
    route_plan_json: dict[str, Any],
    run_id: str | None = None,
    external_ref: str | None = None,
    validation_json: dict[str, Any] | None = None,
) -> PlanTable:
    async with get_session_maker()() as session:
        row = PlanTable(
            route_plan_json=route_plan_json,
            run_id=run_id,
            external_ref=external_ref,
            validation_json=validation_json,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row


async def get_plan(plan_id: uuid.UUID) -> PlanTable | None:
    async with get_session_maker()() as session:
        return await session.get(PlanTable, plan_id)


async def get_plan_by_external_ref(ref: str) -> PlanTable | None:
    async with get_session_maker()() as session:
        q = await session.execute(
            select(PlanTable).where(PlanTable.external_ref == ref),
        )
        return q.scalar_one_or_none()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


async def create_run_log(
    *,
    run_id: str,
    message: str,
    level: str = "info",
    plan_id: uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
) -> RunLogRow:
    async with get_session_maker()() as session:
        row = RunLogRow(
            run_id=run_id,
            plan_id=plan_id,
            level=level,
            message=message,
            detail_json=_jsonable(detail) if detail is not None else None,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row


async def list_run_logs_for_plan(plan_id: uuid.UUID) -> list[RunLogRow]:
    async with get_session_maker()() as session:
        r = await session.execute(
            select(RunLogRow)
            .where(RunLogRow.plan_id == plan_id)
            .order_by(RunLogRow.created_at),
        )
        return list(r.scalars().all())


async def get_plan_by_run_id(run_id: str) -> PlanTable | None:
    """Return the most-recent PlanTable row for *run_id* (string), or None."""
    async with get_session_maker()() as session:
        q = await session.execute(
            select(PlanTable)
            .where(PlanTable.run_id == run_id)
            .order_by(PlanTable.created_at.desc())
            .limit(1),
        )
        return q.scalar_one_or_none()


async def get_latest_plan() -> PlanTable | None:
    """Return the most recently created plan row, or None."""
    async with get_session_maker()() as session:
        q = await session.execute(
            select(PlanTable)
            .where(PlanTable.run_id.isnot(None))
            .order_by(PlanTable.created_at.desc())
            .limit(1),
        )
        return q.scalar_one_or_none()


async def list_run_logs_for_run(run_id: str) -> list[RunLogRow]:
    """Return all RunLogRow entries for *run_id*, oldest first."""
    async with get_session_maker()() as session:
        r = await session.execute(
            select(RunLogRow)
            .where(RunLogRow.run_id == run_id)
            .order_by(RunLogRow.created_at),
        )
        return list(r.scalars().all())


async def create_plan_outcome(
    *,
    plan_id: uuid.UUID,
    waste_kg_predicted: float,
    waste_kg_actual: float,
    delivery_time_predicted_hours: float,
    delivery_time_actual_hours: float,
    demand_predicted: float,
    demand_actual: float,
    notes: str | None = None,
    outcome_index: int | None = None,
    demand_point_id: str | None = None,
    crop_type: str | None = None,
    day_of_week: str | None = None,
    road_segment: str | None = None,
    season: str | None = None,
) -> PlanOutcomeRow:
    async with get_session_maker()() as session:
        plan = await session.get(PlanTable, plan_id)
        if plan is None:
            plan = PlanTable(
                id=plan_id,
                route_plan_json={"routes": []},
                validation_json=None,
                external_ref=None,
                run_id=None,
            )
            session.add(plan)
            await session.flush()

        row = PlanOutcomeRow(
            plan_id=plan_id,
            waste_kg_predicted=waste_kg_predicted,
            waste_kg_actual=waste_kg_actual,
            delivery_time_predicted_hours=delivery_time_predicted_hours,
            delivery_time_actual_hours=delivery_time_actual_hours,
            demand_predicted=demand_predicted,
            demand_actual=demand_actual,
            notes=notes,
            outcome_index=outcome_index,
            demand_point_id=demand_point_id,
            crop_type=crop_type,
            day_of_week=day_of_week,
            road_segment=road_segment,
            season=season or DEFAULT_OUTCOME_SEASON,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row


async def list_outcomes_for_plan(plan_id: uuid.UUID) -> list[PlanOutcomeRow]:
    async with get_session_maker()() as session:
        r = await session.execute(
            select(PlanOutcomeRow)
            .where(PlanOutcomeRow.plan_id == plan_id)
            .order_by(PlanOutcomeRow.outcome_index, PlanOutcomeRow.id),
        )
        return list(r.scalars().all())


async def get_plan_outcome(outcome_id: uuid.UUID) -> PlanOutcomeRow | None:
    async with get_session_maker()() as session:
        return await session.get(PlanOutcomeRow, outcome_id)


async def create_notification_log(
    *,
    run_id: str,
    plan_id: uuid.UUID | None,
    farm_id: str | None,
    channel: str,
    phone: str,
    message_body: str,
    priority: str,
    provider: str,
    provider_message_id: str | None = None,
    status: str,
    error: str | None = None,
) -> NotificationLogRow:
    async with get_session_maker()() as session:
        row = NotificationLogRow(
            run_id=run_id,
            plan_id=plan_id,
            farm_id=farm_id,
            channel=channel,
            phone=phone,
            message_body=message_body,
            priority=priority,
            provider=provider,
            provider_message_id=provider_message_id,
            status=status,
            error=error,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row


async def list_notifications_for_run(run_id: str) -> list[NotificationLogRow]:
    async with get_session_maker()() as session:
        r = await session.execute(
            select(NotificationLogRow)
            .where(NotificationLogRow.run_id == run_id)
            .order_by(NotificationLogRow.created_at),
        )
        return list(r.scalars().all())


async def get_plan_run_detail(run_id: str) -> dict[str, Any] | None:
    """Return ``detail_json`` from the plan_run_complete log for *run_id*."""
    rows = await list_run_logs_for_run(run_id)
    for row in reversed(rows):
        if row.message == "plan_run_complete" and row.detail_json:
            return dict(row.detail_json)
    return None


async def mark_plan_approved(
    plan_id: uuid.UUID,
    *,
    approved_by: str = "fpo",
) -> PlanTable | None:
    async with get_session_maker()() as session:
        row = await session.get(PlanTable, plan_id)
        if row is None:
            return None
        row.approved_at = datetime.now(timezone.utc)
        row.approved_by = approved_by
        await session.commit()
        await session.refresh(row)
        return row


async def mark_notifications_dispatched(plan_id: uuid.UUID) -> PlanTable | None:
    async with get_session_maker()() as session:
        row = await session.get(PlanTable, plan_id)
        if row is None:
            return None
        row.notifications_dispatched_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(row)
        return row


async def update_plan_routes(
    plan_id: uuid.UUID,
    *,
    route_plan_json: dict[str, Any],
    validation_json: dict[str, Any] | None = None,
) -> PlanTable | None:
    """Persist an updated route plan after breakdown re-planning."""
    async with get_session_maker()() as session:
        row = await session.get(PlanTable, plan_id)
        if row is None:
            return None
        row.route_plan_json = _jsonable(route_plan_json)
        if validation_json is not None:
            row.validation_json = _jsonable(validation_json)
        await session.commit()
        await session.refresh(row)
        return row
