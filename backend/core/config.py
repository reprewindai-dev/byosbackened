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
    s3_backup_bucket: str = "veklom-db-backups"

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"

    # Security
    secret_key: str = "change-me-in-production-use-env-var"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    encryption_key: str = ""  # For field encryption, defaults to secret_key if not set

    # ?????? LLM ??? Local Ollama (primary, no external fallback) ??????????????????????????????????????????????????????????????????
    llm_base_url: str = "http://host.docker.internal:11434"
    llm_model_default: str = "qwen2.5:3b"
    llm_fallback: str = "groq"  # "off" | "groq" ??? groq enables self-healing fallback
    llm_timeout_seconds: int = 60
    llm_max_tokens: int = 2048

    # ?????? Groq fallback (self-healing circuit breaker) ???????????????????????????????????????????????????????????????????????????
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"  # fast model for fallback
    groq_model_fast: str = "llama-3.1-8b-instant"
    groq_model_smart: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Circuit breaker ??? opens after N failures, resets after cooldown_seconds
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_cooldown_seconds: int = 60

    # ?????? Conversation memory ?????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
    memory_ttl_seconds: int = 86400    # 24h default per conversation
    memory_max_messages: int = 20      # max messages kept in context window

    # ?????? External AI Providers (optional, for routing diversity) ???????????????????????????????????????
    openai_api_key: str = ""  # OpenAI API key - used when OpenAI provider selected
    openai_model_chat: str = "gpt-4o-mini"  # Default chat model
    openai_model_whisper: str = "whisper-1"  # Default STT model
    
    huggingface_api_key: str = ""  # HuggingFace API key - free tier available
    huggingface_model_chat: str = "mistralai/Mistral-7B-Instruct-v0.1"
    huggingface_model_embed: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # SERP API (optional, non-AI)
    serpapi_key: str = ""

    # Worker
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # CORS ??? tighten in production via CORS_ORIGINS env var
    cors_origins: list[str] = [
        "https://veklom.com",
        "https://www.veklom.com",
        "https://veklom.dev",
        "https://www.veklom.dev",
        "https://app.veklom.dev",
        "https://api.veklom.dev",
        "https://api.veklom.com",
        "http://localhost:3000",
        "http://localhost:3458",
        "http://localhost:3459",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    cors_allow_headers: list[str] = ["Authorization", "Content-Type", "X-API-Key", "X-Request-ID", "stripe-signature"]

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""

    # License gate
    license_enforcement_enabled: bool = False
    license_verify_url: str = "https://license.veklom.com/verify"
    license_verify_backup_url: str = "https://license2.veklom.com/verify"
    license_key: str = ""
    license_admin_token: str = ""
    license_cache_grace_hours: int = 48
    license_grace_hours: int = 72
    license_revalidation_seconds: int = 900
    license_cache_path: str = ""
    license_public_key: str = ""
    license_public_key_path: str = "license_public_key.pem"
    license_heartbeat_url: str = "https://license.veklom.com/heartbeat"
    license_heartbeat_backup_url: str = "https://license2.veklom.com/heartbeat"
    license_issue_url: str = "https://license.veklom.com/issue"
    license_issue_backup_url: str = "https://license2.veklom.com/issue"
    package_name: str = "veklom-backend"
    package_version: str = "0.1.0"
    package_manifest_enforcement_enabled: bool = False
    buyer_download_base_url: str = ""
    buyer_download_version: str = ""

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "https://veklom.com/auth/github/callback"
    marketplace_admin_emails: list[str] = ["veklomdev@hotmail.com"]

    # MFA / Auth security
    max_failed_login_attempts: int = 10
    account_lockout_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Observability
    sentry_dsn: str = ""
    log_format: str = "json"
    metrics_enabled: bool = True
    prometheus_port: int = 9090

    # SMTP / customer onboarding email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    mail_from: str = ""
    mail_reply_to: str = ""

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
