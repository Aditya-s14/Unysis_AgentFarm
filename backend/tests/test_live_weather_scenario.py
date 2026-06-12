"""Unit tests for live_weather scenario type."""

from datetime import date

from models.schemas import Farm, WeatherEvent
from tools.scenario_effects import (
    LIVE,
    coerce_weather_events,
    live_stress_kind,
    live_stress_kind_from_event,
    normalize_scenario_type,
    readings_from_event,
    shelf_life_factor,
)
from tools.weather_api import _apply_scenario_readings, _classify_risk


def test_normalize_live_weather_aliases():
    assert normalize_scenario_type("live_weather") == LIVE
    assert normalize_scenario_type("real_time") == LIVE
    assert normalize_scenario_type("LIVE") == LIVE


def _farm() -> Farm:
    today = date.today()
    return Farm(
        id="f1",
        name="Test",
        lat=12.97,
        lng=77.59,
        crop_type="tomato",
        acreage=1.0,
        typical_yield_kg=100.0,
        harvest_window_start=today,
        harvest_window_end=today,
    )


def test_apply_scenario_readings_passes_through_live():
    farm = _farm()
    rain, temp = _apply_scenario_readings(farm, 12.5, 33.2, LIVE)
    assert rain == 12.5
    assert temp == 33.2


def test_classify_risk_live_warning_on_heat():
    farm = _farm()
    sev, desc = _classify_risk(farm, 5.0, 38.5, scenario_type=LIVE)
    assert sev == "warning"
    assert "live_weather" in desc


def test_shelf_life_factor_live_derives_from_event():
    event = WeatherEvent(
        id="wx-1",
        event_date=date.today(),
        region="Test",
        description="live_weather; rain=30.0mm; temp=29.0C; risk=warning",
        severity="warning",
        precipitation_mm=30.0,
    )
    assert shelf_life_factor(LIVE, event=event) == 0.80
    assert live_stress_kind(30.0, 29.0) == "monsoon_disruption"


def test_readings_from_event_accepts_dict():
    event_dict = {
        "description": "live_weather; rain=25.0mm; temp=29.0C; risk=warning",
        "precipitation_mm": 25.0,
    }
    rain, temp = readings_from_event(event_dict)
    assert rain == 25.0
    assert temp == 29.0
    assert live_stress_kind_from_event(event_dict) == "monsoon_disruption"


def test_coerce_weather_events_from_dict():
    raw = [
        {
            "id": "wx-1",
            "event_date": date.today().isoformat(),
            "region": "T",
            "description": "live_weather; rain=25.0mm; temp=29.0C; risk=warning",
            "severity": "warning",
            "precipitation_mm": 25.0,
        }
    ]
    events = coerce_weather_events(raw)
    assert len(events) == 1
    assert events[0].description.startswith("live_weather")
