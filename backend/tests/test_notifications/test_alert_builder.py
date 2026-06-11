"""Unit tests for farmer alert building."""

from __future__ import annotations

from datetime import date, time as dt_time

import pytest

from models.schemas import (
    AtRiskStock,
    DemandPoint,
    Farm,
    Route,
    RoutePlan,
    RouteStop,
    Truck,
    ValidationResult,
)
from tools.notifications.alert_builder import build_farm_alerts, should_skip_farmer_notifications


def _farm(
    farm_id: str = "farm-r1",
    *,
    phone: str = "+919900000099",
    opt_in: bool = True,
    channel: str = "both",
) -> Farm:
    return Farm(
        id=farm_id,
        name="Test Farm",
        lat=13.08,
        lng=77.54,
        crop_type="tomato",
        acreage=5.0,
        typical_yield_kg=400.0,
        harvest_window_start=date(2026, 1, 1),
        harvest_window_end=date(2026, 12, 31),
        phone=phone,
        preferred_language="en",
        notify_channel=channel,  # type: ignore[arg-type]
        notify_opt_in=opt_in,
    )


def _state(**overrides):  # noqa: ANN003
    farm = _farm()
    dp = DemandPoint(
        id="dp-r1",
        name="Test Mandi",
        lat=13.02,
        lng=77.53,
        type="apmc",
        base_demand_per_day=800.0,
    )
    truck = Truck(
        id="tr-r1",
        capacity_kg=3000.0,
        cost_per_km=20.0,
        availability_start=dt_time(5, 30),
        availability_end=dt_time(20, 0),
    )
    base = {
        "run_id": "run-test",
        "farms": [farm],
        "demand_points": [dp],
        "trucks": [truck],
        "at_risk_stock": [
            AtRiskStock(
                farm_id=farm.id,
                crop_type="tomato",
                kg_at_risk=420.0,
                reason="test",
                hours_until_spoilage=8.0,
            ),
        ],
        "route_plan": RoutePlan(
            routes=[
                Route(
                    truck_id=truck.id,
                    stops=[
                        RouteStop(
                            sequence=0,
                            lat=farm.lat,
                            lng=farm.lng,
                            label=farm.id,
                        ),
                        RouteStop(
                            sequence=1,
                            lat=dp.lat,
                            lng=dp.lng,
                            demand_point_id=dp.id,
                        ),
                    ],
                    distance_km=12.0,
                ),
            ],
        ),
        "validation_result": ValidationResult(valid=True, errors=[]),
        "retry_count": 0,
    }
    base.update(overrides)
    return base


def test_builds_urgent_alert_for_routed_farm() -> None:
    alerts = build_farm_alerts(_state())
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.farm_id == "farm-r1"
    assert alert.channel in ("voice", "both")
    assert alert.priority == "urgent"
    assert alert.mandi_name == "Test Mandi"
    assert "AM" in alert.pickup_time or "PM" in alert.pickup_time


def test_skips_when_no_phone_or_opt_out() -> None:
    farm = _farm(phone=None, opt_in=False)
    state = _state(farms=[farm])
    assert build_farm_alerts(state) == []


def test_skips_when_human_review_needed() -> None:
    state = _state(
        validation_result=ValidationResult(valid=False, errors=["capacity"]),
        retry_count=2,
    )
    assert should_skip_farmer_notifications(state) is True
    assert build_farm_alerts(state) == []


def test_skips_when_spoilage_above_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOTIFY_SPOILAGE_HOURS", "24")
    monkeypatch.setenv("NOTIFY_ALL_ROUTED", "false")
    from config import get_settings

    get_settings.cache_clear()
    state = _state(
        at_risk_stock=[
            AtRiskStock(
                farm_id="farm-r1",
                crop_type="tomato",
                kg_at_risk=420.0,
                reason="test",
                hours_until_spoilage=48.0,
            ),
        ],
    )
    assert build_farm_alerts(state) == []
    get_settings.cache_clear()
