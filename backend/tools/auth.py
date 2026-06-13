"""OTP + JWT authentication (T1).

Phone-first auth for rural India: no email, no password. A user requests a
6-digit OTP for their registered phone, verifies it, and receives a JWT
carrying ``{sub: phone, role, entity_id}``. Roles: fpo / farmer / driver /
mandi (see PLAN doc T1).

OTP delivery is pluggable via ``OTP_PROVIDER``; the only implementation today
is ``mock`` (logs the code, and the request endpoint echoes it back as
``dev_otp`` so demos work with zero SMS infrastructure). A real SMS provider
(MSG91 / Twilio / WhatsApp) is a ~30-line class with the same ``send()``
signature — no auth-flow changes.

OTP state lives in Redis: ``otp:{phone}`` holds a SHA-256 of the code (never
the code itself) with TTL, ``otp_tries:{phone}`` caps verify attempts.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import redis.asyncio as redis
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from config import get_settings
from models.db_models import UserRow
from tools.db import get_session_maker

logger = logging.getLogger(__name__)

ROLES = ("fpo", "farmer", "driver", "mandi")

_OTP_PREFIX = "otp:"
_OTP_TRIES_PREFIX = "otp_tries:"
_MAX_VERIFY_ATTEMPTS = 5

_bearer = HTTPBearer(auto_error=False)


# --- JWT -------------------------------------------------------------------


def create_token(*, phone: str, role: str, entity_id: str | None, name: str | None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": phone,
        "role": role,
        "entity_id": entity_id,
        "name": name,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.JWT_TTL_HOURS)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """FastAPI dependency — decoded JWT claims of the calling user."""
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(creds.credentials)


def require_role(*roles: str):
    """Dependency factory: 403 unless the caller's role is in ``roles``."""

    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role in {sorted(roles)}; you are '{user.get('role')}'",
            )
        return user

    return _checker


# --- OTP -------------------------------------------------------------------


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def store_otp(r: redis.Redis, phone: str, code: str) -> None:
    ttl = get_settings().OTP_TTL_SECONDS
    await r.set(f"{_OTP_PREFIX}{phone}", _hash_code(code), ex=ttl)
    await r.delete(f"{_OTP_TRIES_PREFIX}{phone}")


async def verify_otp(r: redis.Redis, phone: str, code: str) -> bool:
    """Constant-shape verify: counts attempts, deletes the code on success."""
    tries_key = f"{_OTP_TRIES_PREFIX}{phone}"
    tries = await r.incr(tries_key)
    await r.expire(tries_key, get_settings().OTP_TTL_SECONDS)
    if tries > _MAX_VERIFY_ATTEMPTS:
        return False

    key = f"{_OTP_PREFIX}{phone}"
    stored = await r.get(key)
    if stored is None or stored != _hash_code(code):
        return False
    await r.delete(key)
    await r.delete(tries_key)
    return True


# --- OTP delivery providers --------------------------------------------------


class MockOTPProvider:
    """Dev/demo delivery: logs the code instead of sending an SMS."""

    name = "mock"

    async def send(self, phone: str, code: str) -> None:
        logger.info("[MockOTP] OTP for %s is %s", phone, code)


def get_otp_provider() -> MockOTPProvider:
    provider = (get_settings().OTP_PROVIDER or "mock").strip().lower()
    if provider != "mock":
        logger.warning("OTP_PROVIDER=%r not implemented; using mock", provider)
    return MockOTPProvider()


# --- Users -------------------------------------------------------------------


async def get_user_by_phone(phone: str) -> UserRow | None:
    factory = get_session_maker()
    async with factory() as session:
        return await session.scalar(select(UserRow).where(UserRow.phone == phone))


# One demo login per role, wired to real seed-data entities.
_DEMO_USERS = [
    {"phone": "+919800000001", "role": "fpo", "entity_id": None, "name": "FPO Admin"},
    {"phone": "+919800000002", "role": "farmer", "entity_id": "farm-001", "name": "Farmer (Nandi Valley)"},
    {"phone": "+919800000003", "role": "driver", "entity_id": "tr-001", "name": "Driver (tr-001)"},
    {"phone": "+919800000004", "role": "mandi", "entity_id": "dp-apmc-01", "name": "Mandi (Yeshwanthpur)"},
]


async def ensure_demo_users() -> None:
    """Idempotently seed one user per role so every dashboard is demoable."""
    factory = get_session_maker()
    async with factory() as session:
        for u in _DEMO_USERS:
            existing = await session.scalar(
                select(UserRow).where(UserRow.phone == u["phone"]),
            )
            if existing is None:
                session.add(UserRow(**u))
        await session.commit()
