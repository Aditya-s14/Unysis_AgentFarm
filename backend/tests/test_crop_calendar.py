"""Tests for crop calendar peak detection and truck gap analysis."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from models.schemas import Farm, Truck
from tools.crop_calendar import analyze_truck_gap, find_peak_harvest_day
from tools.notifications.calendar_alerts import dispatch_truck_gap_alert

I2_IDS = {
    "farm-001",
    "farm-002",
    "farm-004",
    "farm-006",
    "farm-011",
    "farm-016",
    "farm-017",
}
I3_IDS = {
    "farm-003",
    "farm-005",
    "farm-007",
    "farm-008",
    "farm-009",
    "farm-010",
    "farm-012",
    "farm-013",
}

_CSV = Path(__file__).resolve().parents[2] / "data" / "sample_farms.csv"


def _load_demo_farms() -> list[Farm]:
    farms: list[Farm] = []
    with _CSV.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            farms.append(
                Farm(
                    id=row["id"],
                    name=row["name"],
                    lat=float(row["lat"]),
                    lng=float(row["lng"]),
                    crop_type=row["crop_type"],
                    acreage=float(row["acreage"]),
                    typical_yield_kg=float(row["typical_yield_kg"]),
                    harvest_window_start=date.fromisoformat(row["harvest_window_start"]),
                    harvest_window_end=date.fromisoformat(row["harvest_window_end"]),
                )
            )
    return farms


def _demo_trucks() -> list[Truck]:
    caps = [1000, 1000, 1000, 3000, 3000, 3000, 3000, 5000, 5000, 5000]
    return [
        Truck(
            id=f"tr-{i:03d}",
            capacity_kg=cap,
            cost_per_km=20.0,
            availability_start="05:00:00",
            availability_end="20:00:00",
        )
        for i, cap in enumerate(caps, start=1)
    ]


def test_i2_i3_farm_partition_disjoint():
    assert I2_IDS & I3_IDS == set()


def test_peak_detection_june_26_from_seed():
    farms = _load_demo_farms()
    demo_day = date(2026, 6, 12)
    peak_date, peak_yield = find_peak_harvest_day(farms, demo_day)
    assert peak_date == date(2026, 6, 26)
    assert peak_yield > 0


def test_truck_gap_positive_with_demo_seed():
    farms = _load_demo_farms()
    trucks = _demo_trucks()
    analysis = analyze_truck_gap(farms, trucks, date(2026, 6, 12))
    assert analysis.truck_gap > 0
    assert analysis.trucks_needed > analysis.registered_trucks
    assert set(I3_IDS).issubset(set(analysis.farms_on_peak))


def test_alert_due_at_14_days_not_at_15():
    farms = _load_demo_farms()
    trucks = _demo_trucks()
    at_14 = analyze_truck_gap(farms, trucks, date(2026, 6, 12))
    at_15 = analyze_truck_gap(farms, trucks, date(2026, 6, 11))
    assert at_14.days_until_peak == 14
    assert at_14.alert_due is True
    assert at_15.days_until_peak == 15
    assert at_15.alert_due is False


@pytest.mark.asyncio
async def test_calendar_sms_dispatch_and_dedup():
    farms = _load_demo_farms()
    trucks = _demo_trucks()
    analysis = analyze_truck_gap(farms, trucks, date(2026, 6, 12))
    assert analysis.alert_due

    redis_mock = AsyncMock()
    redis_mock.exists = AsyncMock(return_value=False)
    redis_mock.set = AsyncMock()

    with (
        patch("tools.notifications.calendar_alerts.get_settings") as mock_settings,
        patch("tools.notifications.calendar_alerts.get_provider") as mock_get_provider,
        patch("tools.notifications.calendar_alerts._log_notification", new=AsyncMock()),
        patch(
            "tools.notifications.calendar_alerts._redis_client",
            new=AsyncMock(return_value=redis_mock),
        ),
    ):
        settings = mock_settings.return_value
        settings.NOTIFY_ENABLED = True
        settings.NOTIFY_PROVIDER = "mock"
        settings.FIELD_OFFICER_PHONE = "+919900000099"
        settings.MSG91_TEMPLATE_ID = ""

        provider = AsyncMock()
        provider.name = "mock"
        provider.send_sms = AsyncMock(return_value="mock-sms-cal-1")
        mock_get_provider.return_value = provider

        first = await dispatch_truck_gap_alert(analysis, run_id="run-test")
        assert first["dispatched"] is True
        assert first["sent"] == 1
        provider.send_sms.assert_awaited_once()
        redis_mock.set.assert_awaited_once()

        redis_mock.exists = AsyncMock(return_value=True)
        second = await dispatch_truck_gap_alert(analysis, run_id="run-test")
        assert second["dispatched"] is False
        assert second["skipped"] == 1
        assert provider.send_sms.await_count == 1
