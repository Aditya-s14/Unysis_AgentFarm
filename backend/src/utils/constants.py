"""Domain constants for AgentFarm."""

from __future__ import annotations

from typing import Dict

# Shelf life in days after harvest (rough India averages, ambient storage).
CROP_SHELF_LIFE: Dict[str, int] = {
    "tomato": 3,
    "onion": 30,
    "banana": 5,
    "mango": 7,
    "potato": 60,
    "leafy_greens": 2,
}

# Demand multipliers during Indian festivals (applied to base daily demand).
FESTIVAL_MULTIPLIERS: Dict[str, float] = {
    "diwali": 1.6,
    "pongal": 1.4,
    "onam": 1.35,
    "eid": 1.3,
    "holi": 1.15,
}

# Weather risk thresholds (rainfall in mm over the forecast window).
RISK_THRESHOLDS: Dict[str, float] = {
    "severe_rain_mm": 50.0,
    "warning_rain_mm": 20.0,
    "heatwave_temp_c": 40.0,
}

# Indian crop calendar season labels.
CROP_SEASONS: Dict[str, tuple[int, int]] = {
    "kharif": (6, 10),  # June - October
    "rabi": (11, 3),  # November - March
    "zaid": (3, 6),  # March - June
}

# Unit conversions.
KG_PER_QUINTAL: float = 100.0
ACRE_PER_BIGHA: float = 0.625  # approximate; varies by state
SQ_METRE_PER_ACRE: float = 4046.86

# Routing constants.
HAVERSINE_ROAD_FACTOR: float = 1.3  # multiplier for great-circle distance -> road km
DEFAULT_TRUCK_SPEED_KMH: float = 40.0
MAX_DRIVER_HOURS_DEFAULT: float = 14.0
