"""Weather Agent — fetches forecasts per farm and classifies risk."""

from __future__ import annotations

from typing import Any, Dict

from ..services.weather_service import WeatherService
from .base_agent import BaseAgent


class WeatherAgent(BaseAgent):
    """Populates ``weather_events`` and ``weather_risk_summary`` on the state.

    TODO:
      * call :class:`WeatherService.get_forecast` per farm
      * build ``WeatherEventSchema`` objects (one per farm)
      * derive ``{farm_id: risk_level}`` summary
      * skip network calls if cached forecasts exist in Redis
    """

    def __init__(self, weather_service: WeatherService | None = None) -> None:
        super().__init__(name="weather_agent")
        self._weather = weather_service or WeatherService()

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("weather_agent_start", farms=len(state.get("farms", [])))

        # Placeholder outputs — real implementation iterates farms and calls service.
        state["weather_events"] = state.get("weather_events", [])
        state["weather_risk_summary"] = state.get("weather_risk_summary", {})

        self._append_trace(
            state,
            step="fetch_forecasts",
            data={
                "farms_processed": len(state.get("farms", [])),
                "events_emitted": len(state["weather_events"]),
            },
        )
        return state
