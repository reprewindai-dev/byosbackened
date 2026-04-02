"""Provider health monitoring."""

from typing import Dict, Optional
from datetime import datetime, timedelta
import httpx
import logging

logger = logging.getLogger(__name__)


class ProviderHealthMonitor:
    """Monitor provider health."""

    def __init__(self):
        self.health_status: Dict[str, Dict] = {}

    async def check_provider_health(self, provider: str, health_url: Optional[str] = None) -> bool:
        """Check if provider is healthy."""
        # Default health checks
        if provider == "huggingface":
            # Check HF API
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get("https://api-inference.huggingface.co/health")
                    healthy = response.status_code == 200
            except Exception:
                healthy = False
        elif provider == "openai":
            # Check OpenAI API
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get("https://api.openai.com/v1/models")
                    healthy = response.status_code == 200
            except Exception:
                healthy = False
        else:
            # Local or custom provider
            if health_url:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(health_url)
                        healthy = response.status_code == 200
                except Exception:
                    healthy = False
            else:
                # Assume healthy if no health URL
                healthy = True

        # Update health status
        self.health_status[provider] = {
            "healthy": healthy,
            "last_checked": datetime.utcnow().isoformat(),
        }

        return healthy

    def get_provider_health(self, provider: str) -> Optional[Dict]:
        """Get provider health status."""
        return self.health_status.get(provider)

    def get_all_health_status(self) -> Dict[str, Dict]:
        """Get health status for all providers."""
        return self.health_status.copy()


# Global health monitor
_health_monitor = ProviderHealthMonitor()


def get_health_monitor() -> ProviderHealthMonitor:
    """Get health monitor."""
    return _health_monitor
