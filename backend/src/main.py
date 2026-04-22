"""FastAPI application entrypoint for AgentFarm Optimizer."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.middleware import install_middleware
from .api.routes import get_api_router
from .config.logging_config import configure_logging, get_logger
from .config.settings import get_settings
from .models.database import dispose_engine, init_db
from .services.cache_service import get_cache
from .utils.error_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Connect to DB + Redis on startup and clean up on shutdown."""

    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    logger.info("startup_begin", app=settings.APP_NAME, debug=settings.DEBUG)

    cache = get_cache()
    try:
        await init_db()
    except Exception as exc:  # pragma: no cover - infra path
        logger.warning("init_db_failed", error=str(exc))

    try:
        await cache.connect()
    except Exception as exc:  # pragma: no cover - infra path
        logger.warning("redis_connect_failed", error=str(exc))

    logger.info("startup_ready")
    try:
        yield
    finally:
        logger.info("shutdown_begin")
        await cache.disconnect()
        await dispose_engine()
        logger.info("shutdown_done")


def create_app() -> FastAPI:
    """Application factory."""

    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_middleware(app)
    register_exception_handlers(app)

    @app.get("/health", tags=["health"])
    async def health() -> Dict[str, str]:
        """Liveness probe."""

        return {"status": "ok", "app": settings.APP_NAME, "version": "0.1.0"}

    app.include_router(get_api_router(), prefix="/api")
    return app


app = create_app()
