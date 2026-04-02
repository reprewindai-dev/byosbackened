"""Configuration and environment settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # App
    app_name: str = "BYOS AI Backend"
    app_version: str = "0.1.0"
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"  # Default to True for local dev
    api_prefix: str = "/api/v1"
    data_dir: str = os.getenv("DATA_DIR", "./data")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./local.db")
    database_echo: bool = False

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

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

    # Advanced Security Features
    enable_mfa: bool = True  # Enable Multi-Factor Authentication
    password_min_length: int = 12  # Minimum password length
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True
    max_failed_login_attempts: int = 5  # Lock account after N failed attempts
    account_lockout_duration_minutes: int = 30  # Lock account for N minutes
    enable_intrusion_detection: bool = True  # Enable IDS
    enable_security_monitoring: bool = True  # Enable security monitoring
    enable_vulnerability_scanning: bool = True  # Enable vulnerability scanning

    # AI Citizenship
    ai_citizenship_secret: str = os.getenv("AI_CITIZENSHIP_SECRET", "default_secret")
    # AI Providers
    # Hugging Face
    huggingface_api_key: str = ""
    huggingface_model_chat: str = "mistralai/Mistral-7B-Instruct-v0.1"
    huggingface_model_embed: str = "sentence-transformers/all-MiniLM-L6-v2"
    huggingface_model_whisper: str = "openai/whisper-large-v3"
    huggingface_model_blip: str = "Salesforce/blip-image-captioning-large"
    huggingface_model_ner: str = "dslim/bert-base-NER"
    huggingface_model_musicgen: str = "facebook/musicgen-small"
    huggingface_model_summarize: str = "facebook/bart-large-cnn"
    huggingface_model_sentiment: str = "distilbert-base-uncased-finetuned-sst-2-english"
    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""  # Optional - system works without webhooks
    frontend_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8765"

    # SERP API
    serpapi_key: str = ""

    # OpenAI (optional, only when valuable)
    openai_api_key: str = ""
    openai_model_chat: str = "gpt-4o-mini"
    openai_model_whisper: str = "whisper-1"

    # Local AI (self-hosted)
    local_whisper_url: str = ""  # e.g., "http://whisper:8000"
    local_llm_url: str = ""  # e.g., "http://llm:8000"

    # Worker
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # CORS
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Privacy/Anonymity
    use_proxy: bool = False
    proxy_url: str = ""  # e.g., "http://proxy:port" or "socks5://proxy:port"
    rotate_user_agents: bool = True
    random_referers: bool = True
    log_user_ips: bool = False  # Don't log IPs for privacy
    log_user_agents: bool = False  # Don't log user agents
    mobile_mode: bool = True  # Use mobile user agents (harder to trace)
    location_randomization: bool = True  # Randomize location headers
    session_rotation_minutes: int = (
        60  # Rotate session every N minutes (prevents long-term tracking)
    )
    proxy_rotation_minutes: int = 15  # Rotate proxy every N minutes

    # Bitcoin Payments (Coinbase Commerce)
    coinbase_commerce_api_key: str = ""  # Get from https://commerce.coinbase.com
    coinbase_commerce_webhook_secret: str = ""  # Webhook secret from Coinbase Commerce
    bitcoin_wallet_address: str = ""  # Your Bitcoin wallet address (backup)
    bitcoin_network: str = "mainnet"  # "mainnet" or "testnet"

    # AI Citizenship Service
    ai_citizenship_secret: str = "default_secret_change_me"  # Secret key for certificate signing
    data_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")  # Data directory path

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
