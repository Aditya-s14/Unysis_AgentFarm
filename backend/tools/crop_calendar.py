"""Crop calendar — peak harvest detection and truck fleet gap analysis."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from models.schemas import Farm, Truck

ALERT_DAYS_BEFORE_PEAK = 14


@dataclass
class TruckGapAnalysis:
    peak_date: date
    days_until_peak: int
    peak_yield_kg: float
    registered_trucks: int
    trucks_needed: int
    truck_gap: int
    alert_due: bool
    farms_on_peak: list[str]
    crop_summary: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["peak_date"] = self.peak_date.isoformat()
        return d


def active_yield_on_day(farms: list[Farm], day: date) -> float:
    """Sum typical_yield_kg for farms whose harvest window includes *day*."""
    total = 0.0
    for farm in farms:
        if farm.harvest_window_start <= day <= farm.harvest_window_end:
            total += farm.typical_yield_kg
    return total


def farms_active_on_day(farms: list[Farm], day: date) -> list[str]:
    return [
        f.id
        for f in farms
        if f.harvest_window_start <= day <= f.harvest_window_end
    ]


def find_peak_harvest_day(
    farms: list[Farm],
    today: date | None = None,
    *,
    horizon_days: int = 90,
) -> tuple[date, float]:
    """Return (peak_date, peak_yield_kg) within the forward horizon."""
    ref = today or date.today()
    best_day = ref
    best_yield = 0.0
    for offset in range(horizon_days + 1):
        day = ref + timedelta(days=offset)
        y = active_yield_on_day(farms, day)
        if y > best_yield:
            best_yield = y
            best_day = day
    return best_day, best_yield


def estimate_trucks_needed(total_kg: float, trucks: list[Truck]) -> int:
    if not trucks or total_kg <= 0:
        return 0
    avg_cap = sum(t.capacity_kg for t in trucks) / len(trucks)
    if avg_cap <= 0:
        return 0
    return max(1, math.ceil(total_kg / avg_cap))


def _crop_summary(farms: list[Farm], farm_ids: list[str]) -> str:
    by_crop: dict[str, int] = {}
    id_set = set(farm_ids)
    for f in farms:
        if f.id in id_set:
            by_crop[f.crop_type] = by_crop.get(f.crop_type, 0) + 1
    if not by_crop:
        return "mixed"
    return ", ".join(f"{c} ({n})" for c, n in sorted(by_crop.items()))


def analyze_truck_gap(
    farms: list[Farm],
    trucks: list[Truck],
    today: date | None = None,
) -> TruckGapAnalysis:
    """Compare registered fleet size vs estimated need at peak harvest."""
    ref = today or date.today()
    peak_date, peak_yield = find_peak_harvest_day(farms, ref)
    days_until = (peak_date - ref).days
    registered = len(trucks)
    needed = estimate_trucks_needed(peak_yield, trucks)
    gap = max(0, needed - registered)
    on_peak = farms_active_on_day(farms, peak_date)
    alert_due = gap > 0 and 1 <= days_until <= ALERT_DAYS_BEFORE_PEAK

    return TruckGapAnalysis(
        peak_date=peak_date,
        days_until_peak=days_until,
        peak_yield_kg=round(peak_yield, 1),
        registered_trucks=registered,
        trucks_needed=needed,
        truck_gap=gap,
        alert_due=alert_due,
        farms_on_peak=on_peak,
        crop_summary=_crop_summary(farms, on_peak),
    )
