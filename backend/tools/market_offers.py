"""Helpers for D4 market offer ledger."""

from __future__ import annotations

from uuid import uuid4


def stable_offer_id(side: str, demand_point_id: str, crop_type: str) -> str:
    """Generate a unique append-only offer id."""
    suffix = uuid4().hex[:8]
    return f"market-{side}-{demand_point_id}-{crop_type.lower()}-{suffix}"
