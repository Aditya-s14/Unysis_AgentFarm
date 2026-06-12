"""Farmer SMS/voice alerts when a plan is ready (offline-friendly fallback channel)."""

from tools.notifications.dispatcher import dispatch_farm_alerts

__all__ = ["dispatch_farm_alerts"]
