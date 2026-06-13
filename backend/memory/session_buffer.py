"""Tier 3 — Redis-backed advisor chat history (last 10 messages, 24h TTL)."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis

from config import get_settings

logger = logging.getLogger(__name__)

_REDIS: redis.Redis | None = None

TTL_SECONDS = 24 * 60 * 60
MAX_MESSAGES = 10


def session_redis_key(session_id: str) -> str:
    """Redis key for a session (namespaced per ARCHITECTURE.md)."""
    return f"agentfarm:advisor_session:{session_id.strip()}"


async def _client() -> redis.Redis | None:
    global _REDIS
    try:
        if _REDIS is None:
            _REDIS = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
        return _REDIS
    except Exception as exc:
        logger.warning("advisor session: Redis client unavailable (%s)", exc)
        return None


async def push_message(session_id: str, role: str, content: str) -> None:
    """Append a chat turn; list is trimmed to the last ``MAX_MESSAGES``; TTL refreshed."""
    c = await _client()
    if c is None:
        return
    key = session_redis_key(session_id)
    msg = json.dumps({"role": role, "content": content}, ensure_ascii=False)
    try:
        await c.rpush(key, msg)
        await c.ltrim(key, -MAX_MESSAGES, -1)
        await c.expire(key, TTL_SECONDS)
    except Exception as exc:
        logger.warning("advisor session: push failed session=%s (%s)", session_id, exc)


async def get_history(session_id: str) -> list[dict[str, Any]]:
    """Return message dicts oldest-first (same order as ``push_message``)."""
    c = await _client()
    if c is None:
        return []
    key = session_redis_key(session_id)
    try:
        raw = await c.lrange(key, 0, -1)
    except Exception as exc:
        logger.warning("advisor session: get_history failed session=%s (%s)", session_id, exc)
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        try:
            out.append(json.loads(item))
        except json.JSONDecodeError:
            continue
    return out


async def clear_session(session_id: str) -> None:
    """Delete all buffered messages for a session."""
    c = await _client()
    if c is None:
        return
    key = session_redis_key(session_id)
    try:
        await c.delete(key)
    except Exception as exc:
        logger.warning("advisor session: clear failed session=%s (%s)", session_id, exc)
