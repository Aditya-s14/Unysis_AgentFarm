"""GET/POST /api/price-board — APMC vs private buyer price discovery."""

from __future__ import annotations

import logging

from fastapi import HTTPException
from fastapi import APIRouter
from sqlalchemy import select

from models.db_models import DemandPointRow, FarmRow
from models.schemas import DemandPoint, Farm, PriceOfferAcceptance
from tools.db import get_session_maker
from tools.price_accept_store import get_acceptance, list_acceptances, save_acceptance
from tools.price_discovery import build_price_board, build_price_quote

router = APIRouter()
logger = logging.getLogger(__name__)


async def _load_farms_and_demand() -> tuple[list[Farm], list[DemandPoint]]:
    async with get_session_maker()() as session:
        farm_rows = list(await session.scalars(select(FarmRow)))
        dp_rows = list(await session.scalars(select(DemandPointRow)))
    farms = [
        Farm(
            id=r.id,
            name=r.name,
            lat=r.lat,
            lng=r.lng,
            crop_type=r.crop_type,
            acreage=r.acreage,
            typical_yield_kg=r.typical_yield_kg,
            harvest_window_start=r.harvest_window_start,
            harvest_window_end=r.harvest_window_end,
            phone=r.phone,
            preferred_language=r.preferred_language or "en",
            notify_channel=r.notify_channel or "sms",  # type: ignore[arg-type]
            notify_opt_in=bool(r.notify_opt_in),
        )
        for r in farm_rows
    ]
    dps = [
        DemandPoint(
            id=r.id,
            name=r.name,
            lat=r.lat,
            lng=r.lng,
            type=r.point_type,  # type: ignore[arg-type]
            base_demand_per_day=r.base_demand_per_day,
        )
        for r in dp_rows
    ]
    return farms, dps


def _acceptance_dict(accepted: dict[str, PriceOfferAcceptance]) -> dict[str, dict]:
    return {
        fid: acc.model_dump(mode="json")
        for fid, acc in accepted.items()
    }


@router.get("/price-board")
async def get_price_board() -> dict:
    """Quotes for all seeded farms plus any Redis-stored acceptances."""
    farms, dps = await _load_farms_and_demand()
    quotes = build_price_board(farms, dps)
    farm_ids = [q.farm_id for q in quotes]
    accepted = await list_acceptances(farm_ids)
    return {
        "quotes": [q.to_dict() for q in quotes],
        "accepted": _acceptance_dict(accepted),
    }


@router.get("/price-board/{farm_id}")
async def get_price_board_farm(farm_id: str) -> dict:
    farms, dps = await _load_farms_and_demand()
    farm = next((f for f in farms if f.id == farm_id), None)
    if farm is None:
        raise HTTPException(status_code=404, detail=f"farm {farm_id} not found")
    quote = build_price_quote(farm, dps)
    if quote is None:
        raise HTTPException(status_code=404, detail="no apmc/private demand points for quote")
    acc = await get_acceptance(farm_id)
    return {
        "quote": quote.to_dict(),
        "accepted": acc.model_dump(mode="json") if acc else None,
    }


@router.post("/price-board/accept")
async def accept_private_offer(body: PriceOfferAcceptance) -> dict:
    """Record farmer acceptance of a private buyer offer."""
    farms, dps = await _load_farms_and_demand()
    farm = next((f for f in farms if f.id == body.farm_id), None)
    if farm is None:
        raise HTTPException(status_code=404, detail=f"farm {body.farm_id} not found")

    quote = build_price_quote(farm, dps)
    if quote is None:
        raise HTTPException(status_code=422, detail="cannot build quote for farm")

    acceptance = body.model_copy(
        update={
            "crop_type": quote.crop_type,
            "apmc_demand_point_id": quote.apmc_demand_point_id,
            "private_demand_point_id": quote.private_demand_point_id,
            "accepted_price_per_kg": quote.private_offer_per_kg,
            "tonnage_kg": body.tonnage_kg or quote.tonnage_kg,
        },
    )
    saved, created = await save_acceptance(acceptance)
    payout = round(saved.accepted_price_per_kg * saved.tonnage_kg, 0)
    if not created:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "offer already accepted",
                "acceptance": saved.model_dump(mode="json"),
                "payout_inr": payout,
            },
        )
    return {
        "accepted": True,
        "acceptance": saved.model_dump(mode="json"),
        "payout_inr": payout,
    }
