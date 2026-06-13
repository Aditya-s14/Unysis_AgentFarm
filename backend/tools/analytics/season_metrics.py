"""Aggregate Tier-2 plan outcomes by harvest season for analytics dashboards."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import func, select

from models.db_models import PlanOutcomeRow
from tools.db import get_session_maker

SEASON_ORDER: dict[str, int] = {
    "Kharif 2024": 1,
    "Rabi 2025": 2,
    "Summer 2026": 3,
}

LEARNING_NOTES: dict[int, str] = {
    1: "Baseline — no Tier-2 correction",
    2: "Tier-2 demand bias active",
    3: "Full bias correction active",
}


@dataclass
class SeasonTrendPoint:
    season: str
    sort_order: int
    waste_reduction_pct: float
    forecast_accuracy_pct: float
    delivery_accuracy_pct: float
    outcome_count: int
    avg_delivery_slippage_pct: float
    learning_note: str

    def to_dict(self) -> dict:
        return asdict(self)


def _waste_reduction_pct(predicted: float, actual: float) -> float | None:
    if predicted <= 0:
        return None
    return (predicted - actual) / predicted * 100.0


def _accuracy_pct(predicted: float, actual: float) -> float | None:
    if predicted <= 0:
        return None
    return max(0.0, 100.0 * (1.0 - abs(actual - predicted) / predicted))


def _delivery_slippage_pct(predicted: float, actual: float) -> float | None:
    if predicted <= 0:
        return None
    return (actual - predicted) / predicted * 100.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def aggregate_outcome_rows(rows: list[PlanOutcomeRow]) -> dict[str, list[PlanOutcomeRow]]:
    by_season: dict[str, list[PlanOutcomeRow]] = {}
    for row in rows:
        label = (row.season or "Unknown").strip()
        by_season.setdefault(label, []).append(row)
    return by_season


def build_season_trends(rows: list[PlanOutcomeRow]) -> list[SeasonTrendPoint]:
    """Compute season-over-season metrics from outcome rows."""
    grouped = aggregate_outcome_rows(rows)
    points: list[SeasonTrendPoint] = []

    for season, season_rows in grouped.items():
        if season == "Unknown":
            continue
        waste_pcts: list[float] = []
        forecast_pcts: list[float] = []
        delivery_pcts: list[float] = []
        slippage_pcts: list[float] = []

        for r in season_rows:
            wp = _waste_reduction_pct(r.waste_kg_predicted, r.waste_kg_actual)
            if wp is not None:
                waste_pcts.append(wp)
            fp = _accuracy_pct(r.demand_predicted, r.demand_actual)
            if fp is not None:
                forecast_pcts.append(fp)
            dp = _accuracy_pct(r.delivery_time_predicted_hours, r.delivery_time_actual_hours)
            if dp is not None:
                delivery_pcts.append(dp)
            sp = _delivery_slippage_pct(
                r.delivery_time_predicted_hours,
                r.delivery_time_actual_hours,
            )
            if sp is not None:
                slippage_pcts.append(sp)

        sort_order = SEASON_ORDER.get(season, 99)
        points.append(
            SeasonTrendPoint(
                season=season,
                sort_order=sort_order,
                waste_reduction_pct=round(_mean(waste_pcts), 1),
                forecast_accuracy_pct=round(_mean(forecast_pcts), 1),
                delivery_accuracy_pct=round(_mean(delivery_pcts), 1),
                outcome_count=len(season_rows),
                avg_delivery_slippage_pct=round(_mean(slippage_pcts), 1),
                learning_note=LEARNING_NOTES.get(sort_order, "Tier-2 learning"),
            )
        )

    points.sort(key=lambda p: p.sort_order)
    return points


async def fetch_all_outcomes() -> list[PlanOutcomeRow]:
    async with get_session_maker()() as session:
        result = await session.execute(
            select(PlanOutcomeRow).order_by(PlanOutcomeRow.season, PlanOutcomeRow.outcome_index),
        )
        return list(result.scalars().all())


async def get_season_trends() -> tuple[list[SeasonTrendPoint], int]:
    rows = await fetch_all_outcomes()
    trends = build_season_trends(rows)
    return trends, len(rows)
