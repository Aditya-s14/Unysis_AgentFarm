"""End-to-end pipeline smoke test — geographically clustered Bengaluru scenario.

Uses three tomato farms within ~80 km of each other (Nandi Valley, Tumkur,
Chikkaballapur) with two APMC demand points (Yeshwanthpur, Kolar) and a fleet
of two 3-ton trucks plus one 1-ton truck.

With this fixture the validator passes on the first attempt:
  - Total at-risk load ~1 800 kg << fleet capacity 7 000 kg  → no CAPACITY errors
  - Longest tour leg ≈ 120 km @ 50 km/h = 2.4 h             → no DRIVE_TIME errors
  - human_review: False                                       → no retry loop

Waste-reduction is 100 % because all three at-risk farms are visited (baseline
is zero routing = everything spoils).

Run from inside the container or locally with Postgres + Redis up::

    cd backend && python scripts/test_pipeline.py

Expected output::

    run_id:              <uuid>
    routes:              2-3
    naive_waste:         500 kg  (11.1 % of at-risk)
    optimized_waste:     0 kg  (0.0 % of at-risk)
    waste_reduction_pct: 100.0 %
    agent_traces:        7 agents
    human_review:        False
    Graph smoke test: PASSED
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import select  # noqa: E402

from graph import PipelineRequest, PipelineResult, run_scenario  # noqa: E402
from models.db_models import DemandPointRow, FarmRow, TruckRow  # noqa: E402
from models.schemas import DemandPoint, Farm, Truck  # noqa: E402
from tools.db import dispose_db, init_db  # noqa: E402


# ---------------------------------------------------------------------------
# DB loaders
# ---------------------------------------------------------------------------

async def _load_farms(ids: list[str]) -> list[Farm]:
    from tools.db import get_session_maker
    async with get_session_maker()() as session:
        result = await session.execute(
            select(FarmRow).where(FarmRow.id.in_(ids)),
        )
        rows = list(result.scalars().all())
    # Preserve requested order
    row_by_id = {r.id: r for r in rows}
    out: list[Farm] = []
    for fid in ids:
        if fid not in row_by_id:
            raise RuntimeError(f"Farm {fid!r} not found in DB — run seed first")
        r = row_by_id[fid]
        out.append(
            Farm(
                id=r.id,
                name=r.name,
                lat=r.lat,
                lng=r.lng,
                crop_type=r.crop_type,
                acreage=r.acreage,
                typical_yield_kg=r.typical_yield_kg,
                harvest_window_start=r.harvest_window_start,
                harvest_window_end=r.harvest_window_end,
            )
        )
    return out


async def _load_demand_points(ids: list[str]) -> list[DemandPoint]:
    from tools.db import get_session_maker
    async with get_session_maker()() as session:
        result = await session.execute(
            select(DemandPointRow).where(DemandPointRow.id.in_(ids)),
        )
        rows = list(result.scalars().all())
    row_by_id = {r.id: r for r in rows}
    out: list[DemandPoint] = []
    for did in ids:
        if did not in row_by_id:
            raise RuntimeError(f"DemandPoint {did!r} not found in DB — run seed first")
        r = row_by_id[did]
        # point_type in DB → type in schema
        out.append(
            DemandPoint(
                id=r.id,
                name=r.name,
                lat=r.lat,
                lng=r.lng,
                type=r.point_type,  # type: ignore[arg-type]
                base_demand_per_day=r.base_demand_per_day,
            )
        )
    return out


async def _load_trucks(ids: list[str]) -> list[Truck]:
    from tools.db import get_session_maker
    async with get_session_maker()() as session:
        result = await session.execute(
            select(TruckRow).where(TruckRow.id.in_(ids)),
        )
        rows = list(result.scalars().all())
    row_by_id = {r.id: r for r in rows}
    out: list[Truck] = []
    for tid in ids:
        if tid not in row_by_id:
            raise RuntimeError(f"Truck {tid!r} not found in DB — run seed first")
        r = row_by_id[tid]
        out.append(
            Truck(
                id=r.id,
                capacity_kg=r.capacity_kg,
                cost_per_km=r.cost_per_km,
                availability_start=r.availability_start,
                availability_end=r.availability_end,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Main smoke test
# ---------------------------------------------------------------------------

async def main() -> int:
    await init_db()

    # --- Load fixtures from DB ---
    # Three tomato farms within ~80 km of Bengaluru (no multi-day hauls).
    farm_ids  = ["farm-001", "farm-002", "farm-004"]
    # Two APMC mandis reachable within the same day tour.
    dp_ids    = ["dp-apmc-01", "dp-apmc-02"]
    # Two 3-ton trucks + one 1-ton; fleet capacity 7 000 kg >> at-risk ~1 800 kg.
    truck_ids = ["tr-004", "tr-005", "tr-002"]

    farms   = await _load_farms(farm_ids)
    dps     = await _load_demand_points(dp_ids)
    trucks  = await _load_trucks(truck_ids)

    print(f"Loaded: {len(farms)} farms, {len(dps)} demand-points, {len(trucks)} trucks")

    # --- Build request ---
    request = PipelineRequest(
        farms=farms,
        demand_points=dps,
        trucks=trucks,
        scenario_type="monsoon",
    )

    # --- Run pipeline ---
    t0 = time.perf_counter()
    result: PipelineResult = await run_scenario(request)
    elapsed = time.perf_counter() - t0

    # --- Print summary ---
    routes = len(result.plan.route_plan.routes) if result.plan else 0
    waste_pct = result.kpis.get("waste_reduction_pct", 0.0)
    traces = len(result.agent_traces)

    naive_waste_kg   = result.kpis.get("naive_waste_kg", 0.0)
    opt_waste_kg     = result.kpis.get("optimized_waste_kg", 0.0)
    naive_waste_pct  = result.kpis.get("naive_waste_pct", 0.0)
    opt_waste_pct    = result.kpis.get("optimized_waste_pct", 0.0)

    print(f"\nrun_id:              {result.run_id}")
    print(f"routes:              {routes}")
    print(f"naive_waste:         {naive_waste_kg:.0f} kg  ({naive_waste_pct:.1f} % of at-risk)")
    print(f"optimized_waste:     {opt_waste_kg:.0f} kg  ({opt_waste_pct:.1f} % of at-risk)")
    print(f"waste_reduction_pct: {waste_pct:.1f} %")
    print(f"agent_traces:        {traces} agents")
    print(f"human_review:        {result.human_review}")
    print(f"elapsed:             {elapsed:.1f}s")

    if result.agent_traces:
        print("\nAgent trace summary:")
        for t in result.agent_traces:
            name  = t.get("agent_name", "?")
            notes = (t.get("notes") or "")[:80]
            print(f"  [{name}] {notes}")

    # --- Assertions ---
    failures: list[str] = []

    if result.plan is None:
        failures.append("plan is None — orchestrator_exit did not set final_plan")

    if traces < 6:
        failures.append(
            f"Expected >= 6 agent traces (entry, weather, demand, inventory, "
            f"logistics, validate, exit); got {traces}"
        )

    if elapsed >= 120.0:
        failures.append(f"Pipeline took {elapsed:.1f}s — exceeded 120s budget")

    if failures:
        print("\nAssertions FAILED:")
        for f in failures:
            print(f"  FAIL: {f}")
        print("\nGraph smoke test: FAILED")
        return 1

    print("\nGraph smoke test: PASSED")
    return 0


async def _run() -> int:
    try:
        return await main()
    finally:
        await dispose_db()


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
