"""Response formatting helpers."""

from __future__ import annotations

from typing import Any, Dict


def format_kpi_delta(baseline: float, optimized: float) -> float:
    """Return percentage improvement of ``optimized`` over ``baseline``."""

    if baseline == 0:
        return 0.0
    return round(((baseline - optimized) / baseline) * 100.0, 2)


def sms_truncate(text: str, limit: int = 160) -> str:
    """Truncate a string to SMS length, appending an ellipsis if cut."""

    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "\u2026"


def traces_summary(traces: list[Dict[str, Any]]) -> Dict[str, int]:
    """Return a count of trace entries per agent."""

    summary: Dict[str, int] = {}
    for entry in traces:
        agent = str(entry.get("agent", "unknown"))
        summary[agent] = summary.get(agent, 0) + 1
    return summary
