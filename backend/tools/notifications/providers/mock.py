"""Log-only provider for dev, tests, and demo deployments without SMS credentials."""

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)


class MockProvider:
    """Writes alert content to logs instead of calling an external API."""

    @property
    def name(self) -> str:
        return "mock"

    async def send_sms(
        self,
        to: str,
        body: str,
        *,
        template_id: str | None = None,
    ) -> str:
        msg_id = f"mock-sms-{uuid.uuid4().hex[:12]}"
        logger.info("MOCK SMS → %s: %s", to, body)
        return msg_id

    async def send_voice(
        self,
        to: str,
        script: str,
        *,
        language: str = "en",
    ) -> str:
        call_id = f"mock-voice-{uuid.uuid4().hex[:12]}"
        logger.info("MOCK VOICE (%s) → %s: %s", language, to, script)
        return call_id
