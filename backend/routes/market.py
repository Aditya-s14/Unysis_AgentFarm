"""GET/POST /api/market/* — bid/ask offer ledger (D4)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from models.db_models import DemandPointRow
from models.schemas import DemandPoint, MarketAcceptRequest, MarketOfferCreate
from tools.db import get_session_maker
from tools.market_offer_store import (
    accept_offer,
    create_offer,
    get_offer,
    list_accepted_commitments,
    list_offers,
)

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


@router.get("/market/offers")
async def get_market_offers() -> dict:
    offers = await list_offers()
    return {"offers": [o.model_dump(mode="json") for o in offers]}


@router.get("/market/accepted")
async def get_market_accepted() -> dict:
    commitments = await list_accepted_commitments()
    return {"commitments": [c.model_dump(mode="json") for c in commitments]}


@router.post("/market/offer")
async def post_market_offer(body: MarketOfferCreate) -> dict:
    await _validate_private_dp(body.demand_point_id)
    try:
        saved = await create_offer(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"offer": saved.model_dump(mode="json")}


@router.post("/market/accept")
async def post_market_accept(body: MarketAcceptRequest) -> dict:
    offer = await get_offer(body.offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail=f"offer {body.offer_id!r} not found")
    try:
        commitment = await accept_offer(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    farmer_commitment = {
        "farm_id": commitment.farm_id,
        "tonnage_kg": commitment.quantity_kg,
        "demand_point_id": commitment.demand_point_id,
    }
    return {
        "commitment": commitment.model_dump(mode="json"),
        "farmer_commitment": farmer_commitment,
        "offer": (await get_offer(body.offer_id)).model_dump(mode="json"),
    }
