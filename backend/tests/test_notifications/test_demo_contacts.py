"""Tests for hard-coded demo contact enrichment."""

from __future__ import annotations

from datetime import date, time as dt_time

from models.schemas import Farm, Truck
from tools.notifications.demo_contacts import (
    DEMO_FARM_PHONES,
    DEMO_TRUCK_DRIVER_PHONES,
    enrich_state_contacts,
)


def test_demo_phone_registry_covers_seed_ids() -> None:
    assert DEMO_FARM_PHONES["farm-001"] == "+919900000001"
    assert DEMO_FARM_PHONES["farm-020"] == "+919900000020"
    assert DEMO_TRUCK_DRIVER_PHONES["tr-001"] == "+919910000001"
    assert DEMO_TRUCK_DRIVER_PHONES["tr-010"] == "+919910000010"


def test_enrich_fills_missing_farm_and_truck_phones() -> None:
    state = {
        "farms": [
            Farm(
                id="farm-005",
                name="Bellary",
                lat=15.1,
                lng=76.9,
                crop_type="tomato",
                acreage=10.0,
                typical_yield_kg=500.0,
                harvest_window_start=date(2026, 1, 1),
                harvest_window_end=date(2026, 12, 31),
            ),
        ],
        "trucks": [
            Truck(
                id="tr-004",
                capacity_kg=3000.0,
                cost_per_km=20.0,
                availability_start=dt_time(5, 0),
                availability_end=dt_time(20, 0),
            ),
        ],
    }
    enriched = enrich_state_contacts(state)
    farm = enriched["farms"][0]
    truck = enriched["trucks"][0]
    assert farm.phone == "+919900000005"
    assert farm.notify_opt_in is True
    assert truck.driver_phone == "+919910000004"
