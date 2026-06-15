"""Redis persistence for farmer private-offer acceptances."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import redis.asyncio as redis

from config import get_settings
from models.schemas import PriceOfferAcceptance
from tools.notifications.dispatcher import _log_notification
from tools.notifications.providers import get_provider

logger = logging.getLogger(__name__)

_REDIS: redis.Redis | None = None
_KEY_PREFIX = "price_accept:"
_TTL_S = 30 * 24 * 3600


async def _redis_client() -> redis.Redis:
    global _REDIS
    if _REDIS is None:
        _REDIS = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _REDIS


def _key(farm_id: str) -> str:
    return f"{_KEY_PREFIX}{farm_id}"


async def get_acceptance(farm_id: str) -> PriceOfferAcceptance | None:
    try:
        r = await _redis_client()
        raw = await r.get(_key(farm_id))
        if not raw:
            return None
        return PriceOfferAcceptance.model_validate(json.loads(raw))
    except Exception as exc:  # noqa: BLE001
        logger.warning("price accept get failed farm=%s: %s", farm_id, exc)
        return None


async def list_acceptances(farm_ids: list[str] | None = None) -> dict[str, PriceOfferAcceptance]:
    out: dict[str, PriceOfferAcceptance] = {}
    try:
        r = await _redis_client()
        if farm_ids:
            for fid in farm_ids:
                acc = await get_acceptance(fid)
                if acc:
                    out[fid] = acc
            return out
        async for key in r.scan_iter(match=f"{_KEY_PREFIX}*"):
            fid = key.removeprefix(_KEY_PREFIX)
            raw = await r.get(key)
            if raw:
                out[fid] = PriceOfferAcceptance.model_validate(json.loads(raw))
    except Exception as exc:  # noqa: BLE001
        logger.warning("price accept list failed: %s", exc)
    return out


async def save_acceptance(
    acceptance: PriceOfferAcceptance,
) -> tuple[PriceOfferAcceptance, bool]:
    """Persist acceptance. Returns (record, created). False if already accepted."""
    existing = await get_acceptance(acceptance.farm_id)
    if existing is not None:
        return existing, False

    stamped = acceptance.model_copy(
        update={"accepted_at": acceptance.accepted_at or datetime.now(timezone.utc)},
    )
    try:
        r = await _redis_client()
        await r.set(
            _key(stamped.farm_id),
            stamped.model_dump_json(),
            ex=_TTL_S,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("price accept save failed farm=%s: %s", stamped.farm_id, exc)

    await _maybe_notify_farmer(stamped)
    return stamped, True


async def _maybe_notify_farmer(acceptance: PriceOfferAcceptance) -> None:
    settings = get_settings()
    if not settings.NOTIFY_ENABLED:
        return
    phone = (settings.FIELD_OFFICER_PHONE or "").strip()
    if not phone:
        return
    try:
        provider = get_provider(settings.NOTIFY_PROVIDER.strip().lower() or "mock")
    except ValueError:
        return

    payout = round(acceptance.accepted_price_per_kg * acceptance.tonnage_kg, 0)
    channel = getattr(acceptance, "channel", "private") or "private"
    if channel == "apmc":
        body = (
            f"AgentFarm: {acceptance.farm_id} committed to APMC auction "
            f"at Rs {acceptance.accepted_price_per_kg:.0f}/kg "
            f"({acceptance.tonnage_kg:.0f} kg, est Rs {payout:.0f})."
        )[:160]
    else:
        body = (
            f"AgentFarm: {acceptance.farm_id} accepted private offer "
            f"at Rs {acceptance.accepted_price_per_kg:.0f}/kg "
            f"({acceptance.tonnage_kg:.0f} kg, est Rs {payout:.0f})."
        )[:160]
    try:
        msg_id = await provider.send_sms(phone, body)
        await _log_notification(
            run_id="price-board",
            plan_id=None,
            farm_id=acceptance.farm_id,
            channel="sms",
            phone=phone,
            body=body,
            priority="normal",
            provider=provider.name,
            provider_message_id=msg_id,
            status="sent",
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("price accept SMS skipped: %s", exc)
