"""Farmer crop-ready toggle and truck arrival confirmation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException

from config import get_settings
from models.schemas import FarmReadyPatch, FarmReadyState

router = APIRouter()
logger = logging.getLogger(__name__)

_REDIS: redis.Redis | None = None
_FARM_READY_TTL = 86400  # 24 h


async def _redis_client() -> redis.Redis | None:
    global _REDIS  # noqa: PLW0603
    try:
        if _REDIS is None:
            _REDIS = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
        await _REDIS.ping()
        return _REDIS
    except Exception as exc:  # noqa: BLE001
        logger.debug("farmer Redis unavailable: %s", exc)
        return None


@router.get("/farmer/{farm_id}/ready")
async def get_farmer_ready(farm_id: str) -> dict:
    """Return crop-ready flag for a farm (Redis key farm_ready:{farm_id})."""
    r = await _redis_client()
    if r is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    key = f"farm_ready:{farm_id}"
    try:
        val = await r.get(key)
        ttl = await r.ttl(key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return FarmReadyState(
        farm_id=farm_id,
        ready=val == "1",
        expires_in_seconds=ttl if ttl and ttl > 0 else None,
    ).model_dump()


@router.patch("/farmer/{farm_id}/ready")
async def patch_farmer_ready(farm_id: str, body: FarmReadyPatch) -> dict:
    """Set or clear crop-ready flag with 24 h TTL."""
    r = await _redis_client()
    if r is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    key = f"farm_ready:{farm_id}"
    try:
        await r.set(key, "1" if body.ready else "0", ex=_FARM_READY_TTL)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return FarmReadyState(
        farm_id=farm_id,
        ready=body.ready,
        expires_in_seconds=_FARM_READY_TTL,
    ).model_dump()


@router.post("/run/{run_id}/farm/{farm_id}/arrival")
async def post_farm_arrival(run_id: str, farm_id: str) -> dict:
    """Farmer confirms the assigned truck has arrived at the farm for pickup."""
    r = await _redis_client()
    if r is not None:
        try:
            key = f"farm_arrival:{run_id}:{farm_id}"
            await r.set(key, datetime.now(timezone.utc).isoformat(), ex=86400)
        except Exception as exc:  # noqa: BLE001
            logger.warning("farm arrival Redis write failed: %s", exc)
    return {"run_id": run_id, "farm_id": farm_id, "status": "confirmed"}
