"""Hard-coded demo phone numbers for farms and truck drivers (testing only)."""

from __future__ import annotations

from memory.state import AgentFarmState
from models.schemas import Farm, Truck

# farm-001 … farm-020
DEMO_FARM_PHONES: dict[str, str] = {
    f"farm-{i:03d}": f"+9199000{i:05d}" for i in range(1, 21)
}

# tr-001 … tr-010
DEMO_TRUCK_DRIVER_PHONES: dict[str, str] = {
    f"tr-{i:03d}": f"+9199100{i:05d}" for i in range(1, 11)
}


def _coerce_farm(raw: Farm | dict) -> Farm:
    if isinstance(raw, Farm):
        data = raw.model_dump()
    else:
        data = dict(raw)
    fid = str(data.get("id") or "")
    if not data.get("phone") and fid in DEMO_FARM_PHONES:
        data["phone"] = DEMO_FARM_PHONES[fid]
        data["notify_opt_in"] = True
        if data.get("notify_channel") in (None, "none", "sms"):
            data["notify_channel"] = "both"
    return Farm.model_validate(data)


def _coerce_truck(raw: Truck | dict) -> Truck:
    if isinstance(raw, Truck):
        data = raw.model_dump()
    else:
        data = dict(raw)
    tid = str(data.get("id") or "")
    if not data.get("driver_phone") and tid in DEMO_TRUCK_DRIVER_PHONES:
        data["driver_phone"] = DEMO_TRUCK_DRIVER_PHONES[tid]
    return Truck.model_validate(data)


def enrich_state_contacts(state: AgentFarmState) -> AgentFarmState:
    """Fill missing farm/truck phones from demo registry (does not mutate input)."""
    farms = [_coerce_farm(f) for f in (state.get("farms") or [])]
    trucks = [_coerce_truck(t) for t in (state.get("trucks") or [])]
    return {**state, "farms": farms, "trucks": trucks}
