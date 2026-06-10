"""FastAPI application for AgentFarm Optimizer."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from fastapi import Depends

from config import get_settings
from routes.advisor import router as advisor_router
from routes.auth import router as auth_router
from routes.reroute import router as reroute_router
from routes.runs import router as runs_router
from routes.scenario import router as scenario_router
from tools.auth import ensure_demo_users, get_current_user
from tools.db import (
    backfill_outcome_dims_from_csv,
    dispose_db,
    get_engine,
    init_db,
    seed_if_empty,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await init_db()
    await seed_if_empty()
    await backfill_outcome_dims_from_csv()
    await ensure_demo_users()

    engine: AsyncEngine = get_engine()
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.engine = engine
    app.state.redis = client

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    app.state.db_ready = True

    app.state.redis_ready = False
    try:
        await client.ping()
        app.state.redis_ready = True
    except Exception as exc:
        logger.warning("Redis ping failed at startup — cache/session features degraded: %s", exc)

    try:
        yield
    finally:
        await client.aclose()
        await dispose_db()


app = FastAPI(title="AgentFarm Optimizer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
# Auth endpoints are always live; the pre-existing API is JWT-protected only
# when AUTH_ENABLED=true (kept off mid-sprint so teammates aren't blocked).
_protected = [Depends(get_current_user)] if get_settings().AUTH_ENABLED else []
app.include_router(auth_router, prefix="/api")
app.include_router(scenario_router, prefix="/api", dependencies=_protected)
app.include_router(runs_router, prefix="/api", dependencies=_protected)
app.include_router(advisor_router, prefix="/api", dependencies=_protected)
# Reroute (R4) carries its own require_role("driver","fpo") — always enforced.
app.include_router(reroute_router, prefix="/api")


# --- Global exception handler ---
@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — process is up."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready(request: Request) -> JSONResponse:
    """Readiness probe — Postgres and Redis connectivity."""
    checks: dict[str, str] = {}
    ok = True

    try:
        engine: AsyncEngine = request.app.state.engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        ok = False

    try:
        client = request.app.state.redis
        await client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        ok = False

    body = {"status": "ok" if ok else "degraded", "checks": checks}
    return JSONResponse(status_code=200 if ok else 503, content=body)
