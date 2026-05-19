"""Compare KPIs and weather across scenario types (smoke test)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from graph import PipelineRequest, run_scenario  # noqa: E402
from scripts.test_pipeline import (  # noqa: E402
    _load_demand_points,
    _load_farms,
    _load_trucks,
)
from tools.db import dispose_db, init_db  # noqa: E402


async def _run_one(scenario_type: str, farms, dps, trucks):
    req = PipelineRequest(
        farms=farms,
        demand_points=dps,
        trucks=trucks,
        scenario_type=scenario_type,
    )
    result = await run_scenario(req)
    kpis = result.kpis or {}
    traces = result.agent_traces or []
    weather_note = next(
        (t["notes"] for t in traces if t.get("agent_name") == "weather_agent"),
        "",
    )
    return {
        "scenario": scenario_type,
        "waste_reduction_pct": kpis.get("waste_reduction_pct"),
        "naive_waste_kg": kpis.get("naive_waste_kg"),
        "optimized_waste_kg": kpis.get("optimized_waste_kg"),
        "at_risk_count": kpis.get("at_risk_count"),
        "route_count": kpis.get("route_count"),
        "weather_note": weather_note[:120],
    }


async def main() -> None:
    await init_db()
    farm_ids = [f"farm-{i:03d}" for i in range(1, 21)]
    dp_ids = [
        "dp-apmc-01", "dp-apmc-02", "dp-apmc-03", "dp-apmc-04", "dp-apmc-05",
        "dp-apmc-06", "dp-priv-01", "dp-priv-02", "dp-priv-03", "dp-ret-01",
    ]
    truck_ids = [f"tr-{i:03d}" for i in range(1, 11)]
    farms = await _load_farms(farm_ids)
    dps = await _load_demand_points(dp_ids)
    trucks = await _load_trucks(truck_ids)
    scenarios = ["normal_day", "heat_wave", "monsoon_disruption"]
    results = []
    for st in scenarios:
        print(f"Running {st}...")
        results.append(await _run_one(st, farms, dps, trucks))
    await dispose_db()

    print("\n=== Scenario comparison ===")
    for r in results:
        print(
            f"{r['scenario']:22}  reduction={r['waste_reduction_pct']}%  "
            f"naive={r['naive_waste_kg']}kg  opt={r['optimized_waste_kg']}kg  "
            f"at_risk={r['at_risk_count']}  routes={r['route_count']}"
        )

    reductions = [r["waste_reduction_pct"] for r in results]
    if len(set(reductions)) < 2:
        print("\nWARN: waste_reduction_pct not distinct across scenarios")
        sys.exit(1)
    print("\nPASS: scenarios produce distinct KPIs")


if __name__ == "__main__":
    asyncio.run(main())
