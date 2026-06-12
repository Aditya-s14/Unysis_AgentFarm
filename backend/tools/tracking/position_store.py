"""Redis storage for live truck positions and deviation debounce state."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis

from config import get_settings
from models.schemas import TruckPosition
from tools.tracking.deviation import DeviationState

logger = logging.getLogger(__name__)

_REDIS: redis.Redis | None = None
_POS_PREFIX = "truck_pos:"
_DEV_PREFIX = "truck_dev_state:"
_RUN_TRUCKS_PREFIX = "truck_pos_index:"


async def _redis_client() -> redis.Redis | None:
    global _REDIS
    try:
        if _REDIS is None:
            _REDIS = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
        await _REDIS.ping()
        return _REDIS
    except Exception as exc:  # noqa: BLE001
        logger.debug("tracking Redis unavailable: %s", exc)
        return None


def _ttl_seconds() -> int:
    return max(1, int(get_settings().TRACKING_POSITION_TTL_HOURS)) * 3600


def _pos_key(run_id: str, truck_id: str) -> str:
    return f"{_POS_PREFIX}{run_id}:{truck_id}"


def _dev_key(run_id: str, truck_id: str) -> str:
    return f"{_DEV_PREFIX}{run_id}:{truck_id}"


def _index_key(run_id: str) -> str:
    return f"{_RUN_TRUCKS_PREFIX}{run_id}"


async def save_position(position: TruckPosition) -> None:
    r = await _redis_client()
    if r is None:
        return
    ttl = _ttl_seconds()
    key = _pos_key(position.run_id, position.truck_id)
    try:
        await r.set(key, position.model_dump_json(), ex=ttl)
        await r.sadd(_index_key(position.run_id), position.truck_id)
        await r.expire(_index_key(position.run_id), ttl)
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_position failed run=%s truck=%s: %s", position.run_id, position.truck_id, exc)


async def get_position(run_id: str, truck_id: str) -> TruckPosition | None:
    r = await _redis_client()
    if r is None:
        return None
    try:
        raw = await r.get(_pos_key(run_id, truck_id))
        if not raw:
            return None
        return TruckPosition.model_validate_json(raw)
    except Exception as exc:  # noqa: BLE001
        logger.debug("get_position failed: %s", exc)
        return None


async def list_positions(run_id: str, truck_ids: list[str]) -> list[TruckPosition]:
    r = await _redis_client()
    if r is None:
        return []
    out: list[TruckPosition] = []
    try:
        indexed = await r.smembers(_index_key(run_id))
        ids = list({*truck_ids, *indexed})
        for tid in ids:
            pos = await get_position(run_id, tid)
            if pos is not None:
                out.append(pos)
    except Exception as exc:  # noqa: BLE001
        logger.debug("list_positions failed: %s", exc)
    return out


async def get_deviation_state(run_id: str, truck_id: str) -> DeviationState:
    r = await _redis_client()
    if r is None:
        return DeviationState()
    try:
        raw = await r.get(_dev_key(run_id, truck_id))
        if not raw:
            return DeviationState()
        data = json.loads(raw)
        return DeviationState.from_dict(data if isinstance(data, dict) else None)
    except Exception as exc:  # noqa: BLE001
        logger.debug("get_deviation_state failed: %s", exc)
        return DeviationState()


async def save_deviation_state(run_id: str, truck_id: str, state: DeviationState) -> None:
    r = await _redis_client()
    if r is None:
        return
    try:
        await r.set(
            _dev_key(run_id, truck_id),
            json.dumps(state.to_dict()),
            ex=_ttl_seconds(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_deviation_state failed: %s", exc)


# In-memory fallback when Redis is down (single-process debounce only)
_MEM_POS: dict[str, str] = {}
_MEM_DEV: dict[str, dict[str, Any]] = {}


def _mem_pos_key(run_id: str, truck_id: str) -> str:
    return f"{run_id}:{truck_id}"


async def save_position_with_fallback(position: TruckPosition) -> None:
    await save_position(position)
    _MEM_POS[_mem_pos_key(position.run_id, position.truck_id)] = position.model_dump_json()


async def get_position_with_fallback(run_id: str, truck_id: str) -> TruckPosition | None:
    pos = await get_position(run_id, truck_id)
    if pos is not None:
        return pos
    raw = _MEM_POS.get(_mem_pos_key(run_id, truck_id))
    if raw:
        return TruckPosition.model_validate_json(raw)
    return None


async def get_deviation_state_with_fallback(run_id: str, truck_id: str) -> DeviationState:
    state = await get_deviation_state(run_id, truck_id)
    if state.off_route_since or state.last_alert_at:
        return state
    mem = _MEM_DEV.get(_mem_pos_key(run_id, truck_id))
    return DeviationState.from_dict(mem)


async def save_deviation_state_with_fallback(
    run_id: str,
    truck_id: str,
    state: DeviationState,
) -> None:
    await save_deviation_state(run_id, truck_id, state)
    _MEM_DEV[_mem_pos_key(run_id, truck_id)] = state.to_dict()
