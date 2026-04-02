"""Production environment configuration."""
import os
from typing import Optional

class ProductionConfig:
    """Production configuration settings."""
    
    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "postgresql://user:password@localhost:5432/byos_prod"
    )
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")  # Required in production
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    
    # Application
    APP_NAME = "BYOS Backend"
    VERSION = "1.0.0"
    DEBUG = False
    
    # Logging
    LOG_LEVEL = "INFO"
    
    # Monitoring
    ENABLE_METRICS = True
    METRICS_PORT = 8001
    
    # Audit
    AUDIT_LOG_RETENTION_DAYS = 365
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = 3600  # 1 hour
    
    # Intrusion Detection
    INTRUSION_DETECTION_ENABLED = True
    INTRUSION_DETECTION_THRESHOLD = 25
    
    # Features
    ENABLE_SSO = True
    ENABLE_SCIM = True
    ENABLE_AUDIT_LOGGING = True
    ENABLE_RBAC = True
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL for this environment."""
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required in production")
        return cls.DATABASE_URL
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if this is production environment."""
        return True
    
    @classmethod
    def validate(cls) -> None:
        """Validate production configuration."""
        required_vars = ["SECRET_KEY", "DATABASE_URL"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        if os.getenv("SECRET_KEY") == "dev-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be changed from default value in production")
