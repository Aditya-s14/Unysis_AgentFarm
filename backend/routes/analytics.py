"""GET /api/analytics/season-trends — Tier-2 season-over-season metrics."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from tools.analytics.season_metrics import get_season_trends

router = APIRouter()


@router.get("/analytics/season-trends")
async def season_trends() -> dict:
    """Return aggregated waste, forecast, and delivery accuracy by harvest season."""
    seasons, total = await get_season_trends()
    return {
        "seasons": [s.to_dict() for s in seasons],
        "tier2_outcome_total": total,
    }


@router.get("/analytics/season-trends/export")
async def season_trends_export() -> PlainTextResponse:
    """CSV export of season trend metrics (AI Exporter demo)."""
    seasons, total = await get_season_trends()
    buf = io.StringIO()
    fields = [
        "season",
        "sort_order",
        "waste_reduction_pct",
        "forecast_accuracy_pct",
        "delivery_accuracy_pct",
        "outcome_count",
        "avg_delivery_slippage_pct",
        "learning_note",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for s in seasons:
        writer.writerow(s.to_dict())
    writer.writerow({"season": "TOTAL", "outcome_count": total})
    return PlainTextResponse(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=season_trends.csv"},
    )
