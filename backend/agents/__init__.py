"""LangGraph-compatible agents for AgentFarm Optimizer.

Pipeline agents (each is ``async def run(state) -> state``):
  weather_agent     — WeatherEvents + risk summary (no LLM)
  demand_agent      — 7-day demand forecast with festival/bias correction (1 LLM call)
  inventory_agent   — at-risk stock ranked by spoilage urgency (1 LLM call)
  logistics_agent   — OR-Tools CVRP route plan (no LLM)
  validator         — 5 rule checks; increments retry_count on failure (no LLM)
  orchestrator_entry / orchestrator_exit — bookend nodes (no LLM)

Decoupled service (NOT a graph node):
  advisor_agent.answer_query(run_id, session_id, question) -> AdvisorResponse
"""

from agents.advisor_agent import answer_query as advisor_answer_query
from agents.demand_agent import run as demand_agent
from agents.inventory_agent import run as inventory_agent
from agents.logistics_agent import run as logistics_agent
from agents.metrics import compute_kpi_delta
from agents.orchestrator import orchestrator_entry, orchestrator_exit
from agents.validator import run as validator
from agents.weather_agent import run as weather_agent

__all__ = [
    "weather_agent",
    "demand_agent",
    "inventory_agent",
    "logistics_agent",
    "validator",
    "orchestrator_entry",
    "orchestrator_exit",
    "advisor_answer_query",
    "compute_kpi_delta",
]
