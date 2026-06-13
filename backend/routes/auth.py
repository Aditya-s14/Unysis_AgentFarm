"""POST /api/auth/request-otp, POST /api/auth/verify-otp, GET /api/auth/me (T1)."""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from config import get_settings
from tools.auth import (
    create_token,
    generate_otp,
    get_current_user,
    get_otp_provider,
    get_user_by_phone,
    store_otp,
    verify_otp,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")


def _normalize_phone(raw: str) -> str:
    phone = raw.strip().replace(" ", "").replace("-", "")
    if not _PHONE_RE.match(phone):
        raise HTTPException(status_code=422, detail="Invalid phone number format")
    if not phone.startswith("+"):
        phone = f"+91{phone[-10:]}" if len(phone) == 10 else f"+{phone}"
    return phone


class RequestOTPBody(BaseModel):
    phone: str = Field(min_length=10, max_length=20)


class VerifyOTPBody(BaseModel):
    phone: str = Field(min_length=10, max_length=20)
    code: str = Field(min_length=4, max_length=8)


@router.post("/auth/request-otp")
async def request_otp(body: RequestOTPBody, request: Request) -> dict:
    """Send a one-time code to a registered phone."""
    phone = _normalize_phone(body.phone)

    user = await get_user_by_phone(phone)
    if user is None:
        # Unknown phones are rejected (registration is an FPO/admin action,
        # out of T1 scope). 404 keeps the demo error message honest.
        raise HTTPException(status_code=404, detail="Phone number not registered")

    code = generate_otp()
    try:
        await store_otp(request.app.state.redis, phone, code)
    except Exception as exc:
        logger.exception("OTP store failed")
        raise HTTPException(status_code=503, detail="OTP storage unavailable") from exc

    provider = get_otp_provider()
    await provider.send(phone, code)

    resp: dict = {"sent": True, "ttl_seconds": get_settings().OTP_TTL_SECONDS}
    if provider.name == "mock":
        # Dev convenience only — the mock provider has no SMS channel, so the
        # demo UI shows the code inline. Real providers never echo the code.
        resp["dev_otp"] = code
    return resp


@router.post("/auth/verify-otp")
async def verify_otp_endpoint(body: VerifyOTPBody, request: Request) -> dict:
    """Exchange a valid OTP for a JWT carrying {role, entity_id}."""
    phone = _normalize_phone(body.phone)

    try:
        ok = await verify_otp(request.app.state.redis, phone, body.code.strip())
    except Exception as exc:
        logger.exception("OTP verify failed")
        raise HTTPException(status_code=503, detail="OTP storage unavailable") from exc
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid or expired code")

    user = await get_user_by_phone(phone)
    if user is None:
        raise HTTPException(status_code=404, detail="Phone number not registered")

    token = create_token(
        phone=user.phone, role=user.role, entity_id=user.entity_id, name=user.name,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": get_settings().JWT_TTL_HOURS * 3600,
        "role": user.role,
        "entity_id": user.entity_id,
        "name": user.name,
    }


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)) -> dict:
    """Decoded claims of the calling token — used by the frontend to hydrate."""
    return {
        "phone": user.get("sub"),
        "role": user.get("role"),
        "entity_id": user.get("entity_id"),
        "name": user.get("name"),
        "exp": user.get("exp"),
    }
