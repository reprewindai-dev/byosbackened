"""
Service Registry — Central registry for all BYOS-connected services.

BYOS is the source of truth. All downstream services (CO2 Router, Cobi Engine,
Runtime DEKES, LockerSphere verticals) register here and receive routing,
auth tokens, and health monitoring.
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
    FRONTEND = "frontend"
    ENGINE = "engine"
    RUNTIME = "runtime"
    PROXY = "proxy"
    VERTICAL = "vertical"


class RegisteredService(BaseModel):
    """A service registered with the BYOS source-of-truth."""

    service_id: str = Field(..., description="Unique service identifier")
    name: str = Field(..., description="Human-readable service name")
    service_type: ServiceType
    base_url: str = Field(..., description="Base URL for the service")
    health_endpoint: str = Field(default="/health", description="Health check path")
    api_prefix: str = Field(default="/api/v1", description="API prefix for the service")
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[float] = None
    last_healthy: Optional[float] = None
    metadata: dict = Field(default_factory=dict)
    enabled: bool = True
    requires_auth: bool = True


# ─── Default service definitions ──────────────────────────────────────────────

DEFAULT_SERVICES: list[dict] = [
    {
        "service_id": "co2router-site",
        "name": "CO2 Router Site",
        "service_type": ServiceType.FRONTEND,
        "base_url": "https://co2router.com",
        "health_endpoint": "/api/health",
        "api_prefix": "/api",
        "metadata": {
            "description": "Public-facing marketing site and live demo for CO2 Router",
            "repo": "reprewindai-dev/co2router-site",
            "stack": "Next.js 14, TypeScript, Tailwind CSS",
        },
    },
    {
        "service_id": "ecobe-engine",
        "name": "Cobi Engine (ecobe-engineclaude)",
        "service_type": ServiceType.ENGINE,
        "base_url": "https://co2router.tech",
        "health_endpoint": "/health",
        "api_prefix": "/api/v1",
        "metadata": {
            "description": "CO2 Router deterministic decision engine — routing, replay, proof, adapters",
            "repo": "reprewindai-dev/ecobe-engineclaude",
            "stack": "TypeScript, Express, Prisma, Redis",
        },
    },
    {
        "service_id": "ecobe-mvp",
        "name": "Cobi MVP Runtime Proxy",
        "service_type": ServiceType.PROXY,
        "base_url": "https://ecobe-mvp-5mjgu.ondigitalocean.app",
        "health_endpoint": "/health",
        "api_prefix": "",
        "metadata": {
            "description": "Decision proxy — accepts demo traffic and forwards to engine",
            "repo": "reprewindai-dev/ecobe-mvp",
            "stack": "Next.js, Express, Prisma",
        },
    },
    {
        "service_id": "runtime-dekes",
        "name": "DEKES Signed Runtime",
        "service_type": ServiceType.RUNTIME,
        "base_url": "",
        "health_endpoint": "/api/health",
        "api_prefix": "/api",
        "metadata": {
            "description": "Lead intelligence and buyer qualification runtime",
            "repo": "reprewindai-dev/runtimedekes",
            "stack": "Next.js, Prisma, PostgreSQL, Stripe",
        },
    },
    {
        "service_id": "lockersphere-security",
        "name": "LockerSphere Security",
        "service_type": ServiceType.VERTICAL,
        "base_url": "",
        "health_endpoint": "/health",
        "api_prefix": "/api/v1",
        "metadata": {
            "description": "AI-powered security platform — the original LockerSphere",
            "repo": "reprewindai-dev/lockerphycer",
            "vertical": "security",
        },
    },
    {
        "service_id": "lockersphere-hospital",
        "name": "LockerSphere Hospital",
        "service_type": ServiceType.VERTICAL,
        "base_url": "",
        "health_endpoint": "/health",
        "api_prefix": "/api/v1",
        "metadata": {
            "description": "HIPAA-grade hospital safety, HL7/FHIR, global compliance",
            "vertical": "hospital",
        },
    },
    {
        "service_id": "lockersphere-bank",
        "name": "LockerSphere Bank",
        "service_type": ServiceType.VERTICAL,
        "base_url": "",
        "health_endpoint": "/health",
        "api_prefix": "/api/v1",
        "metadata": {
            "description": "PCI-DSS, SOX, anti-fraud, transaction monitoring",
            "vertical": "bank",
        },
    },
    {
        "service_id": "lockersphere-insurance",
        "name": "LockerSphere Insurance",
        "service_type": ServiceType.VERTICAL,
        "base_url": "",
        "health_endpoint": "/health",
        "api_prefix": "/api/v1",
        "metadata": {
            "description": "Claims processing, actuarial AI, underwriting",
            "vertical": "insurance",
        },
    },
    {
        "service_id": "lockersphere-content",
        "name": "LockerSphere Content Creator",
        "service_type": ServiceType.VERTICAL,
        "base_url": "",
        "health_endpoint": "/health",
        "api_prefix": "/api/v1",
        "metadata": {
            "description": "Content moderation, copyright protection, monetization",
            "vertical": "content_creator",
        },
    },
    {
        "service_id": "lockersphere-general",
        "name": "LockerSphere General",
        "service_type": ServiceType.VERTICAL,
        "base_url": "",
        "health_endpoint": "/health",
        "api_prefix": "/api/v1",
        "metadata": {
            "description": "General-purpose white-label — works out of the box",
            "vertical": "general",
        },
    },
]


class ServiceRegistry:
    """In-memory service registry. BYOS is the source of truth."""

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
