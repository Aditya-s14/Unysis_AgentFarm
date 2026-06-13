"""End-to-end API smoke test — runs against the live container on localhost:8000.

Usage (from inside the container or host with port forwarded)::

    docker exec agentfarm_backend python scripts/test_api.py

All five checks must pass:
  PASS  /health
  PASS  /api/scenario/run
  PASS  /api/run/{run_id}
  PASS  /api/run/{run_id}/traces
  PASS  /api/advisor/query
"""

from __future__ import annotations

import asyncio
import sys

import httpx

BASE = "http://localhost:8000"

PAYLOAD = {
    "scenario_type": "monsoon",
    "farms": [
        {
            "id": "farm-001",
            "name": "Nandi Valley Tomatoes",
            "lat": 13.0827,
            "lng": 77.5439,
            "crop_type": "tomato",
            "acreage": 4.2,
            "typical_yield_kg": 1200,
            "harvest_window_start": "2026-03-01",
            "harvest_window_end": "2026-06-15",
        },
        {
            "id": "farm-004",
            "name": "Chikkaballapur Cherry Tomatoes",
            "lat": 13.4322,
            "lng": 77.7275,
            "crop_type": "tomato",
            "acreage": 3.8,
            "typical_yield_kg": 1500,
            "harvest_window_start": "2026-03-10",
            "harvest_window_end": "2026-06-20",
        },
    ],
    "demand_points": [
        {
            "id": "dp-apmc-01",
            "name": "Yeshwanthpur APMC",
            "lat": 12.9683,
            "lng": 77.5758,
            "point_type": "apmc",
            "base_demand_per_day": 2000,
        },
        {
            "id": "dp-apmc-02",
            "name": "Kolar Regional APMC",
            "lat": 13.1367,
            "lng": 78.1297,
            "point_type": "apmc",
            "base_demand_per_day": 1400,
        },
    ],
    "trucks": [
        {
            "id": "tr-004",
            "capacity_kg": 3000,
            "cost_per_km": 22.4,
            "availability_start": "04:30:00",
            "availability_end": "22:00:00",
        },
        {
            "id": "tr-005",
            "capacity_kg": 3000,
            "cost_per_km": 23.1,
            "availability_start": "05:00:00",
            "availability_end": "21:30:00",
        },
    ],
}


async def main() -> None:
    failures: list[str] = []

    async with httpx.AsyncClient(timeout=180) as client:

        # 1. Health check
        try:
            r = await client.get(f"{BASE}/health")
            assert r.status_code == 200, f"status={r.status_code}"
            print("PASS  /health")
        except Exception as exc:
            failures.append(f"FAIL  /health: {exc}")
            print(failures[-1])

        # 2. Run scenario
        run_id: str = ""
        waste_pct: float = 0.0
        try:
            r = await client.post(f"{BASE}/api/scenario/run", json=PAYLOAD)
            assert r.status_code == 200, r.text[:300]
            data = r.json()
            run_id = data["run_id"]
            waste_pct = data.get("kpis", {}).get("waste_reduction_pct", 0.0)
            print(
                f"PASS  /api/scenario/run  run_id={run_id}"
                f"  waste_reduction={waste_pct:.1f}%"
            )
        except Exception as exc:
            failures.append(f"FAIL  /api/scenario/run: {exc}")
            print(failures[-1])

        if not run_id:
            print("\nCannot test run-specific endpoints without a run_id — aborting.")
            sys.exit(1)

        # 3. Get run
        try:
            r = await client.get(f"{BASE}/api/run/{run_id}")
            assert r.status_code == 200, r.text[:300]
            print(f"PASS  /api/run/{{run_id}}")
        except Exception as exc:
            failures.append(f"FAIL  /api/run/{{run_id}}: {exc}")
            print(failures[-1])

        # 4. Get traces
        try:
            r = await client.get(f"{BASE}/api/run/{run_id}/traces")
            assert r.status_code == 200, r.text[:300]
            traces = r.json()
            print(f"PASS  /api/run/{{run_id}}/traces  ({len(traces)} traces)")
        except Exception as exc:
            failures.append(f"FAIL  /api/run/{{run_id}}/traces: {exc}")
            print(failures[-1])

        # 5. Advisor query
        try:
            r = await client.post(
                f"{BASE}/api/advisor/query",
                json={
                    "run_id": run_id,
                    "session_id": "sess-test-001",
                    "question": "Which farm is highest risk today?",
                },
            )
            assert r.status_code == 200, r.text[:300]
            answer = r.json().get("answer", "")
            print(f"PASS  /api/advisor/query  answer={answer[:80]}...")
        except Exception as exc:
            failures.append(f"FAIL  /api/advisor/query: {exc}")
            print(failures[-1])

    if failures:
        print(f"\n{len(failures)} test(s) FAILED")
        sys.exit(1)

    print("\nAll API tests PASSED")


asyncio.run(main())
