"""Smoke test: force validator retries via undersized truck fleet.

Run inside the backend container::

    docker exec agentfarm_backend python scripts/test_validator_retry_loop.py

Expects at least one validator trace with ``retry_triggered=True`` and
multiple logistics / validator passes when capacity cannot be met immediately.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from datetime import date, time as dt_time

from graph import PipelineRequest, run_scenario  # noqa: E402
from models.schemas import DemandPoint, Farm, Truck  # noqa: E402
from scripts.test_validator_smoke import load_farms  # noqa: E402


def _stress_trucks() -> list[Truck]:
    """Fleet too small for typical at-risk load — triggers capacity retries."""
    return [
        Truck(
            id="tr-stress-1",
            capacity_kg=350.0,
            cost_per_km=22.0,
            availability_start=dt_time(5, 0),
            availability_end=dt_time(20, 0),
        ),
        Truck(
            id="tr-stress-2",
            capacity_kg=350.0,
            cost_per_km=22.0,
            availability_start=dt_time(5, 0),
            availability_end=dt_time(20, 0),
        ),
    ]


async def main() -> None:
    farms = load_farms(only_ids={"farm-001", "farm-002", "farm-004"})
    dps = [
        DemandPoint(
            id="dp-1", name="KR Market", lat=12.9683, lng=77.5758,
            type="apmc", base_demand_per_day=500.0,
        ),
        DemandPoint(
            id="dp-2", name="Yeshwanthpur APMC", lat=13.0280, lng=77.5366,
            type="apmc", base_demand_per_day=400.0,
        ),
    ]
    trucks = _stress_trucks()

    result = await run_scenario(
        PipelineRequest(
            farms=farms,
            demand_points=dps,
            trucks=trucks,
            scenario_type="capacity_stress",
        ),
    )

    traces = result.agent_traces or []
    validators = [t for t in traces if t.get("agent_name") == "validator"]
    logistics = [t for t in traces if t.get("agent_name") == "logistics_agent"]
    retry_preps = [t for t in traces if t.get("agent_name") == "retry_prep"]

    print(f"run_id={result.run_id}")
    print(f"human_review={result.human_review}")
    last_vd = (validators[-1].get("details") or {}) if validators else {}
    plan_valid = last_vd.get("valid", False)
    print(f"final_validation_valid={plan_valid}")

    if plan_valid and result.human_review:
        print("FAIL: human_review=True but final validation passed")
        sys.exit(1)
    if last_vd.get("max_retries_reached") and not plan_valid and not result.human_review:
        print("FAIL: max retries exhausted with invalid plan but human_review=False")
        sys.exit(1)

    print(f"validator_runs={len(validators)} logistics_runs={len(logistics)} retry_prep={len(retry_preps)}")

    retry_triggered = [
        t for t in validators
        if (t.get("details") or {}).get("retry_triggered")
    ]
    print(f"validator retry_triggered traces: {len(retry_triggered)}")

    if retry_triggered:
        d = retry_triggered[0].get("details") or {}
        print(f"  reason_for_retry={d.get('reason_for_retry')}")
        print(f"  relaxation_factor_applied={d.get('relaxation_factor_applied')}")

    if len(logistics) < 2:
        print("WARN: expected >= 2 logistics runs (initial + retry)")
    if not retry_triggered:
        print("FAIL: no retry_triggered validator trace")
        sys.exit(1)

    retry_logistics = [t for t in logistics if (t.get("details") or {}).get("is_retry_run")]
    if not retry_logistics:
        print("FAIL: no logistics retry run with previous_validator_failure")
        sys.exit(1)

    prev = (retry_logistics[0].get("details") or {}).get("previous_validator_failure")
    print(f"  logistics references prior failure: {bool(prev)}")

    print("PASS: retry loop observable in traces")


if __name__ == "__main__":
    asyncio.run(main())
