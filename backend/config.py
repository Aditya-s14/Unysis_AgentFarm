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
    # OpenRouteService (NOT OpenRouter — different services).
    # Hosted free routing API: https://openrouteservice.org (sign up for key).
    # When set, takes priority over OSRM in the distance chain.
    ORS_API_KEY: str = ""
    DATABASE_URL: str = (
        "postgresql+asyncpg://agentfarm:agentfarm@localhost:5432/agentfarm"
    )
    REDIS_URL: str = "redis://localhost:6379/0"

    # Directory containing sample_*.csv (repo root `data/`). In Docker set e.g. /seed-data.
    DATA_SEED_DIR: str = ""

    # --- Auth (T1) ---
    # HS256 signing secret for JWTs. The default is fine for local dev only;
    # set a real value in .env for anything shared.
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_TTL_HOURS: int = 24
    OTP_TTL_SECONDS: int = 300
    # OTP delivery channel. Only "mock" is implemented (logs the code and
    # echoes it as dev_otp); swap in an SMS provider class without touching
    # the auth flow.
    OTP_PROVIDER: str = "mock"
    # Gate enforcement on the pre-existing API (scenario/runs/advisor) so
    # teammates' work is not blocked mid-sprint. Auth endpoints themselves
    # are always live. Flip to true at integration time.
    AUTH_ENABLED: bool = False

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

    # Farmer notifications (SMS / voice fallback when plan is ready)
    NOTIFY_ENABLED: bool = False
    NOTIFY_PROVIDER: str = "mock"  # mock | msg91 | twilio
    MSG91_AUTH_KEY: str = ""
    MSG91_SENDER_ID: str = "KISANM"
    MSG91_TEMPLATE_ID: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    NOTIFY_SPOILAGE_HOURS: float = 24.0
    NOTIFY_VOICE_SPOILAGE_HOURS: float = 12.0
    NOTIFY_ALL_ROUTED: bool = False
    NOTIFY_REQUIRE_APPROVAL: bool = True
    FIELD_OFFICER_PHONE: str = ""

    # Vehicle breakdown assistance (live incident re-planning)
    BREAKDOWN_ENABLED: bool = True
    BREAKDOWN_AUTO_NOTIFY: bool = False

    # Live truck GPS tracking and route deviation alerts
    TRACKING_ENABLED: bool = True
    TRACKING_INGEST_KEY: str = ""
    DEVIATION_THRESHOLD_KM: float = 3.0
    DEVIATION_DEBOUNCE_SECONDS: int = 120
    DEVIATION_ALERT_COOLDOWN_MIN: int = 15
    TRACKING_POSITION_TTL_HOURS: int = 24
    TRACKING_STALE_MINUTES: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
