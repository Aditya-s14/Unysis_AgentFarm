"""Route deviation alert persistence via run_logs."""

from __future__ import annotations

from typing import Any

from models.schemas import RouteDeviationAlert
from tools.db import list_run_logs_for_run

DEVIATION_LOG_MESSAGE = "route_deviation_alert"


class TrackingError(Exception):
    """Tracking gateway failure with HTTP status."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def alert_from_detail(detail: dict[str, Any]) -> RouteDeviationAlert:
    return RouteDeviationAlert.model_validate(detail)


async def list_deviation_alerts(run_id: str) -> list[RouteDeviationAlert]:
    rows = await list_run_logs_for_run(run_id)
    by_id: dict[str, RouteDeviationAlert] = {}
    for row in rows:
        if row.message != DEVIATION_LOG_MESSAGE or not row.detail_json:
            continue
        alert = alert_from_detail(dict(row.detail_json))
        by_id[alert.alert_id] = alert
    return sorted(
        by_id.values(),
        key=lambda a: a.created_at or "",
        reverse=True,
    )
