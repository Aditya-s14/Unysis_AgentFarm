"""Global exception handlers for the FastAPI app."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class AgentFarmError(Exception):
    """Base class for domain-specific exceptions."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR


class NotFoundError(AgentFarmError):
    """Raised when a requested entity does not exist."""

    status_code = status.HTTP_404_NOT_FOUND


class ValidationFailedError(AgentFarmError):
    """Raised when domain validation fails."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


def _problem_response(status_code: int, detail: str, **extra: Any) -> JSONResponse:
    body: Dict[str, Any] = {"detail": detail, "status_code": status_code}
    body.update(extra)
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the given FastAPI app."""

    @app.exception_handler(AgentFarmError)
    async def _agentfarm_error(_: Request, exc: AgentFarmError) -> JSONResponse:
        logger.warning("agentfarm_error", error=str(exc), status=exc.status_code)
        return _problem_response(exc.status_code, str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("validation_error", errors=exc.errors())
        return _problem_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Request validation failed",
            errors=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", error=str(exc))
        return _problem_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
        )
