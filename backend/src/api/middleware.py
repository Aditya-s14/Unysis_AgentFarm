"""Custom ASGI middleware: request IDs and request timing."""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach an ``X-Request-ID`` header, generate one if absent."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Log request duration and expose it via ``X-Process-Time``."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}"
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(elapsed_ms, 2),
            request_id=getattr(request.state, "request_id", None),
        )
        return response


def install_middleware(app: FastAPI) -> None:
    """Install the AgentFarm middleware stack on ``app``."""

    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)


__all__ = ["RequestIDMiddleware", "TimingMiddleware", "install_middleware"]

_ = ASGIApp  # keep import for type checkers referencing Starlette
