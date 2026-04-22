"""HTTP route modules for the AgentFarm API."""

from fastapi import APIRouter

from . import advisor, data, outcomes, runs, scenario


def get_api_router() -> APIRouter:
    """Return a composite ``APIRouter`` with all sub-routers mounted."""

    router = APIRouter()
    router.include_router(scenario.router)
    router.include_router(runs.router)
    router.include_router(advisor.router)
    router.include_router(outcomes.router)
    router.include_router(data.router)
    return router


__all__ = ["get_api_router"]
