"""
Service Gateway — BYOS internal service management API.

Exposes endpoints for managing BYOS's own internal services:
AI providers, workspace services, monitoring, billing, etc.
"""

import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from apps.api.deps import get_current_workspace_id
from core.services.service_registry import (
    get_service_registry,
    RegisteredService,
    ServiceRegistry,
    ServiceStatus,
    ServiceType,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/services", tags=["service-gateway"])


# ─── Request / Response models ────────────────────────────────────────────────


class ServiceRegisterRequest(BaseModel):
    service_id: str
    name: str
    service_type: str = "core"
    base_url: str = ""
    health_endpoint: str = "/health"
    metadata: dict = Field(default_factory=dict)


class ServiceUpdateRequest(BaseModel):
    base_url: Optional[str] = None
    enabled: Optional[bool] = None
    health_endpoint: Optional[str] = None
    metadata: Optional[dict] = None


class ServiceHealthReport(BaseModel):
    service_id: str
    status: str
    details: Optional[dict] = None


class ServiceSummary(BaseModel):
    service_id: str
    name: str
    service_type: str
    base_url: str
    status: str
    enabled: bool
    last_health_check: Optional[float] = None
    metadata: dict = Field(default_factory=dict)


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/registry")
async def list_services(
    service_type: Optional[str] = None,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """List all BYOS internal services. Optionally filter by type."""
    registry = get_service_registry()

    if service_type:
        try:
            st = ServiceType(service_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid service_type. Valid: {[e.value for e in ServiceType]}",
            )
        services = registry.list_by_type(st)
    else:
        services = registry.list_all()

    return {
        "services": [
            ServiceSummary(
                service_id=s.service_id,
                name=s.name,
                service_type=s.service_type.value,
                base_url=s.base_url,
                status=s.status.value,
                enabled=s.enabled,
                last_health_check=s.last_health_check,
                metadata=s.metadata,
            ).model_dump()
            for s in services
        ],
        "total": len(services),
        "source": "byos-backend",
        "timestamp": time.time(),
    }


@router.get("/registry/{service_id}")
async def get_service(
    service_id: str,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Get details for a specific internal service."""
    registry = get_service_registry()
    svc = registry.get(service_id)
    if not svc:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    return svc.model_dump()


@router.post("/register")
async def register_service(
    request: ServiceRegisterRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Register a new internal service."""
    registry = get_service_registry()

    try:
        st = ServiceType(request.service_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service_type. Valid: {[e.value for e in ServiceType]}",
        )

    service = RegisteredService(
        service_id=request.service_id,
        name=request.name,
        service_type=st,
        base_url=request.base_url,
        health_endpoint=request.health_endpoint,
        metadata=request.metadata,
    )

    registered = registry.register(service)
    return {
        "message": "Service registered",
        "service": registered.model_dump(),
    }


@router.patch("/registry/{service_id}")
async def update_service(
    service_id: str,
    request: ServiceUpdateRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Update an internal service's configuration."""
    registry = get_service_registry()
    svc = registry.get(service_id)
    if not svc:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")

    if request.base_url is not None:
        svc.base_url = request.base_url
    if request.enabled is not None:
        svc.enabled = request.enabled
    if request.health_endpoint is not None:
        svc.health_endpoint = request.health_endpoint
    if request.metadata is not None:
        svc.metadata.update(request.metadata)

    return {"message": "Service updated", "service": svc.model_dump()}


@router.delete("/registry/{service_id}")
async def deregister_service(
    service_id: str,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Remove a service from the registry."""
    registry = get_service_registry()
    if not registry.deregister(service_id):
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    return {"message": "Service deregistered", "service_id": service_id}


@router.post("/health-report")
async def report_health(
    report: ServiceHealthReport,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Receive a health report from an internal service."""
    registry = get_service_registry()

    try:
        ss = ServiceStatus(report.status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid: {[e.value for e in ServiceStatus]}",
        )

    if not registry.update_health(report.service_id, ss):
        raise HTTPException(
            status_code=404, detail=f"Service '{report.service_id}' not found"
        )

    return {
        "message": "Health report received",
        "service_id": report.service_id,
        "status": ss.value,
    }


@router.get("/topology")
async def service_topology(
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Returns the BYOS internal service topology."""
    registry = get_service_registry()
    all_services = registry.list_all()

    topology = {
        "platform": "veklom",
        "version": "1.0.0",
        "layers": {
            "ai_providers": [],
            "core": [],
            "integrations": [],
            "monitoring": [],
            "billing": [],
        },
        "wiring": [],
        "timestamp": time.time(),
    }

    layer_map = {
        ServiceType.AI_PROVIDER: "ai_providers",
        ServiceType.CORE: "core",
        ServiceType.INTEGRATION: "integrations",
        ServiceType.MONITORING: "monitoring",
        ServiceType.BILLING: "billing",
    }

    for svc in all_services:
        layer = layer_map.get(svc.service_type, "core")
        topology["layers"][layer].append({
            "id": svc.service_id,
            "name": svc.name,
            "url": svc.base_url,
            "status": svc.status.value,
            "enabled": svc.enabled,
        })

    # Internal wiring: how BYOS subsystems connect
    topology["wiring"] = [
        {
            "from": "provider-router",
            "to": "ollama-local",
            "protocol": "HTTP",
            "description": "Primary AI inference — local Ollama",
        },
        {
            "from": "provider-router",
            "to": "groq-cloud",
            "protocol": "HTTPS",
            "description": "Fallback AI inference — Groq cloud",
        },
        {
            "from": "circuit-breaker",
            "to": "provider-router",
            "protocol": "internal",
            "description": "Circuit breaker controls failover between providers",
        },
        {
            "from": "workspace-gateway",
            "to": "billing-engine",
            "protocol": "internal",
            "description": "Workspace operations trigger billing metering",
        },
        {
            "from": "workspace-gateway",
            "to": "security-suite",
            "protocol": "internal",
            "description": "All workspace actions pass through security checks",
        },
    ]

    return topology


@router.get("/providers")
async def list_providers(
    workspace_id: str = Depends(get_current_workspace_id),
):
    """List AI provider routes with circuit breaker status."""
    registry = get_service_registry()
    ai_providers = registry.list_by_type(ServiceType.AI_PROVIDER)

    providers = []
    for idx, svc in enumerate(ai_providers):
        providers.append({
            "id": svc.service_id,
            "name": svc.name,
            "role": svc.metadata.get("role", "unknown"),
            "models": svc.metadata.get("models", []),
            "base_url": svc.base_url,
            "priority": idx + 1,
            "enabled": svc.enabled,
            "status": svc.status.value,
            "circuit_state": "closed" if svc.status != ServiceStatus.UNHEALTHY else "open",
        })

    return providers


@router.get("/circuit-breaker/status")
async def circuit_breaker_status(
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Circuit breaker status for AI providers."""
    registry = get_service_registry()
    ai_providers = registry.list_by_type(ServiceType.AI_PROVIDER)

    statuses = []
    for svc in ai_providers:
        statuses.append({
            "provider": svc.service_id,
            "name": svc.name,
            "role": svc.metadata.get("role", "unknown"),
            "state": "closed" if svc.status != ServiceStatus.UNHEALTHY else "open",
            "failure_count": 0,
            "success_count": 0,
            "last_state_change_at": time.time(),
            "next_retry_at": None,
        })

    return statuses
