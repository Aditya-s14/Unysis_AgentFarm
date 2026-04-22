"""Thin Redis wrapper used as the cross-cutting cache layer."""

from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as redis

from ..config.logging_config import get_logger
from ..config.settings import get_settings

logger = get_logger(__name__)


class CacheService:
    """Async Redis cache with JSON-serialised values."""

    def __init__(self, url: Optional[str] = None) -> None:
        self._url = url or get_settings().REDIS_URL
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Open the Redis connection pool."""

        if self._client is None:
            self._client = redis.from_url(self._url, decode_responses=True)

    async def disconnect(self) -> None:
        """Close the Redis connection pool."""

        if self._client is not None:
            await self._client.close()
            self._client = None

    async def _require(self) -> redis.Redis:
        if self._client is None:
            await self.connect()
        assert self._client is not None
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """Return the JSON-decoded value at ``key`` or ``None``."""

        client = await self._require()
        raw = await client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Serialise ``value`` as JSON and store at ``key``."""

        client = await self._require()
        payload = json.dumps(value, default=str)
        await client.set(key, payload, ex=ttl)

    async def ttl(self, key: str) -> int:
        """Return the remaining TTL for ``key`` in seconds (-2 if missing)."""

        client = await self._require()
        return int(await client.ttl(key))

    async def delete(self, key: str) -> None:
        """Delete a key if it exists."""

        client = await self._require()
        await client.delete(key)


_cache_singleton: Optional[CacheService] = None


def get_cache() -> CacheService:
    """Return the process-wide :class:`CacheService` singleton."""

    global _cache_singleton
    if _cache_singleton is None:
        _cache_singleton = CacheService()
    return _cache_singleton
