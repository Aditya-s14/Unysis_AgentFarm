"""Persist per-run OpenWeather snapshots for advisor and other consumers.

Tier-2 (Postgres): stored inside ``run_logs.detail_json.weather_snapshot``.
Tier-3 (Redis): keyed by run_id for fast lookup (7-day TTL).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis

from config import get_settings

logger = logging.getLogger(__name__)

_REDIS: redis.Redis | None = None
_RUN_WEATHER_PREFIX = "weather_run:"
_RUN_WEATHER_TTL_S = 7 * 24 * 3600


async def _redis_client() -> redis.Redis:
    global _REDIS
    if _REDIS is None:
        _REDIS = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _REDIS


def _run_key(run_id: str) -> str:
    return f"{_RUN_WEATHER_PREFIX}{run_id.strip()}"


async def save_run_weather_snapshot(run_id: str, snapshot: dict[str, Any]) -> None:
    """Cache weather snapshot in Redis (best-effort)."""
    if not run_id or not snapshot:
        return
    try:
        r = await _redis_client()
        await r.set(_run_key(run_id), json.dumps(snapshot), ex=_RUN_WEATHER_TTL_S)
    except Exception as exc:  # noqa: BLE001
        logger.warning("weather_store: Redis save failed run_id=%s: %s", run_id, exc)


async def get_run_weather_snapshot(run_id: str) -> dict[str, Any] | None:
    """Load cached weather snapshot for a run, or None."""
    if not run_id:
        return None
    try:
        r = await _redis_client()
        raw = await r.get(_run_key(run_id))
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("weather_store: Redis get failed run_id=%s: %s", run_id, exc)
        return None
