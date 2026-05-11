"""End-to-end smoke test: load seeded farms, solve VRP, run validator.

Proves the realistic per-day yields make the validator return ``valid=True``
on a normal plan with no errors. Run from inside the backend container::

    docker exec agentfarm_backend python scripts/test_validator_smoke.py
"""

from __future__ import annotations

import asyncio
import csv
import os
import sys
from datetime import date, time as dt_time
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from config import get_settings  # noqa: E402
from models.schemas import AtRiskStock, DemandPoint, Farm, Truck  # noqa: E402
from tools.maps_api import get_distance_matrix  # noqa: E402
from tools.vrp_solver import solve_vrp  # noqa: E402
from tools.weather_api import fetch_weather  # noqa: E402
from agents.validator import run as validator  # noqa: E402
from memory.state import initial_agent_farm_state  # noqa: E402


def _resolve_data_dir() -> Path:
    p = _root.parent / "data"
    if (p / "sample_farms.csv").is_file():
        return p
    return _root / "data"


def load_farms(
    n: int = 5,
    only_ids: set[str] | None = None,
) -> list[Farm]:
    """Load farms from the seed CSV.

    If ``only_ids`` is given, ignore ``n`` and return just those farms in CSV order.
    """
    path = _resolve_data_dir() / "sample_farms.csv"
    out: list[Farm] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if only_ids is not None and row["id"].strip() not in only_ids:
                continue
            out.append(
                Farm(
                    id=row["id"].strip(),
                    name=row["name"].strip(),
                    lat=float(row["lat"]),
                    lng=float(row["lng"]),
                    crop_type=row["crop_type"].strip(),
                    acreage=float(row["acreage"]),
                    typical_yield_kg=float(row["typical_yield_kg"]),
                    harvest_window_start=date.fromisoformat(
                        row["harvest_window_start"].strip(),
                    ),
                    harvest_window_end=date.fromisoformat(
                        row["harvest_window_end"].strip(),
                    ),
                )
            )
            if only_ids is None and len(out) >= n:
                break
    return out


async def main() -> int:
    # Use farms clustered around Bengaluru so a single-day tour is realistic.
    farms = load_farms(only_ids={"farm-001", "farm-002", "farm-004"})
    print("farms:")
    for f in farms:
        print(f"  {f.id:<10} {f.crop_type:<8} yield={f.typical_yield_kg:.0f} kg")

    dps = [
        DemandPoint(id="dp-1", name="KR Market", lat=12.9683, lng=77.5758,
                    type="apmc", base_demand_per_day=500.0),
        DemandPoint(id="dp-2", name="Yeshwanthpur APMC", lat=13.0280, lng=77.5366,
                    type="apmc", base_demand_per_day=400.0),
        DemandPoint(id="dp-3", name="Kolar Retail", lat=13.1372, lng=78.1291,
                    type="retail", base_demand_per_day=100.0),
    ]
    trucks = [
        Truck(id="tr-1", capacity_kg=3000.0, cost_per_km=22.0,
              availability_start=dt_time(5, 0), availability_end=dt_time(20, 0)),
        Truck(id="tr-2", capacity_kg=3000.0, cost_per_km=22.0,
              availability_start=dt_time(5, 0), availability_end=dt_time(20, 0)),
        Truck(id="tr-3", capacity_kg=5000.0, cost_per_km=20.0,
              availability_start=dt_time(4, 0), availability_end=dt_time(22, 0)),
    ]

    at_risk = [
        AtRiskStock(
            farm_id=f.id,
            crop_type=f.crop_type,
            kg_at_risk=0.4 * f.typical_yield_kg,
            hours_until_spoilage=18.0,
        )
        for f in farms
    ]
    total_load = sum(s.kg_at_risk for s in at_risk)
    fleet_cap = sum(t.capacity_kg for t in trucks)
    print(
        f"at_risk total = {total_load:.0f} kg vs fleet capacity = "
        f"{fleet_cap:.0f} kg",
    )

    dep_lat = sum(f.lat for f in farms) / len(farms)
    dep_lng = sum(f.lng for f in farms) / len(farms)
    coords = (
        [(dep_lat, dep_lng)]
        + [(f.lat, f.lng) for f in farms]
        + [(d.lat, d.lng) for d in dps]
    )
    matrix = await get_distance_matrix(coords, coords)

    os.environ.setdefault("VRP_TIME_LIMIT", "5")
    get_settings.cache_clear()

    plan = solve_vrp(farms, dps, trucks, at_risk, matrix, relaxation_factor=1.0)
    print(
        f"vrp: {len(plan.routes)} routes, "
        f"objective={plan.objective_value}, notes={plan.notes!r}",
    )

    events = await fetch_weather(farms)
    risk_summary = {f.id: e.severity for f, e in zip(farms, events)}

    state = initial_agent_farm_state(run_id="validator-smoke", scenario_type="normal")
    state["farms"] = farms
    state["demand_points"] = dps
    state["trucks"] = trucks
    state["at_risk_stock"] = at_risk
    state["route_plan"] = plan
    state["weather_events"] = events
    state["weather_risk_summary"] = risk_summary

    state = await validator(state)
    vr = state["validation_result"]
    print(f"validation_result.valid    = {vr.valid}")
    print(f"validation_result.errors   = {vr.errors}")
    print(f"validation_result.warnings = {vr.warnings}")
    print(f"retry_count                = {state.get('retry_count', 0)}")

    if not vr.valid:
        print("FAIL: validator rejected the plan")
        return 1
    print("PASS: validator returned valid=True with zero errors")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
