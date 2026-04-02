"""Configuration and environment settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # App
    app_name: str = "BYOS AI Backend"
    app_version: str = "0.1.0"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql://postgres:postgres@postgres:5432/byos_ai"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # S3/MinIO
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "byos-ai"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    # Security
    secret_key: str = "change-me-in-production-use-env-var"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    encryption_key: str = ""  # For field encryption, defaults to secret_key if not set

    # ── LLM — Local Ollama (primary, no external fallback) ──────────────────────
    llm_base_url: str = "http://host.docker.internal:11434"
    llm_model_default: str = "llama3.2:1b"
    llm_fallback: str = "off"   # "off" = hard fail; never route to external providers
    llm_timeout_seconds: int = 60
    llm_max_tokens: int = 2048

    # SERP API (optional, non-AI)
    serpapi_key: str = ""

    # Worker
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # CORS
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""

    # MFA / Auth security
    max_failed_login_attempts: int = 10
    account_lockout_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Observability
    sentry_dsn: str = ""
    log_format: str = "json"
    metrics_enabled: bool = True
    prometheus_port: int = 9090

    # Content safety
    content_filtering_enabled: bool = True
    age_verification_required: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
