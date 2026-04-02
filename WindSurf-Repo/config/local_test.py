"""Local development configuration for testing."""
import os
from config.development import DevelopmentConfig

class LocalTestConfig(DevelopmentConfig):
    """Local testing configuration with custom ports."""
    
    # Override the port for local testing
    API_PORT = int(os.getenv("API_PORT", "8765"))  # Custom port for testing
    
    # Database - use a separate test database
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./test_byos.db"
    )
    
    # Debug mode for testing
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    
    # Disable some features for testing
    ENABLE_INTRUSION_DETECTION = False  # Disable for easier testing
    ENABLE_RATE_LIMITING = False  # Disable for easier testing
    
    # Test-specific settings
    TEST_MODE = True
    
    @classmethod
    def get_api_url(cls) -> str:
        """Get the full API URL for this configuration."""
        return f"http://localhost:{cls.API_PORT}/api/v1"
