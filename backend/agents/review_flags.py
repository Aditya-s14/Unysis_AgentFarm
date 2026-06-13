"""Shared human-review and retry-limit helpers for validator / orchestrator / graph."""

from __future__ import annotations

from config import get_settings
from memory.state import AgentFarmState


def max_retries() -> int:
    """Configured retry cap (default 2)."""
    return max(0, int(get_settings().max_retries))


def needs_human_review(state: AgentFarmState) -> bool:
    """True only when retries are exhausted and the plan is still invalid."""
    vr = state.get("validation_result")
    retry = state.get("retry_count") or 0
    if vr is not None and vr.valid:
        return False
    return retry >= max_retries()
