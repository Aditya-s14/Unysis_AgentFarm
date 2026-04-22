"""Shared pytest fixtures for AgentFarm backend tests."""

from __future__ import annotations

import asyncio
import uuid
from typing import AsyncIterator, Dict, Iterator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.main import create_app
from src.models.database import Base


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Create a session-scoped event loop for async tests."""

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide an in-memory SQLite async session for isolated tests."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Return a Redis-like AsyncMock (get/set/ttl/delete)."""

    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.ttl.return_value = -2
    mock.delete.return_value = 1
    return mock


@pytest.fixture
def client() -> Iterator[TestClient]:
    """FastAPI ``TestClient`` for route-level tests."""

    app = create_app()
    with TestClient(app) as c:
        yield c


# --- Factories --- #


@pytest.fixture
def sample_farm() -> Dict[str, object]:
    """Return a minimal, valid farm payload."""

    return {
        "id": str(uuid.uuid4()),
        "name": "Test Farm",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "crop_type": "tomato",
        "acreage": 5.0,
        "typical_yield_kg": 1000.0,
    }


@pytest.fixture
def sample_demand_point() -> Dict[str, object]:
    """Return a minimal, valid demand-point payload."""

    return {
        "id": str(uuid.uuid4()),
        "name": "Test Mandi",
        "latitude": 12.97,
        "longitude": 77.60,
        "type": "apmc",
        "base_demand_per_day_kg": 500.0,
    }


@pytest.fixture
def sample_truck() -> Dict[str, object]:
    """Return a minimal, valid truck payload."""

    return {
        "id": str(uuid.uuid4()),
        "name": "Truck-01",
        "capacity_kg": 3000.0,
        "cost_per_km": 12.5,
    }
