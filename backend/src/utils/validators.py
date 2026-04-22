"""Generic input validators."""

from __future__ import annotations


def validate_latlng(latitude: float, longitude: float) -> None:
    """Raise ``ValueError`` if coordinates are out of range."""

    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"Invalid latitude: {latitude}")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"Invalid longitude: {longitude}")


def validate_positive(value: float, name: str = "value") -> None:
    """Raise ``ValueError`` if ``value`` is not strictly positive."""

    if value <= 0:
        raise ValueError(f"{name} must be > 0 (got {value})")
