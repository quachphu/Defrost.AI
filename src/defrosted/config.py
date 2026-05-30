"""
All configuration in one place. No hardcoded values anywhere else.
Every secret is read from environment variables — never committed to git.

Usage:
    from defrosted.config import get_settings
    settings = get_settings()  # cached singleton
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    environment: str = "development"     # "development" | "staging" | "production"
    log_level: str = "INFO"

    # Database
    database_url: str                    # postgresql+asyncpg://user:pass@host/db
    database_pool_size: int = 20
    database_max_overflow: int = 40

    # Redis
    redis_url: str                       # redis://host:6379/0

    # AWS
    aws_region: str = "us-east-1"
    s3_bucket_name: str
    s3_documents_prefix: str = "documents/"

    # AI
    anthropic_api_key: str
    langsmith_api_key: str | None = None
    langsmith_project: str = "defrosted-production"

    # Communication
    sendgrid_api_key: str
    outreach_from_email: str = "agent@defrosted.ai"
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str            # E.164 format
    bland_ai_api_key: str

    # Browser automation
    browserbase_api_key: str
    browserbase_project_id: str

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "defrosted"
    temporal_task_queue: str = "rental-search-queue"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached singleton Settings instance.
    @lru_cache ensures we only parse environment variables once per process.
    This is safe because settings are read-only after startup.
    """
    return Settings()  # type: ignore[call-arg]  # values come from env at runtime
