"""
Smoke tests for weather_api, maps_api, vrp_solver (run from repo: PYTHONPATH=backend).

  cd backend && set PYTHONPATH=. && python scripts/test_core_tools.py
"""

from __future__ import annotations

import asyncio
import csv
import os
import sys
import time
from datetime import date
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from config import get_settings  # noqa: E402
from models.schemas import (  # noqa: E402
    AtRiskStock,
    DemandPoint,
    Farm,
    Truck,
)
from tools.maps_api import get_distance_matrix  # noqa: E402
from tools.vrp_solver import solve_vrp  # noqa: E402
from tools.weather_api import fetch_weather  # noqa: E402


def _resolve_data_dir() -> Path:
    p = _root.parent / "data"
    if (p / "sample_farms.csv").is_file():
        return p
    return _root / "data"


def load_farms(limit: int | None = None) -> list[Farm]:
    path = _resolve_data_dir() / "sample_farms.csv"
    out: list[Farm] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
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
                ),
            )
            if limit is not None and len(out) >= limit:
                break
    return out


async def run_weather(farm_count: int = 20) -> None:
    farms = load_farms(limit=farm_count)
    t0 = time.perf_counter()
    events = await fetch_weather(farms)
    dt = time.perf_counter() - t0
    assert len(events) == len(farms), (len(events), len(farms))
    print(f"[weather] {len(events)} WeatherEvents in {dt:.2f}s (fallback or live)")


async def run_maps() -> None:
    pts = [
        (12.97, 77.59),
        (13.08, 77.54),
        (15.31, 75.07),
        (19.99, 73.78),
        (18.52, 73.85),
    ]
    t0 = time.perf_counter()
    mat = await get_distance_matrix(pts, pts)
    dt = time.perf_counter() - t0
    n = len(pts)
    assert len(mat) == n and all(len(r) == n for r in mat)
    assert all(isinstance(mat[i][j], float) for i in range(n) for j in range(n))
    print(f"[maps] {n}x{n} matrix ok in {dt:.2f}s (diagonal ~0)")


async def run_vrp() -> None:
    farms = load_farms(limit=5)
    dps = [
        DemandPoint(
            id="dp-1",
            name="Mandi A",
            lat=13.0,
            lng=77.5,
            type="apmc",
            base_demand_per_day=500.0,
        ),
        DemandPoint(
            id="dp-2",
            name="Mandi B",
            lat=14.0,
            lng=76.0,
            type="apmc",
            base_demand_per_day=400.0,
        ),
        DemandPoint(
            id="dp-3",
            name="Retail C",
            lat=12.5,
            lng=77.0,
            type="retail",
            base_demand_per_day=100.0,
        ),
    ]
    from datetime import time as dt_time

    trucks = [
        Truck(
            id="tr-1",
            capacity_kg=3000.0,
            cost_per_km=22.0,
            availability_start=dt_time(5, 0),
            availability_end=dt_time(20, 0),
        ),
        Truck(
            id="tr-2",
            capacity_kg=3000.0,
            cost_per_km=22.0,
            availability_start=dt_time(5, 0),
            availability_end=dt_time(20, 0),
        ),
        Truck(
            id="tr-3",
            capacity_kg=5000.0,
            cost_per_km=20.0,
            availability_start=dt_time(4, 0),
            availability_end=dt_time(22, 0),
        ),
    ]
    # depot = mean of farm coords (index 0)
    dep_lat = sum(f.lat for f in farms) / len(farms)
    dep_lng = sum(f.lng for f in farms) / len(farms)
    coords = [(dep_lat, dep_lng)] + [(f.lat, f.lng) for f in farms] + [
        (d.lat, d.lng) for d in dps
    ]

    matrix = await get_distance_matrix(coords, coords)
    at_risk = [
        AtRiskStock(
            farm_id=farms[0].id,
            crop_type=farms[0].crop_type,
            kg_at_risk=800.0,
        ),
    ]
    os.environ.setdefault("VRP_TIME_LIMIT", "5")
    get_settings.cache_clear()

    t0 = time.perf_counter()
    plan = solve_vrp(
        farms,
        dps,
        trucks,
        at_risk,
        matrix,
        relaxation_factor=1.0,
    )
    dt = time.perf_counter() - t0
    assert plan.routes, "RoutePlan should contain routes"
    assert dt < 30.0, f"VRP took {dt:.1f}s (expected <30s with VRP_TIME_LIMIT test override)"
    print(
        f"[vrp] RoutePlan with {len(plan.routes)} routes, "
        f"objective={plan.objective_value}, notes={plan.notes!r} in {dt:.2f}s",
    )


async def main() -> None:
    await run_weather(20)
    await run_maps()
    await run_vrp()


if __name__ == "__main__":
    asyncio.run(main())
