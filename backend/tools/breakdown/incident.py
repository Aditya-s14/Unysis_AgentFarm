"""Breakdown incident persistence and lookup via run_logs."""

from __future__ import annotations

from typing import Any

from models.schemas import BreakdownIncident
from tools.db import list_run_logs_for_run

INCIDENT_LOG_MESSAGE = "breakdown_incident"


class BreakdownError(Exception):
    """Breakdown gateway failure with HTTP status."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def incident_from_detail(detail: dict[str, Any]) -> BreakdownIncident:
    return BreakdownIncident.model_validate(detail)


async def list_incidents(run_id: str) -> list[BreakdownIncident]:
    """Return breakdown incidents for a run (latest record per incident_id)."""
    rows = await list_run_logs_for_run(run_id)
    by_id: dict[str, BreakdownIncident] = {}
    for row in rows:
        if row.message != INCIDENT_LOG_MESSAGE or not row.detail_json:
            continue
        incident = incident_from_detail(dict(row.detail_json))
        by_id[incident.incident_id] = incident
    return list(by_id.values())


async def get_incident(run_id: str, incident_id: str) -> BreakdownIncident | None:
    for incident in await list_incidents(run_id):
        if incident.incident_id == incident_id:
            return incident
    return None


def broken_truck_ids(incidents: list[BreakdownIncident]) -> set[str]:
    """Trucks reported broken (any status except failed without replan)."""
    return {
        inc.truck_id
        for inc in incidents
        if inc.status in ("pending_approval", "approved")
    }
