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

from config import get_settings
from routes.advisor import router as advisor_router
from routes.runs import router as runs_router
from routes.scenario import router as scenario_router
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

    engine: AsyncEngine = get_engine()
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.engine = engine
    app.state.redis = client

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    await client.ping()

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
app.include_router(scenario_router, prefix="/api")
app.include_router(runs_router, prefix="/api")
app.include_router(advisor_router, prefix="/api")


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
    return {"status": "ok"}
