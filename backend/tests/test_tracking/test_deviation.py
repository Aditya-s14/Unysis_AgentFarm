"""Unit tests for route deviation geometry."""

from __future__ import annotations

from models.schemas import RouteStop
from tools.tracking.deviation import (
    DeviationState,
    distance_to_route_km,
    evaluate_deviation,
    is_on_route,
    validate_demo_coords,
)


def _stops_line() -> list[RouteStop]:
    return [
        RouteStop(sequence=0, lat=13.0, lng=77.0, label="a"),
        RouteStop(sequence=1, lat=13.1, lng=77.1, label="b"),
        RouteStop(sequence=2, lat=13.2, lng=77.2, label="c"),
    ]


def test_distance_on_route_near_zero() -> None:
    d = distance_to_route_km(13.1, 77.1, _stops_line())
    assert d < 1.0


def test_distance_far_from_route() -> None:
    d = distance_to_route_km(14.5, 78.5, _stops_line())
    assert d > 50.0


def test_is_on_route_threshold() -> None:
    assert is_on_route(2.9, threshold_km=3.0)
    assert not is_on_route(3.1, threshold_km=3.0)


def test_validate_demo_coords() -> None:
    assert validate_demo_coords(13.08, 77.54)
    assert not validate_demo_coords(0.0, 0.0)


def test_evaluate_deviation_debounce_blocks_immediate_alert() -> None:
    from datetime import datetime, timezone

    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    result = evaluate_deviation(
        deviation_km=5.0,
        now=now,
        state=DeviationState(),
        threshold_km=3.0,
        debounce_seconds=120,
        cooldown_min=15,
    )
    assert not result.should_alert
    assert result.new_state.off_route_since is not None


def test_evaluate_deviation_fires_after_debounce() -> None:
    from datetime import datetime, timedelta, timezone

    start = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    state = DeviationState(off_route_since=start.isoformat())
    now = start + timedelta(seconds=130)
    result = evaluate_deviation(
        deviation_km=5.0,
        now=now,
        state=state,
        threshold_km=3.0,
        debounce_seconds=120,
        cooldown_min=15,
    )
    assert result.should_alert


def test_evaluate_deviation_cooldown_suppresses_repeat() -> None:
    from datetime import datetime, timedelta, timezone

    start = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    alerted = start + timedelta(seconds=130)
    state = DeviationState(
        off_route_since=start.isoformat(),
        last_alert_at=alerted.isoformat(),
    )
    now = alerted + timedelta(minutes=5)
    result = evaluate_deviation(
        deviation_km=5.0,
        now=now,
        state=state,
        threshold_km=3.0,
        debounce_seconds=120,
        cooldown_min=15,
    )
    assert not result.should_alert


def test_evaluate_deviation_resets_when_back_on_route() -> None:
    from datetime import datetime, timezone

    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    state = DeviationState(off_route_since=now.isoformat(), last_alert_at=now.isoformat())
    result = evaluate_deviation(
        deviation_km=1.0,
        now=now,
        state=state,
        threshold_km=3.0,
    )
    assert result.on_route
    assert result.new_state.off_route_since is None
