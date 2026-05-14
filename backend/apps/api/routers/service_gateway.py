"""
Service Gateway — BYOS source-of-truth API for managing connected services.

Exposes endpoints for service registration, health monitoring, routing
configuration, and frontend consumption. All downstream services
(CO2 Router, Cobi Engine, Runtime DEKES, LockerSphere verticals)
are registered and managed through this gateway.
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
    service_type: str = "frontend"
    base_url: str
    health_endpoint: str = "/health"
    api_prefix: str = "/api/v1"
    metadata: dict = Field(default_factory=dict)
    requires_auth: bool = True


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
    """List all registered services. Optionally filter by type."""
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
    """Get details for a specific registered service."""
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
    """Register a new service with the BYOS source-of-truth."""
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
        api_prefix=request.api_prefix,
        metadata=request.metadata,
        requires_auth=request.requires_auth,
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
    """Update a registered service's configuration."""
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
    """Receive a health report from a downstream service."""
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
    """
    Returns the full service topology — how BYOS wires to all
    downstream frontends, engines, runtimes, and verticals.
    """
    registry = get_service_registry()
    all_services = registry.list_all()

    topology = {
        "source_of_truth": "byos-backend",
        "version": "1.0.0",
        "layers": {
            "frontends": [],
            "engines": [],
            "runtimes": [],
            "proxies": [],
            "verticals": [],
        },
        "wiring": [],
        "timestamp": time.time(),
    }

    layer_map = {
        ServiceType.FRONTEND: "frontends",
        ServiceType.ENGINE: "engines",
        ServiceType.RUNTIME: "runtimes",
        ServiceType.PROXY: "proxies",
        ServiceType.VERTICAL: "verticals",
    }

    for svc in all_services:
        layer = layer_map.get(svc.service_type, "frontends")
        topology["layers"][layer].append({
            "id": svc.service_id,
            "name": svc.name,
            "url": svc.base_url,
            "status": svc.status.value,
            "enabled": svc.enabled,
        })

    # Wiring: BYOS → all services
    topology["wiring"] = [
        {
            "from": "byos-backend",
            "to": "co2router-site",
            "protocol": "HTTPS",
            "description": "BYOS serves as auth/billing source for CO2 Router frontend",
        },
        {
            "from": "co2router-site",
            "to": "ecobe-mvp",
            "protocol": "HTTPS",
            "description": "CO2 Router site proxies demo decisions through ecobe-mvp",
        },
        {
            "from": "ecobe-mvp",
            "to": "ecobe-engine",
            "protocol": "HTTPS",
            "description": "ecobe-mvp forwards to the canonical engine for real decisions",
        },
        {
            "from": "byos-backend",
            "to": "runtime-dekes",
            "protocol": "HTTPS",
            "description": "BYOS provides auth, billing, and quota enforcement for DEKES",
        },
        {
            "from": "byos-backend",
            "to": "lockersphere-*",
            "protocol": "HTTPS",
            "description": "BYOS provides shared auth/billing for all LockerSphere verticals",
        },
    ]

    return topology


@router.get("/providers")
async def list_providers(
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    List all provider routes for the frontend routing panel.
    Combines LLM providers with service providers.
    """
    registry = get_service_registry()
    engines = registry.list_by_type(ServiceType.ENGINE)
    proxies = registry.list_by_type(ServiceType.PROXY)
    runtimes = registry.list_by_type(ServiceType.RUNTIME)

    providers = []
    for idx, svc in enumerate(engines + proxies + runtimes):
        providers.append({
            "id": svc.service_id,
            "name": svc.name,
            "provider": svc.service_type.value,
            "model": svc.metadata.get("stack", "unknown"),
            "priority": idx + 1,
            "enabled": svc.enabled,
            "latency_p50_ms": 0,
            "latency_p99_ms": 0,
            "error_rate_pct": 0.0,
            "circuit_state": "closed" if svc.status != ServiceStatus.UNHEALTHY else "open",
            "last_failure_at": None,
            "cost_per_1k_tokens_usd": 0.0,
        })

    return providers


@router.get("/circuit-breaker/status")
async def circuit_breaker_status(
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Circuit breaker status for all registered services.
    Used by the frontend routing panel.
    """
    registry = get_service_registry()
    all_services = registry.list_all()

    statuses = []
    for svc in all_services:
        if svc.service_type in (ServiceType.ENGINE, ServiceType.PROXY, ServiceType.RUNTIME):
            statuses.append({
                "provider": svc.service_id,
                "state": "closed" if svc.status != ServiceStatus.UNHEALTHY else "open",
                "failure_count": 0,
                "success_count": 0,
                "last_state_change_at": time.time(),
                "next_retry_at": None,
            })

    return statuses
