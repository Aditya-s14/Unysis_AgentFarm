"""Application settings (Pydantic Settings)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for AgentFarm Optimizer."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    OPENWEATHER_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"
    OSRM_URL: str = ""
    DATABASE_URL: str = (
        "postgresql+asyncpg://agentfarm:agentfarm@localhost:5432/agentfarm"
    )
    REDIS_URL: str = "redis://localhost:6379/0"

    # Directory containing sample_*.csv (repo root `data/`). In Docker set e.g. /seed-data.
    DATA_SEED_DIR: str = ""

    vrp_time_limit: int = 30
    max_retries: int = 2
    planning_temp: float = 0.0
    advisor_temp: float = 0.3
    # Max straight-line distance (km) a farm may be matched with a mandi.
    # Reflects how India's APMC system actually works at the farmer layer:
    # produce moves to the nearest regional mandi (typically <100 km), with
    # cross-state movement happening at the wholesaler tier later. 150 km
    # gives some slack for cross-border districts.
    max_farm_mandi_km: float = 150.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
