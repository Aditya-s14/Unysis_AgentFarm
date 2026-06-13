"""GET/POST/DELETE /api/buyer/demand — direct buyer crop demand posts."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from models.db_models import DemandPointRow
from models.schemas import BuyerDemandPostCreate, DemandPoint
from tools.buyer_demand_store import delete_post, list_posts, upsert_from_create
from tools.db import get_session_maker

router = APIRouter()
logger = logging.getLogger(__name__)


async def _load_private_demand_points() -> dict[str, DemandPoint]:
    async with get_session_maker()() as session:
        rows = list(
            await session.scalars(
                select(DemandPointRow).where(DemandPointRow.point_type == "private"),
            ),
        )
    return {
        r.id: DemandPoint(
            id=r.id,
            name=r.name,
            lat=r.lat,
            lng=r.lng,
            type="private",
            base_demand_per_day=r.base_demand_per_day,
        )
        for r in rows
    }


async def _validate_private_dp(demand_point_id: str) -> None:
    private = await _load_private_demand_points()
    if demand_point_id not in private:
        raise HTTPException(
            status_code=422,
            detail=f"demand_point_id {demand_point_id!r} must reference a private demand point",
        )


@router.get("/buyer/demand")
async def get_buyer_demands() -> dict:
    posts = await list_posts()
    return {"posts": [p.model_dump(mode="json") for p in posts]}


@router.post("/buyer/demand")
async def post_buyer_demand(body: BuyerDemandPostCreate) -> dict:
    await _validate_private_dp(body.demand_point_id)
    saved = await upsert_from_create(body)
    return {"post": saved.model_dump(mode="json")}


@router.delete("/buyer/demand/{post_id}")
async def remove_buyer_demand(post_id: str) -> dict:
    removed = await delete_post(post_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"post {post_id!r} not found")
    return {"deleted": True, "post_id": post_id}
