"""Redis persistence for direct buyer demand posts (D2)."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as redis

from config import get_settings
from tools.db import resolve_data_dir
from models.schemas import BuyerDemandPost, BuyerDemandPostCreate
from tools.buyer_demands import stable_post_id

logger = logging.getLogger(__name__)

_REDIS: redis.Redis | None = None
_KEY_PREFIX = "buyer_demand:"
_TTL_S = 30 * 24 * 3600


async def _redis_client() -> redis.Redis:
    global _REDIS
    if _REDIS is None:
        _REDIS = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _REDIS


def _key(post_id: str) -> str:
    return f"{_KEY_PREFIX}{post_id}"


def _load_csv_rows() -> list[BuyerDemandPost]:
    path = resolve_data_dir() / "sample_buyer_demands.csv"
    if not path.is_file():
        return []
    posts: list[BuyerDemandPost] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            dp_id = row["demand_point_id"]
            crop = row["crop_type"]
            post_id = row.get("id") or stable_post_id(dp_id, crop)
            posts.append(
                BuyerDemandPost(
                    id=post_id,
                    demand_point_id=dp_id,
                    buyer_name=row["buyer_name"],
                    buyer_type=row["buyer_type"],  # type: ignore[arg-type]
                    crop_type=crop,
                    quantity_kg=float(row["quantity_kg"]),
                    price_per_kg=float(row["price_per_kg"]),
                ),
            )
    return posts


async def seed_if_empty() -> int:
    """Load sample CSV into Redis when no buyer demand keys exist."""
    try:
        r = await _redis_client()
        async for _ in r.scan_iter(match=f"{_KEY_PREFIX}*", count=1):
            return 0
    except Exception as exc:  # noqa: BLE001
        logger.warning("buyer demand seed check failed: %s", exc)
        return 0

    seeded = 0
    for post in _load_csv_rows():
        _, created = await save_post(post)
        if created:
            seeded += 1
    if seeded:
        logger.info("buyer_demand_store: seeded %d posts from CSV", seeded)
    return seeded


async def list_posts() -> list[BuyerDemandPost]:
    out: list[BuyerDemandPost] = []
    try:
        r = await _redis_client()
        async for key in r.scan_iter(match=f"{_KEY_PREFIX}*"):
            raw = await r.get(key)
            if raw:
                out.append(BuyerDemandPost.model_validate(json.loads(raw)))
    except Exception as exc:  # noqa: BLE001
        logger.warning("buyer demand list failed: %s", exc)
    return sorted(out, key=lambda p: (p.demand_point_id, p.crop_type))


async def get_post(post_id: str) -> BuyerDemandPost | None:
    try:
        r = await _redis_client()
        raw = await r.get(_key(post_id))
        if not raw:
            return None
        return BuyerDemandPost.model_validate(json.loads(raw))
    except Exception as exc:  # noqa: BLE001
        logger.warning("buyer demand get failed id=%s: %s", post_id, exc)
        return None


async def save_post(post: BuyerDemandPost) -> tuple[BuyerDemandPost, bool]:
    """Persist post. Returns (record, created). Upsert preserves stable id."""
    existing = await get_post(post.id)
    stamped = post.model_copy(
        update={"posted_at": post.posted_at or datetime.now(timezone.utc)},
    )
    try:
        r = await _redis_client()
        await r.set(_key(stamped.id), stamped.model_dump_json(), ex=_TTL_S)
    except Exception as exc:  # noqa: BLE001
        logger.warning("buyer demand save failed id=%s: %s", stamped.id, exc)
    return stamped, existing is None


async def upsert_from_create(body: BuyerDemandPostCreate) -> BuyerDemandPost:
    post_id = stable_post_id(body.demand_point_id, body.crop_type)
    post = BuyerDemandPost(
        id=post_id,
        demand_point_id=body.demand_point_id,
        buyer_name=body.buyer_name,
        buyer_type=body.buyer_type,
        crop_type=body.crop_type,
        quantity_kg=body.quantity_kg,
        price_per_kg=body.price_per_kg,
    )
    saved, _ = await save_post(post)
    return saved


async def delete_post(post_id: str) -> bool:
    try:
        r = await _redis_client()
        removed = await r.delete(_key(post_id))
        return removed > 0
    except Exception as exc:  # noqa: BLE001
        logger.warning("buyer demand delete failed id=%s: %s", post_id, exc)
        return False
