"""Redis persistence for D4 bid/ask offer ledger."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as redis

from config import get_settings
from models.schemas import (
    MarketAcceptRequest,
    MarketAcceptedCommitment,
    MarketOffer,
    MarketOfferCreate,
)
from tools.db import resolve_data_dir
from tools.market_offers import stable_offer_id

logger = logging.getLogger(__name__)

_REDIS: redis.Redis | None = None
_OFFER_PREFIX = "market_offer:"
_ACCEPTED_PREFIX = "market_accepted:"
_TTL_S = 30 * 24 * 3600


async def _redis_client() -> redis.Redis:
    global _REDIS
    if _REDIS is None:
        _REDIS = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _REDIS


def _offer_key(offer_id: str) -> str:
    return f"{_OFFER_PREFIX}{offer_id}"


def _accepted_key(offer_id: str) -> str:
    return f"{_ACCEPTED_PREFIX}{offer_id}"


def _validate_create(body: MarketOfferCreate) -> None:
    if body.side == "ask":
        if body.role != "farmer":
            raise ValueError("ask offers require role=farmer")
        if not body.farm_id:
            raise ValueError("ask offers require farm_id")
    elif body.side == "bid":
        if body.role != "buyer":
            raise ValueError("bid offers require role=buyer")
        if not body.buyer_name:
            raise ValueError("bid offers require buyer_name")
    else:
        raise ValueError(f"invalid side {body.side!r}")


def _load_csv_rows() -> tuple[list[MarketOffer], list[MarketAcceptedCommitment]]:
    path = resolve_data_dir() / "sample_market_offers.csv"
    if not path.is_file():
        return [], []
    offers: list[MarketOffer] = []
    commitments: list[MarketAcceptedCommitment] = []
    now = datetime.now(timezone.utc)
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            status = row.get("status") or "open"
            farm_id = row.get("farm_id") or None
            buyer_name = row.get("buyer_name") or None
            accepted_at = now if status == "accepted" else None
            offer = MarketOffer(
                id=row["id"],
                side=row["side"],  # type: ignore[arg-type]
                role=row["role"],  # type: ignore[arg-type]
                farm_id=farm_id or None,
                buyer_name=buyer_name or None,
                demand_point_id=row["demand_point_id"],
                crop_type=row["crop_type"],
                quantity_kg=float(row["quantity_kg"]),
                price_per_kg=float(row["price_per_kg"]),
                status=status,  # type: ignore[arg-type]
                created_at=now,
                accepted_at=accepted_at,
            )
            offers.append(offer)
            if status == "accepted" and farm_id:
                commitments.append(
                    MarketAcceptedCommitment(
                        offer_id=offer.id,
                        farm_id=farm_id,
                        demand_point_id=offer.demand_point_id,
                        crop_type=offer.crop_type,
                        quantity_kg=offer.quantity_kg,
                        price_per_kg=offer.price_per_kg,
                        accepted_at=accepted_at or now,
                    ),
                )
    return offers, commitments


async def seed_if_empty() -> int:
    """Load sample CSV into Redis when no market offer keys exist."""
    try:
        r = await _redis_client()
        async for _ in r.scan_iter(match=f"{_OFFER_PREFIX}*", count=1):
            return 0
    except Exception as exc:  # noqa: BLE001
        logger.warning("market offer seed check failed: %s", exc)
        return 0

    offers, commitments = _load_csv_rows()
    seeded = 0
    for offer in offers:
        _, created = await _save_offer(offer)
        if created:
            seeded += 1
    for commitment in commitments:
        await _save_accepted(commitment)
    if seeded:
        logger.info(
            "market_offer_store: seeded %d offers (%d accepted) from CSV",
            seeded,
            len(commitments),
        )
    return seeded


async def list_offers(*, status: str | None = None) -> list[MarketOffer]:
    out: list[MarketOffer] = []
    try:
        r = await _redis_client()
        async for key in r.scan_iter(match=f"{_OFFER_PREFIX}*"):
            raw = await r.get(key)
            if raw:
                offer = MarketOffer.model_validate(json.loads(raw))
                if status is None or offer.status == status:
                    out.append(offer)
    except Exception as exc:  # noqa: BLE001
        logger.warning("market offer list failed: %s", exc)
    return sorted(out, key=lambda o: (o.created_at or datetime.min.replace(tzinfo=timezone.utc), o.id))


async def get_offer(offer_id: str) -> MarketOffer | None:
    try:
        r = await _redis_client()
        raw = await r.get(_offer_key(offer_id))
        if not raw:
            return None
        return MarketOffer.model_validate(json.loads(raw))
    except Exception as exc:  # noqa: BLE001
        logger.warning("market offer get failed id=%s: %s", offer_id, exc)
        return None


async def _save_offer(offer: MarketOffer) -> tuple[MarketOffer, bool]:
    existing = await get_offer(offer.id)
    stamped = offer.model_copy(
        update={"created_at": offer.created_at or datetime.now(timezone.utc)},
    )
    try:
        r = await _redis_client()
        await r.set(_offer_key(stamped.id), stamped.model_dump_json(), ex=_TTL_S)
    except Exception as exc:  # noqa: BLE001
        logger.warning("market offer save failed id=%s: %s", stamped.id, exc)
    return stamped, existing is None


async def _save_accepted(commitment: MarketAcceptedCommitment) -> None:
    try:
        r = await _redis_client()
        await r.set(
            _accepted_key(commitment.offer_id),
            commitment.model_dump_json(),
            ex=_TTL_S,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "market accepted save failed offer_id=%s: %s",
            commitment.offer_id,
            exc,
        )


async def list_accepted_commitments() -> list[MarketAcceptedCommitment]:
    out: list[MarketAcceptedCommitment] = []
    try:
        r = await _redis_client()
        async for key in r.scan_iter(match=f"{_ACCEPTED_PREFIX}*"):
            raw = await r.get(key)
            if raw:
                out.append(MarketAcceptedCommitment.model_validate(json.loads(raw)))
    except Exception as exc:  # noqa: BLE001
        logger.warning("market accepted list failed: %s", exc)
    return sorted(out, key=lambda c: c.accepted_at)


async def create_offer(body: MarketOfferCreate) -> MarketOffer:
    _validate_create(body)
    offer_id = stable_offer_id(body.side, body.demand_point_id, body.crop_type)
    offer = MarketOffer(
        id=offer_id,
        side=body.side,
        role=body.role,
        farm_id=body.farm_id,
        buyer_name=body.buyer_name,
        demand_point_id=body.demand_point_id,
        crop_type=body.crop_type,
        quantity_kg=body.quantity_kg,
        price_per_kg=body.price_per_kg,
        status="open",
    )
    saved, _ = await _save_offer(offer)
    return saved


async def accept_offer(body: MarketAcceptRequest) -> MarketAcceptedCommitment:
    offer = await get_offer(body.offer_id)
    if offer is None:
        raise LookupError(f"offer {body.offer_id!r} not found")
    if offer.status != "open":
        raise ValueError(f"offer {body.offer_id!r} is not open (status={offer.status})")

    if offer.side == "ask":
        farm_id = offer.farm_id
        if not farm_id:
            raise ValueError("ask offer missing farm_id")
    else:
        farm_id = body.farm_id
        if not farm_id:
            raise ValueError("accepting a bid requires farm_id")

    now = datetime.now(timezone.utc)
    commitment = MarketAcceptedCommitment(
        offer_id=offer.id,
        farm_id=farm_id,
        demand_point_id=offer.demand_point_id,
        crop_type=offer.crop_type,
        quantity_kg=offer.quantity_kg,
        price_per_kg=offer.price_per_kg,
        accepted_at=now,
    )
    updated_offer = offer.model_copy(update={"status": "accepted", "accepted_at": now})
    if offer.side == "bid":
        updated_offer = updated_offer.model_copy(update={"farm_id": farm_id})
    await _save_offer(updated_offer)
    await _save_accepted(commitment)
    return commitment
