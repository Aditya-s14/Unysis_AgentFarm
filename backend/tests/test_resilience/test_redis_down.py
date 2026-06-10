"""Redis unavailable — distance cache and advisor sessions degrade gracefully."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from memory.session_buffer import get_history, push_message
from tools.maps_api import get_distance_matrix, haversine_km


@pytest.mark.asyncio
async def test_distance_matrix_when_redis_get_fails() -> None:
    pts = [(12.97, 77.59), (13.08, 77.54)]
    with (
        patch("tools.maps_api.redis.from_url") as mock_redis,
        patch("tools.maps_api._ors_pair_km", new=AsyncMock(return_value=None)),
        patch("tools.maps_api._google_pair_km", new=AsyncMock(return_value=None)),
    ):
        client = AsyncMock()
        client.get.side_effect = ConnectionError("redis down")
        client.set.side_effect = ConnectionError("redis down")
        client.aclose = AsyncMock()
        mock_redis.return_value = client

        mat = await get_distance_matrix(pts, pts)

    assert len(mat) == 2
    assert abs(mat[0][1] - haversine_km(pts[0], pts[1])) < 0.01


@pytest.mark.asyncio
async def test_advisor_session_buffer_redis_down() -> None:
    with patch("memory.session_buffer._client", new=AsyncMock(return_value=None)):
        await push_message("sess-1", "user", "hello")
        history = await get_history("sess-1")
    assert history == []
