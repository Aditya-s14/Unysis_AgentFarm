"""Provider protocol for outbound farmer alerts."""

from __future__ import annotations

from typing import Protocol


class NotificationProvider(Protocol):
    """Send SMS and optional voice alerts to a farmer phone number."""

    @property
    def name(self) -> str:
        """Provider identifier stored in notification_logs."""

    async def send_sms(
        self,
        to: str,
        body: str,
        *,
        template_id: str | None = None,
    ) -> str:
        """Send SMS; return provider message id."""

    async def send_voice(
        self,
        to: str,
        script: str,
        *,
        language: str = "en",
    ) -> str:
        """Place voice call with TTS script; return provider call id."""
