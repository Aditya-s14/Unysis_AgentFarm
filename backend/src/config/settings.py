"""Application settings loaded from environment variables.

Uses ``pydantic-settings`` (Pydantic v2) so every setting is typed, validated
and auto-loaded from ``.env``. Downstream modules should consume configuration
through :func:`get_settings` rather than reading ``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the AgentFarm backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "AgentFarm Optimizer"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])

    # --- Datastores ---
    DATABASE_URL: str = "postgresql+asyncpg://agentfarm:agentfarm@localhost:5432/agentfarm"
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- External APIs ---
    OPENWEATHER_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    OSRM_BASE_URL: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    LANGSMITH_API_KEY: str = ""

    # --- LLM / Agent behaviour ---
    MODEL_NAME: str = "gpt-4.1-mini"
    PLANNING_TEMP: float = 0.0
    ADVISOR_TEMP: float = 0.3

    # --- Optimization ---
    VRP_TIME_LIMIT: int = 30  # seconds
    MAX_RETRIES: int = 2

    # --- Caching ---
    WEATHER_CACHE_TTL: int = 3600  # 1 hour
    DISTANCE_CACHE_TTL: int = 86400  # 24 hours
    ADVISOR_SESSION_TTL: int = 86400  # 24 hours
    ADVISOR_SESSION_MAX_MESSAGES: int = 10


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""

    return Settings()
