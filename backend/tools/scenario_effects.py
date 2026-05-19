"""Scenario-type normalization and shared adjustment factors.

Frontend sends: normal_day | heat_wave | monsoon_disruption
Tests may send:  normal | monsoon | default
"""

from __future__ import annotations

from models.schemas import Farm

# Canonical scenario slugs
NORMAL = "normal_day"
HEAT = "heat_wave"
MONSOON = "monsoon_disruption"

_ALIASES: dict[str, str] = {
    "normal": NORMAL,
    "normal_day": NORMAL,
    "default": NORMAL,
    "": NORMAL,
    "heat_wave": HEAT,
    "heatwave": HEAT,
    "monsoon": MONSOON,
    "monsoon_disruption": MONSOON,
    "capacity_stress": NORMAL,
}


def normalize_scenario_type(scenario_type: str | None) -> str:
    key = (scenario_type or "").strip().lower()
    return _ALIASES.get(key, key if key in (NORMAL, HEAT, MONSOON) else NORMAL)


def is_monsoon_high_risk_farm(farm: Farm) -> bool:
    """Western Ghats / coastal belt — heavier monsoon exposure in demo geography."""
    return farm.lng < 76.2 or farm.lat < 13.4


def shelf_life_factor(scenario_type: str | None) -> float:
    """Multiplier on base shelf-life days (lower = faster spoilage)."""
    st = normalize_scenario_type(scenario_type)
    if st == HEAT:
        return 0.60  # 40% reduction
    if st == MONSOON:
        return 0.80  # 20% humidity spoilage reduction
    return 1.0


def travel_time_multiplier(scenario_type: str | None) -> float:
    """Extra road delay factor for monsoon-affected legs."""
    if normalize_scenario_type(scenario_type) == MONSOON:
        return 1.3
    return 1.0


def market_absorption_factor(scenario_type: str | None) -> float:
    """Effective mandi daily demand under scenario stress (KPI demand-cap)."""
    st = normalize_scenario_type(scenario_type)
    if st == MONSOON:
        return 0.82
    if st == HEAT:
        return 0.94
    return 1.0


def naive_coordination_penalty(
    scenario_type: str | None,
    *,
    at_risk_count: int = 0,
) -> float:
    """Extra naive-routing waste from uncoordinated farm→mandi trips under stress."""
    st = normalize_scenario_type(scenario_type)
    penalty = 1.05
    if st == HEAT:
        penalty += (1.0 - shelf_life_factor(st)) * 1.15
    elif st == MONSOON:
        penalty += (travel_time_multiplier(st) - 1.0) * 0.85
    else:
        congestion = min(0.42, max(0.15, at_risk_count * 0.018))
        penalty += congestion
    return penalty


def scenario_adjustment_details(
    *,
    scenario_type: str,
    weather_fetch_meta: dict | None = None,
    retry_count: int = 0,
    demand_scale: float | None = None,
) -> dict[str, float | str | int | None]:
    """Structured scenario knobs for agent trace `details` blocks."""
    raw = (scenario_type or "").strip().lower()
    st = normalize_scenario_type(scenario_type)
    out: dict[str, float | str | int | None] = {
        "scenario_type_raw": raw or st,
        "scenario_type_normalized": st,
        "shelf_life_factor": shelf_life_factor(scenario_type),
        "travel_time_multiplier": travel_time_multiplier(scenario_type),
        "market_absorption_factor": market_absorption_factor(scenario_type),
    }
    if weather_fetch_meta:
        out["weather_source"] = weather_fetch_meta.get("weather_source")
    if retry_count:
        out["retry_count"] = retry_count
    if demand_scale is not None:
        out["demand_scale"] = demand_scale
    return out


def scenario_trace_note(scenario_type: str | None) -> str:
    raw = (scenario_type or "").strip().lower()
    if raw == "capacity_stress":
        return (
            "Scenario: capacity_stress demo — undersized truck fleet triggers validator "
            "retry loop; weather/shelf effects = normal_day."
        )
    st = normalize_scenario_type(scenario_type)
    notes = {
        NORMAL: "Scenario: normal_day — applied specific adjustments (mild weather, baseline shelf life, standard routing).",
        HEAT: "Scenario: heat_wave — applied specific adjustments (temp >38°C, shelf life −40%, morning-delivery route bias).",
        MONSOON: "Scenario: monsoon_disruption — applied specific adjustments (high-risk zone rain >25mm, shelf life −20%, travel ×1.3 on affected roads).",
    }
    return notes.get(st, f"Scenario: {st} — applied specific adjustments.")


def apply_monsoon_distance_matrix(
    matrix: list[list[float]],
    farms: list[Farm],
) -> list[list[float]]:
    """Scale legs through monsoon high-risk nodes by travel_time_multiplier (1.3)."""
    mult = travel_time_multiplier(MONSOON)
    n = len(matrix)
    nf = len(farms)
    high_risk = {i + 1 for i, f in enumerate(farms) if is_monsoon_high_risk_farm(f)}
    out = [row[:] for row in matrix]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if i in high_risk or j in high_risk:
                out[i][j] *= mult
    return out


def apply_heat_wave_morning_bias(
    matrix: list[list[float]],
    farms: list[Farm],
    at_risk_hours: dict[str, float],
) -> list[list[float]]:
    """Prefer early farm→mandi legs for urgent stock (morning delivery bias)."""
    n = len(matrix)
    nf = len(farms)
    out = [row[:] for row in matrix]
    for i in range(1, nf + 1):
        farm_id = farms[i - 1].id
        hours = at_risk_hours.get(farm_id, 120.0)
        urgency = max(0.0, min(1.0, (72.0 - hours) / 72.0))
        mandi_discount = 1.0 - 0.18 * urgency
        for j in range(nf + 1, n):
            out[i][j] *= mandi_discount
        for k in range(1, nf + 1):
            if k != i:
                out[i][k] *= 1.0 + 0.12 * urgency
    return out
