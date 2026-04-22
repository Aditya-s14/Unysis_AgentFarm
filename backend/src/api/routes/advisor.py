"""``POST /api/advisor/query`` — decoupled Farmer Advisor service."""

from __future__ import annotations

from fastapi import APIRouter, status

from ...agents.advisor_agent import AdvisorAgent
from ...schemas.advisor_schema import AdvisorRequest, AdvisorResponse

router = APIRouter(prefix="/advisor", tags=["advisor"])

_advisor = AdvisorAgent()


@router.post("/query", response_model=AdvisorResponse, status_code=status.HTTP_200_OK)
async def post_advisor_query(request: AdvisorRequest) -> AdvisorResponse:
    """Generate a contextual plain-language answer for a farmer query."""

    result = await _advisor.answer(
        run_id=request.run_id,
        session_id=request.session_id,
        user_question=request.user_question,
        language=request.language,
    )
    return AdvisorResponse(
        answer=result["answer"],
        sessionId=result["session_id"],
        referenced_entities=result.get("referenced_entities", []),
        history=None,
    )
