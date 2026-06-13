"""Map internal exceptions to safe HTTP error messages for API clients."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def is_database_leak_message(text: str) -> bool:
    """True when exception text looks like raw SQL / driver internals."""
    lowered = text.lower()
    markers = (
        "insert into",
        "integrityerror",
        "foreignkeyviolation",
        "asyncpg.exceptions",
        "sqlalchemy",
        "[sql:",
        "parameters:",
    )
    return any(m in lowered for m in markers)


def friendly_outcome_error(exc: Exception) -> HTTPException:
    """Return a client-safe HTTP error for outcome persistence failures."""
    if isinstance(exc, IntegrityError) or is_database_leak_message(str(exc)):
        return HTTPException(
            status_code=409,
            detail="Could not save outcome — run may be missing from the database. Run a new scenario and try again.",
        )
    return HTTPException(
        status_code=500,
        detail="Could not save outcome. Please try again or contact support.",
    )
