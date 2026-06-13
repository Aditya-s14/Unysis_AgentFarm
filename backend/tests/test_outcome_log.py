"""Tests for POST /api/outcome/log and plan outcome persistence."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.db_models import PlanOutcomeRow, PlanTable
from tools.db import create_plan_outcome
from tools.http_errors import friendly_outcome_error, is_database_leak_message


@pytest.mark.asyncio
async def test_create_plan_outcome_creates_stub_plan(monkeypatch):
    """Missing plan row is auto-created before outcome insert."""
    import tools.db as db_mod

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    added: list = []

    def _add(obj):
        added.append(obj)

    session.add = _add
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    async def _refresh(row):
        if not getattr(row, "id", None):
            row.id = uuid.uuid4()

    session.refresh = _refresh

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(db_mod, "get_session_maker", lambda: MagicMock(return_value=ctx))

    plan_id = uuid.uuid4()
    row = await create_plan_outcome(
        plan_id=plan_id,
        waste_kg_predicted=100.0,
        waste_kg_actual=80.0,
        delivery_time_predicted_hours=4.0,
        delivery_time_actual_hours=4.5,
        demand_predicted=2000.0,
        demand_actual=1800.0,
        notes="test stub plan",
        demand_point_id="dp-apmc-01",
        crop_type="tomato",
        day_of_week="tuesday",
    )

    assert row.plan_id == plan_id
    assert any(isinstance(obj, PlanTable) for obj in added)
    assert any(isinstance(obj, PlanOutcomeRow) for obj in added)


def test_outcome_log_api_creates_row(client, monkeypatch):
    """POST /api/outcome/log returns 201 and passes payload through."""
    captured: dict = {}

    async def _fake_create(**kwargs):
        captured.update(kwargs)

        class Row:
            id = uuid.uuid4()
            plan_id = kwargs["plan_id"]

        return Row()

    monkeypatch.setattr("routes.advisor.create_plan_outcome", _fake_create)

    plan_id = str(uuid.uuid4())
    body = {
        "plan_id": plan_id,
        "waste_kg_predicted": 50.0,
        "waste_kg_actual": 40.0,
        "delivery_time_predicted_hours": 3.5,
        "delivery_time_actual_hours": 11.28,
        "demand_predicted": 2000.0,
        "demand_actual": 450.0,
        "demand_point_id": "dp-apmc-01",
        "crop_type": "tomato",
        "day_of_week": "wednesday",
        "notes": "mandi modal test",
    }

    resp = client.post("/api/outcome/log", json=body)
    assert resp.status_code == 201
    assert resp.json()["plan_id"] == plan_id
    assert captured["delivery_time_actual_hours"] == pytest.approx(11.28)


def test_friendly_outcome_error_hides_sql():
    raw = (
        "IntegrityError: insert into plan_outcomes (...) "
        "violates foreign key constraint plan_outcomes_plan_id_fkey"
    )
    exc = friendly_outcome_error(Exception(raw))
    assert exc.status_code == 409
    assert "INSERT INTO" not in exc.detail.upper()
    assert "foreign key" not in exc.detail.lower()
    assert is_database_leak_message(raw)
