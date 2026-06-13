"""Tests for multi-season Tier-2 analytics."""

from __future__ import annotations

import csv
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from models.db_models import PlanOutcomeRow
from tools.analytics.season_metrics import (
    LEARNING_NOTES,
    SEASON_ORDER,
    _accuracy_pct,
    _waste_reduction_pct,
    build_season_trends,
)

_CSV = Path(__file__).resolve().parents[2] / "data" / "sample_outcomes.csv"


def _outcome_key(row: dict) -> tuple:
    return (
        row["mandi_id"].strip(),
        row["crop_type"].strip().lower(),
        row["weekday"].strip().lower(),
        (row.get("road_segment") or "").strip(),
    )


def _load_csv_rows() -> list[PlanOutcomeRow]:
    rows: list[PlanOutcomeRow] = []
    with _CSV.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                PlanOutcomeRow(
                    id=uuid.uuid4(),
                    plan_id=uuid.uuid4(),
                    waste_kg_predicted=float(row["waste_kg_predicted"]),
                    waste_kg_actual=float(row["waste_kg_actual"]),
                    delivery_time_predicted_hours=float(row["delivery_time_predicted_h"]),
                    delivery_time_actual_hours=float(row["delivery_time_actual_h"]),
                    demand_predicted=float(row["demand_predicted"]),
                    demand_actual=float(row["demand_actual"]),
                    season=row["season"].strip(),
                    demand_point_id=row["mandi_id"].strip(),
                    crop_type=row["crop_type"].strip(),
                    day_of_week=row["weekday"].strip(),
                    road_segment=(row.get("road_segment") or "").strip() or None,
                    outcome_index=int(row["outcome_index"]),
                )
            )
    return rows


def test_metric_formulas():
    assert _waste_reduction_pct(100, 90) == pytest.approx(10.0)
    assert _accuracy_pct(100, 90) == pytest.approx(90.0)
    assert _accuracy_pct(100, 110) == pytest.approx(90.0)


def test_seed_bias_correction_keys_consistent_across_seasons():
    by_season_index: dict[str, dict[int, tuple]] = {}
    with _CSV.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            season = row["season"].strip()
            idx = int(row["outcome_index"])
            by_season_index.setdefault(season, {})[idx] = _outcome_key(row)
    assert set(by_season_index) == {"Kharif 2024", "Rabi 2025", "Summer 2026"}
    for season in by_season_index:
        assert len(by_season_index[season]) == 40
    kharif = by_season_index["Kharif 2024"]
    for idx in range(1, 41):
        assert by_season_index["Rabi 2025"][idx] == kharif[idx]
        assert by_season_index["Summer 2026"][idx] == kharif[idx]


def test_season_trends_monotonic_improvement():
    trends = build_season_trends(_load_csv_rows())
    assert len(trends) == 3
    assert [t.season for t in trends] == ["Kharif 2024", "Rabi 2025", "Summer 2026"]
    k, r, s = trends[0], trends[1], trends[2]
    assert k.waste_reduction_pct < r.waste_reduction_pct < s.waste_reduction_pct
    assert k.forecast_accuracy_pct < r.forecast_accuracy_pct < s.forecast_accuracy_pct
    assert k.delivery_accuracy_pct < r.delivery_accuracy_pct < s.delivery_accuracy_pct
    assert k.outcome_count == r.outcome_count == s.outcome_count == 40


def test_learning_note_progression():
    trends = build_season_trends(_load_csv_rows())
    assert trends[0].learning_note == LEARNING_NOTES[SEASON_ORDER["Kharif 2024"]]
    assert trends[1].learning_note == LEARNING_NOTES[SEASON_ORDER["Rabi 2025"]]
    assert trends[2].learning_note == "Full bias correction active"


def test_demand_history_key_has_three_seasons():
    rows = _load_csv_rows()
    matches = [
        r
        for r in rows
        if r.demand_point_id == "dp-apmc-01"
        and (r.crop_type or "").lower() == "tomato"
        and (r.day_of_week or "").lower() == "tuesday"
    ]
    seasons = {r.season for r in matches}
    assert seasons == {"Kharif 2024", "Rabi 2025", "Summer 2026"}


def test_route_history_nh48_three_seasons():
    rows = _load_csv_rows()
    nh48 = [r for r in rows if r.road_segment == "NH-48"]
    seasons = {r.season for r in nh48}
    assert seasons == {"Kharif 2024", "Rabi 2025", "Summer 2026"}
    assert len(nh48) == 30  # 10 rows per season


def test_season_trends_api(client):
    trends = build_season_trends(_load_csv_rows())
    with patch(
        "routes.analytics.get_season_trends",
        new=AsyncMock(return_value=(trends, 120)),
    ):
        resp = client.get("/api/analytics/season-trends")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier2_outcome_total"] == 120
    seasons = data["seasons"]
    assert len(seasons) == 3
    assert seasons[0]["season"] == "Kharif 2024"
    assert seasons[2]["learning_note"] == "Full bias correction active"


def test_season_trends_csv_export(client):
    trends = build_season_trends(_load_csv_rows())
    with patch(
        "routes.analytics.get_season_trends",
        new=AsyncMock(return_value=(trends, 120)),
    ):
        resp = client.get("/api/analytics/season-trends/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    lines = resp.text.strip().splitlines()
    assert lines[0].startswith("season,")
    assert len(lines) >= 4
