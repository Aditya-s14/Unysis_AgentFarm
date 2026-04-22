"""Unit converters relevant to Indian agricultural data."""

from __future__ import annotations

from .constants import ACRE_PER_BIGHA, KG_PER_QUINTAL


def quintal_to_kg(quintal: float) -> float:
    """Convert quintals to kilograms."""

    return quintal * KG_PER_QUINTAL


def kg_to_quintal(kg: float) -> float:
    """Convert kilograms to quintals."""

    return kg / KG_PER_QUINTAL


def bigha_to_acre(bigha: float) -> float:
    """Convert bigha to acres (approximate)."""

    return bigha * ACRE_PER_BIGHA


def acre_to_bigha(acre: float) -> float:
    """Convert acres to bigha (approximate)."""

    return acre / ACRE_PER_BIGHA
