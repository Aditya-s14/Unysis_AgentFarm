"""Notification provider implementations."""

from tools.notifications.providers.base import NotificationProvider
from tools.notifications.providers.mock import MockProvider

__all__ = ["MockProvider", "NotificationProvider", "get_provider"]


def get_provider(name: str) -> NotificationProvider:
    if name == "mock":
        return MockProvider()
    raise ValueError(
        f"Unknown NOTIFY_PROVIDER={name!r}; use 'mock' for dev or configure msg91/twilio"
    )
