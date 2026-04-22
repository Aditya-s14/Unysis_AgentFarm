"""Weather-related tool functions used by the Weather Agent."""

from __future__ import annotations

from typing import Any, Dict

from ..config.logging_config import get_logger
from ..models.weather_event import WeatherRiskLevel
from ..utils.constants import RISK_THRESHOLDS

logger = get_logger(__name__)


def classify_risk(rain_mm: float, temperature_c: float) -> WeatherRiskLevel:
    """Classify weather risk based on rainfall and temperature thresholds."""

    if rain_mm >= RISK_THRESHOLDS["severe_rain_mm"]:
        return WeatherRiskLevel.SEVERE
    if rain_mm >= RISK_THRESHOLDS["warning_rain_mm"]:
        return WeatherRiskLevel.WARNING
    if temperature_c >= RISK_THRESHOLDS["heatwave_temp_c"]:
        return WeatherRiskLevel.WARNING
    return WeatherRiskLevel.NORMAL


def synthetic_forecast(latitude: float, longitude: float) -> Dict[str, Any]:
    """Return a deterministic synthetic forecast when the API is unavailable.

    TODO: replace with real OpenWeatherMap call inside
    :mod:`src.services.weather_service`.
    """

    return {
        "rain_mm": 5.0,
        "temperature_c": 30.0,
        "humidity_pct": 60.0,
        "source": "synthetic",
        "latitude": latitude,
        "longitude": longitude,
    }
