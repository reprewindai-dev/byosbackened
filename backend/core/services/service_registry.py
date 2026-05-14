"""
Service Registry — Central registry for BYOS internal services.

Tracks BYOS's own internal subsystems (AI providers, workspace services,
monitoring, billing, etc.) for health monitoring, routing, and the
Services dashboard.
"""

import logging
import time
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceType(str, Enum):
    AI_PROVIDER = "ai_provider"
    CORE = "core"
    INTEGRATION = "integration"
    MONITORING = "monitoring"
    BILLING = "billing"


class RegisteredService(BaseModel):
    """An internal BYOS service."""

    service_id: str = Field(..., description="Unique service identifier")
    name: str = Field(..., description="Human-readable service name")
    service_type: ServiceType
    base_url: str = Field(default="", description="Base URL or internal path")
    health_endpoint: str = Field(default="/health", description="Health check path")
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[float] = None
    last_healthy: Optional[float] = None
    metadata: dict = Field(default_factory=dict)
    enabled: bool = True


# ─── Default BYOS internal services ──────────────────────────────────────────

DEFAULT_SERVICES: list[dict] = [
    {
        "service_id": "ollama-local",
        "name": "Ollama Local Inference",
        "service_type": ServiceType.AI_PROVIDER,
        "base_url": "http://localhost:11434",
        "health_endpoint": "/api/tags",
        "metadata": {
            "description": "Local LLM inference via Ollama",
            "role": "primary",
            "models": ["llama3", "mistral", "codellama"],
        },
    },
    {
        "service_id": "groq-cloud",
        "name": "Groq Cloud Fallback",
        "service_type": ServiceType.AI_PROVIDER,
        "base_url": "https://api.groq.com",
        "health_endpoint": "/openai/v1/models",
        "metadata": {
            "description": "Cloud LLM fallback via Groq — activates when Ollama circuit opens",
            "role": "fallback",
            "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        },
    },
    {
        "service_id": "circuit-breaker",
        "name": "Provider Circuit Breaker",
        "service_type": ServiceType.CORE,
        "metadata": {
            "description": "Automatic failover between Ollama (primary) and Groq (fallback)",
            "pattern": "circuit-breaker with half-open recovery",
        },
    },
    {
        "service_id": "provider-router",
        "name": "Intelligent Provider Router",
        "service_type": ServiceType.CORE,
        "metadata": {
            "description": "Cost-optimized routing across AI providers",
            "strategies": ["cost_optimized", "quality_optimized", "speed_optimized", "hybrid"],
        },
    },
    {
        "service_id": "workspace-gateway",
        "name": "Workspace Gateway",
        "service_type": ServiceType.CORE,
        "metadata": {
            "description": "Multi-tenant workspace isolation and management",
        },
    },
    {
        "service_id": "billing-engine",
        "name": "Billing & Subscription Engine",
        "service_type": ServiceType.BILLING,
        "metadata": {
            "description": "Stripe-powered billing, subscriptions, and usage metering",
        },
    },
    {
        "service_id": "security-suite",
        "name": "Security Suite",
        "service_type": ServiceType.CORE,
        "metadata": {
            "description": "Content safety, DLP, threat detection, and compliance monitoring",
        },
    },
    {
        "service_id": "monitoring-suite",
        "name": "Monitoring Suite",
        "service_type": ServiceType.MONITORING,
        "metadata": {
            "description": "Platform health, usage metrics, and alerting",
        },
    },
]


class ServiceRegistry:
    """In-memory registry of BYOS internal services."""

    def __init__(self):
        self._services: dict[str, RegisteredService] = {}
        self._boot()

    def _boot(self):
        for svc in DEFAULT_SERVICES:
            self.register(RegisteredService(**svc))

    def register(self, service: RegisteredService) -> RegisteredService:
        self._services[service.service_id] = service
        logger.info("Service registered: %s (%s)", service.service_id, service.name)
        return service

    def deregister(self, service_id: str) -> bool:
        if service_id in self._services:
            del self._services[service_id]
            logger.info("Service deregistered: %s", service_id)
            return True
        return False

    def get(self, service_id: str) -> Optional[RegisteredService]:
        return self._services.get(service_id)

    def list_all(self) -> list[RegisteredService]:
        return list(self._services.values())

    def list_by_type(self, service_type: ServiceType) -> list[RegisteredService]:
        return [s for s in self._services.values() if s.service_type == service_type]

    def list_healthy(self) -> list[RegisteredService]:
        return [
            s for s in self._services.values()
            if s.status in (ServiceStatus.HEALTHY, ServiceStatus.UNKNOWN)
        ]

    def update_health(self, service_id: str, status: ServiceStatus) -> bool:
        svc = self._services.get(service_id)
        if not svc:
            return False
        svc.status = status
        svc.last_health_check = time.time()
        if status == ServiceStatus.HEALTHY:
            svc.last_healthy = time.time()
        return True

    def update_url(self, service_id: str, base_url: str) -> bool:
        svc = self._services.get(service_id)
        if not svc:
            return False
        svc.base_url = base_url
        return True


# Module-level singleton
_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry
