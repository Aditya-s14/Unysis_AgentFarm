"""Bad / outlier weather sensor readings."""

from __future__ import annotations

import pytest

from tools.weather_api import sanitize_sensor_readings


def test_sanitize_rejects_extreme_outliers() -> None:
    rain, temp, quality = sanitize_sensor_readings(0.0, -999.0)
    assert quality == "rejected"
    assert temp == 28.0


def test_sanitize_clamps_high_rain() -> None:
    rain, temp, quality = sanitize_sensor_readings(800.0, 30.0)
    assert quality == "clamped"
    assert rain == 500.0
    assert temp == 30.0


def test_sanitize_ok_normal_readings() -> None:
    rain, temp, quality = sanitize_sensor_readings(12.5, 32.0)
    assert quality == "ok"
    assert rain == 12.5
    assert temp == 32.0
