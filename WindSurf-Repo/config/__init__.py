"""Configuration management."""
import os
from typing import Dict, Any

class Config:
    """Base configuration class."""
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # Application
    APP_NAME = "BYOS Backend"
    VERSION = "1.0.0"
    DEBUG = False
    DATA_DIR = os.getenv("DATA_DIR", "./data")
    
    # Logging
    LOG_LEVEL = "INFO"
    
    # Monitoring
    ENABLE_METRICS = True
    METRICS_PORT = 8001
    
    # Audit
    AUDIT_LOG_RETENTION_DAYS = 90
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = 1000
    RATE_LIMIT_WINDOW = 3600  # 1 hour
    
    # Intrusion Detection
    INTRUSION_DETECTION_ENABLED = True
    INTRUSION_DETECTION_THRESHOLD = 50
    
    # Features
    ENABLE_SSO = True
    ENABLE_SCIM = True
    ENABLE_AUDIT_LOGGING = True
    ENABLE_RBAC = True
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL for current environment."""
        return cls.DATABASE_URL
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if this is production environment."""
        return False
    
    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        """Get all settings as dictionary."""
        return {
            "database_url": cls.get_database_url(),
            "secret_key": cls.SECRET_KEY,
            "algorithm": cls.ALGORITHM,
            "access_token_expire_minutes": cls.ACCESS_TOKEN_EXPIRE_MINUTES,
            "app_name": cls.APP_NAME,
            "version": cls.VERSION,
            "debug": cls.DEBUG,
            "log_level": cls.LOG_LEVEL,
            "enable_metrics": cls.ENABLE_METRICS,
            "metrics_port": cls.METRICS_PORT,
            "audit_log_retention_days": cls.AUDIT_LOG_RETENTION_DAYS,
            "rate_limit_requests": cls.RATE_LIMIT_REQUESTS,
            "rate_limit_window": cls.RATE_LIMIT_WINDOW,
            "intrusion_detection_enabled": cls.INTRUSION_DETECTION_ENABLED,
            "intrusion_detection_threshold": cls.INTRUSION_DETECTION_THRESHOLD,
            "enable_sso": cls.ENABLE_SSO,
            "enable_scim": cls.ENABLE_SCIM,
            "enable_audit_logging": cls.ENABLE_AUDIT_LOGGING,
            "enable_rbac": cls.ENABLE_RBAC,
        }


def get_config() -> Config:
    """Get configuration based on environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        from config.production import ProductionConfig
        return ProductionConfig
    elif env == "local_test":
        from config.local_test import LocalTestConfig
        return LocalTestConfig
    elif env == "development":
        from config.development import DevelopmentConfig
        return DevelopmentConfig
    else:
        return Config


# Global config instance
settings = get_config()
