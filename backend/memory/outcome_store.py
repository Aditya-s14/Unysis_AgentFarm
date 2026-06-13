"""Tier 2 — cross-run learning from persisted plan outcomes (Postgres)."""

from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import func, select

from models.db_models import PlanOutcomeRow, PlanTable
from models.schemas import PlanOutcome
from tools.db import DEFAULT_OUTCOME_SEASON, get_session_maker


def _row_to_plan_outcome(row: PlanOutcomeRow) -> PlanOutcome:
    return PlanOutcome(
        id=row.id,
        plan_id=row.plan_id,
        waste_kg_predicted=row.waste_kg_predicted,
        waste_kg_actual=row.waste_kg_actual,
        delivery_time_predicted_hours=row.delivery_time_predicted_hours,
        delivery_time_actual_hours=row.delivery_time_actual_hours,
        demand_predicted=row.demand_predicted,
        demand_actual=row.demand_actual,
        notes=row.notes,
        demand_point_id=row.demand_point_id,
        crop_type=row.crop_type,
        day_of_week=row.day_of_week,
        road_segment=row.road_segment,
        season=row.season,
    )


async def get_demand_history(
    demand_point_id: str,
    crop_type: str,
    day_of_week: str,
) -> list[PlanOutcome]:
    """Historical outcomes for a mandi + crop + weekday (bias correction for Demand agent)."""
    cid = demand_point_id.strip()
    crop = crop_type.strip().lower()
    dow = day_of_week.strip().lower()
    async with get_session_maker()() as session:
        r = await session.execute(
            select(PlanOutcomeRow)
            .where(
                PlanOutcomeRow.demand_point_id == cid,
                func.lower(PlanOutcomeRow.crop_type) == crop,
                func.lower(PlanOutcomeRow.day_of_week) == dow,
            )
            .order_by(PlanOutcomeRow.outcome_index, PlanOutcomeRow.id),
        )
        rows = list(r.scalars().all())
    return [_row_to_plan_outcome(x) for x in rows]


async def get_route_history(road_segment: str) -> list[PlanOutcome]:
    """Historical outcomes touching a road segment (travel-time priors for Logistics)."""
    seg = road_segment.strip()
    async with get_session_maker()() as session:
        r = await session.execute(
            select(PlanOutcomeRow)
            .where(PlanOutcomeRow.road_segment == seg)
            .order_by(PlanOutcomeRow.outcome_index, PlanOutcomeRow.id),
        )
        rows = list(r.scalars().all())
    return [_row_to_plan_outcome(x) for x in rows]


async def log_outcome(outcome: PlanOutcome) -> None:
    """Persist a new outcome row; creates a stub plan row if ``plan_id`` is missing in DB."""
    plan_uuid = outcome.plan_id
    if isinstance(plan_uuid, str):
        plan_uuid = uuid.UUID(plan_uuid)
    plan_uuid = cast(uuid.UUID, plan_uuid)

    async with get_session_maker()() as session:
        plan = await session.get(PlanTable, plan_uuid)
        if plan is None:
            plan = PlanTable(
                id=plan_uuid,
                route_plan_json={"routes": []},
                validation_json=None,
                external_ref=None,
                run_id=None,
            )
            session.add(plan)
            await session.flush()

        row = PlanOutcomeRow(
            plan_id=plan_uuid,
            waste_kg_predicted=outcome.waste_kg_predicted,
            waste_kg_actual=outcome.waste_kg_actual,
            delivery_time_predicted_hours=outcome.delivery_time_predicted_hours,
            delivery_time_actual_hours=outcome.delivery_time_actual_hours,
            demand_predicted=outcome.demand_predicted,
            demand_actual=outcome.demand_actual,
            notes=outcome.notes,
            outcome_index=None,
            demand_point_id=outcome.demand_point_id,
            crop_type=outcome.crop_type,
            day_of_week=outcome.day_of_week,
            road_segment=outcome.road_segment,
            season=outcome.season or DEFAULT_OUTCOME_SEASON,
        )
        session.add(row)
        await session.commit()
