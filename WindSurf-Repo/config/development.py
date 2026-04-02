"""Development environment configuration."""
import os
from typing import Optional

class DevelopmentConfig:
    """Development configuration settings."""
    
    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./dev.db"
    )
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # Application
    APP_NAME = "BYOS Backend"
    VERSION = "1.0.0"
    DEBUG = True
    
    # Logging
    LOG_LEVEL = "DEBUG"
    
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
        """Get database URL for this environment."""
        return cls.DATABASE_URL
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if this is production environment."""
        return False
