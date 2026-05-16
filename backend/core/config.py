"""Configuration and environment settings."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from functools import lru_cache


def _default_ollama_base_url() -> str:
    """Pick a sane Ollama default for local Windows and Dockerized runs."""
    if os.getenv("LLM_BASE_URL"):
        return os.getenv("LLM_BASE_URL", "").rstrip("/") or "http://127.0.0.1:11434"

    inside_docker = Path("/.dockerenv").exists() or os.getenv("DOCKER_CONTAINER") == "true"
    if inside_docker:
        return "http://host.docker.internal:11434"
    return "http://127.0.0.1:11434"


def _normalize_ollama_base_url(value: str) -> str:
    """Keep local Windows on localhost, preserve explicit production URLs."""
    raw = (value or "").strip().rstrip("/")
    if not raw:
        return _default_ollama_base_url()

    inside_docker = Path("/.dockerenv").exists() or os.getenv("DOCKER_CONTAINER") == "true"
    if not inside_docker and "host.docker.internal" in raw:
        return "http://127.0.0.1:11434"
    return raw


def _normalize_provider_base_url(value: str) -> str:
    """Normalize OpenAI-compatible provider/gateway base URLs."""
    return (value or "").strip().rstrip("/")


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

    # Upstash QStash - optional durable HTTP job dispatch.
    qstash_url: str = "https://qstash-us-east-1.upstash.io"
    qstash_token: str = ""
    qstash_current_signing_key: str = ""
    qstash_next_signing_key: str = ""
    qstash_callback_base_url: str = ""
    upstash_workflow_url: str = ""

    # Upstash Redis REST fallback - used when TCP Redis is unavailable.
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""

    # Upstash Search - optional governed evidence/search index.
    upstash_search_rest_url: str = ""
    upstash_search_rest_token: str = ""
    upstash_search_index: str = "default"
    upstash_search_timeout_seconds: float = 2.0

    # S3/MinIO
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "byos-ai"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    s3_backup_bucket: str = "backend-db-backups"

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"

    # Security
    secret_key: str = "change-me-in-production-use-env-var"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    encryption_key: str = ""  # For field encryption, defaults to secret_key if not set

    # â”€â”€ LLM â€” Local Ollama (primary, no external fallback) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    llm_base_url: str = _default_ollama_base_url()
    llm_model_default: str = "qwen2.5:1.5b"
    llm_fallback: str = "groq"  # "off" | "groq" â€” groq enables self-healing fallback
    llm_timeout_seconds: int = 60
    llm_latency_budget_seconds: float = 2.5
    llm_on_prem_timeout_seconds: float = 20.0
    llm_keep_alive: str = "30m"
    llm_max_tokens: int = 2048

    # â”€â”€ Groq fallback (self-healing circuit breaker) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"  # fast model for fallback
    groq_model_fast: str = "llama-3.1-8b-instant"
    groq_model_smart: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_timeout_seconds: float = 10.0

    # Circuit breaker â€” opens after N failures, resets after cooldown_seconds
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_cooldown_seconds: int = 60

    # â”€â”€ Conversation memory â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    memory_ttl_seconds: int = 86400    # 24h default per conversation
    memory_max_messages: int = 20      # max messages kept in context window

    # â”€â”€ External AI Providers (optional, for routing diversity) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    openai_api_key: str = ""  # OpenAI API key - used when OpenAI provider selected
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model_chat: str = "gpt-4o-mini"  # Default chat model
    openai_model_whisper: str = "whisper-1"  # Default STT model
    ai_integrations_openai_base_url: str = ""
    ai_integrations_openai_api_key: str = ""
    ai_integrations_gemini_base_url: str = ""
    ai_integrations_gemini_api_key: str = ""

    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    gemini_model_chat: str = "gemini-2.5-pro"
    
    huggingface_api_key: str = ""  # HuggingFace API key - free tier available
    huggingface_model_chat: str = "mistralai/Mistral-7B-Instruct-v0.1"
    huggingface_model_embed: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # SERP API (optional, non-AI)
    serpapi_key: str = ""
    resend_api_key: str = ""
    resend_webhook_secret: str = ""
    resend_from_vendor: str = "Marketplace <noreply@example.com>"
    resend_from_compliance: str = "Compliance <compliance@example.com>"
    resend_vendor_audience_id: str = ""
    resend_regulated_audience_id: str = ""

    # Worker
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # CORS â€” tighten in production via CORS_ORIGINS env var
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3458",
        "http://localhost:3459",
        "https://veklom.com",
        "https://www.veklom.com",
        "https://veklom.dev",
        "https://www.veklom.dev",
        "https://api.veklom.com",
        "https://api.veklom.dev",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    cors_allow_headers: list[str] = ["Authorization", "Content-Type", "X-API-Key", "X-Request-ID", "stripe-signature"]

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_api_version: str = "2026-04-22.dahlia"

    # License gate
    license_enforcement_enabled: bool = False
    license_verify_url: str = ""
    license_verify_backup_url: str = ""
    license_key: str = ""
    license_admin_token: str = ""
    license_cache_grace_hours: int = 48
    license_grace_hours: int = 72
    license_revalidation_seconds: int = 900
    license_cache_path: str = ""
    license_public_key: str = ""
    license_public_key_path: str = "license_public_key.pem"
    license_heartbeat_url: str = ""
    license_heartbeat_backup_url: str = ""
    license_issue_url: str = ""
    license_issue_backup_url: str = ""
    package_name: str = "byos-ai-backend"
    package_version: str = "0.1.0"
    package_manifest_enforcement_enabled: bool = False
    buyer_download_base_url: str = ""
    buyer_download_version: str = ""

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:3000/auth/github/callback"
    marketplace_admin_emails: list[str] = []

    # MFA / Auth security
    max_failed_login_attempts: int = 10
    account_lockout_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Observability
    sentry_dsn: str = ""
    sentry_environment: str = ""
    sentry_release: str = ""
    sentry_send_default_pii: bool = False
    sentry_enable_logs: bool = True
    sentry_traces_sample_rate: float = 0.1
    sentry_profile_session_sample_rate: float = 0.0
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

    @model_validator(mode="after")
    def _resolve_ollama_url(self) -> "Settings":
        self.llm_base_url = _normalize_ollama_base_url(self.llm_base_url)
        if self.ai_integrations_openai_base_url:
            self.openai_base_url = self.ai_integrations_openai_base_url
        if self.ai_integrations_openai_api_key and not self.openai_api_key:
            self.openai_api_key = self.ai_integrations_openai_api_key
        if self.ai_integrations_gemini_base_url:
            self.gemini_base_url = self.ai_integrations_gemini_base_url
        if self.ai_integrations_gemini_api_key and not self.gemini_api_key:
            self.gemini_api_key = self.ai_integrations_gemini_api_key
        self.openai_base_url = _normalize_provider_base_url(self.openai_base_url)
        self.gemini_base_url = _normalize_provider_base_url(self.gemini_base_url)
        self.qstash_url = _normalize_provider_base_url(self.qstash_url)
        self.qstash_callback_base_url = _normalize_provider_base_url(
            self.qstash_callback_base_url or os.getenv("BACKEND_URL", "")
        )
        self.upstash_workflow_url = _normalize_provider_base_url(
            self.upstash_workflow_url or os.getenv("UPSTASH_WORKFLOW_URL", "")
        )
        return self


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
