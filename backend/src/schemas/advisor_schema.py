"""Pydantic schemas for the Advisor Agent API."""

from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


class AdvisorRequest(BaseModel):
    """Payload for ``POST /api/advisor/query``."""

    run_id: uuid.UUID = Field(..., alias="runId")
    session_id: str = Field(..., alias="sessionId", max_length=128)
    user_question: str = Field(..., alias="userQuestion", min_length=1, max_length=2048)
    language: str = Field("en", description="Response language code (e.g. 'en', 'hi')")

    model_config = {"populate_by_name": True}


class AdvisorMessage(BaseModel):
    """A single message in the advisor session buffer."""

    role: str
    content: str


class AdvisorResponse(BaseModel):
    """Response for ``POST /api/advisor/query``."""

    answer: str
    session_id: str = Field(..., alias="sessionId")
    referenced_entities: List[str] = Field(default_factory=list)
    history: Optional[List[AdvisorMessage]] = None

    model_config = {"populate_by_name": True}
