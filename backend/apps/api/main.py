"""FastAPI application - BYOS AI + Security Suite."""
import json
import logging
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from core.config import get_settings
from core.auth import get_current_workspace
from db.session import SessionLocal
from core.logging import setup_logging
from core.observability.sentry import configure_sentry
from core.security.zero_trust import ZeroTrustMiddleware
from apps.api.middleware.metrics import MetricsMiddleware
from apps.api.middleware.intelligent_routing import IntelligentRoutingMiddleware
from apps.api.middleware.edge_routing import EdgeRoutingMiddleware
from apps.api.middleware.budget_check import BudgetCheckMiddleware
from apps.api.middleware.rate_limit import RateLimitMiddleware
from apps.api.middleware.entitlement_check import EntitlementCheckMiddleware
from apps.api.middleware.locker_security_integration import LockerSecurityMiddleware
from apps.api.middleware.request_security import RequestSecurityMiddleware
from apps.api.middleware.performance import PerformanceMiddleware, GzipMiddleware
from apps.api.middleware.fast_path import FastPathMiddleware
from apps.api.routers import (
    upload,
    transcribe,
    extract,
    export,
    search,
    job,
    privacy,
    cost,
    routing,
    budget,
    audit,
    billing,
    metrics,
    plugins,
    explainability,
    compliance,
    autonomous,
    insights,
    suggestions,
)
from apps.api.routers.auth import router as auth_router
from apps.api.routers.security_suite import router as security_router
from apps.api.routers.monitoring_suite import router as monitoring_router
from apps.api.routers.admin import router as admin_router
from apps.api.routers.subscriptions import router as subscriptions_router
from apps.api.routers.content_safety import router as content_safety_router
from apps.api.routers.exec_router import router as exec_router
from apps.api.routers.demo_pipeline import router as demo_pipeline_router
from apps.api.routers.locker_security import router as locker_security_router
from apps.api.routers.locker_monitoring import router as locker_monitoring_router
from apps.api.routers.locker_users import router as locker_users_router
from apps.api.routers.kill_switch import router as kill_switch_router
from apps.api.routers.token_wallet import router as token_wallet_router
from apps.api.routers.support_bot import router as support_bot_router
from apps.api.routers.ai import router as ai_router
from apps.api.routers.workspace import router as workspace_router
from apps.api.routers.workspace import public_router as public_status_router
from apps.api.routers.marketplace_v1 import router as marketplace_v1_router
from apps.api.routers.edge_canary import router as edge_canary_router
from apps.api.routers.resend_webhooks import router as resend_webhooks_router
from apps.api.routers.qstash_webhooks import router as qstash_webhooks_router
from apps.api.routers.telemetry import router as telemetry_router
from apps.api.routers.pipelines import router as pipelines_router
from apps.api.routers.deployments import router as deployments_router
from apps.api.routers.marketplace_automation import router as marketplace_automation_router
from apps.api.routers.platform_pulse import router as platform_pulse_router
from apps.api.routers.internal_operators import router as internal_operators_router
from apps.api.routers.internal_uacp import router as internal_uacp_router
from apps.api.routers.subscriptions import stripe_webhook as subscriptions_webhook_handler
from apps.api.workflows import register_workflows
from edge.routers.edge_ingest import router as edge_ingest_router
from edge.routers.mqtt import router as edge_mqtt_router
from edge.routers.control import router as edge_control_router
from edge.routers.modbus import router as edge_modbus_router
from edge.routers.snmp import router as edge_snmp_router
from license.middleware import LicenseGateMiddleware, bootstrap_license_check
from herald.scheduler import start_herald_scheduler, stop_herald_scheduler
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
setup_logging()
configure_sentry()

# Initialize providers
from core.providers.init import initialize_providers
initialize_providers()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "BYOS AI + Security Suite - Portable, secure, cost-intelligent AI backend. "
        "No lock-in. Swap hosts in a weekend. Built for agencies, enterprises, and privacy-first platforms."
    ),
    openapi_url=None,  # Disabled - using protected custom route
    docs_url=None,  # Disabled - using protected custom route
    redoc_url=None,  # Disabled - using protected custom route
    # Security hardening
    max_request_size=10 * 1024 * 1024,  # 10MB limit per request
)

register_workflows(app)


@app.on_event("startup")
async def startup_validation():
    """Validate production configuration on startup."""
    from core.security.secrets_validation import validate_production_config
    from db.session import Base, engine
    import db.models  # noqa: F401 - ensure model metadata is registered before create_all
    try:
        result = validate_production_config()
        logger.info("Production configuration validated successfully")
        if result.get("warnings"):
            logger.warning(f"Configuration warnings: {len(result['warnings'])}")
        if settings.package_manifest_enforcement_enabled:
            from pathlib import Path
            from license.package_guard import verify_package_manifest

            verify_package_manifest(Path.cwd())
            logger.info("Package manifest integrity check completed")
        if settings.license_enforcement_enabled:
            await bootstrap_license_check()
        # Safety net: ensure core tables exist even if migrations were missed.
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema presence check completed")
        start_herald_scheduler()
    except ValueError as e:
        logger.critical(f"PRODUCTION CONFIGURATION INVALID: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_scheduler():
    """Stop background schedulers cleanly."""
    stop_herald_scheduler()


# Middleware stack (outermost = first to run)
# 1. LockerPhycer Security (IDS, rate limiting, security headers) - First line of defense
app.add_middleware(LockerSecurityMiddleware)
# 2. Request security (request ID, IP blocking, brute force protection)
app.add_middleware(RequestSecurityMiddleware)
# 3. Rate limiting (Redis-backed)
app.add_middleware(RateLimitMiddleware)
# 4. Zero-trust authentication
app.add_middleware(ZeroTrustMiddleware)
app.add_middleware(LicenseGateMiddleware)
app.add_middleware(EntitlementCheckMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(IntelligentRoutingMiddleware)
app.add_middleware(EdgeRoutingMiddleware)
app.add_middleware(BudgetCheckMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
# Performance optimization layer (for 777ms latency target)
app.add_middleware(GzipMiddleware)  # Compress responses > 1KB
app.add_middleware(PerformanceMiddleware)  # Caching + keep-alive

# OUTERMOST: pure-ASGI fast path for hot public endpoints.
# Bypasses the entire middleware chain for /health, /status, /, docs, openapi.json.
# Last add_middleware call = first executed.
app.add_middleware(FastPathMiddleware)

# Core AI + Cost Intelligence routers
app.include_router(upload.router, prefix=settings.api_prefix)
app.include_router(transcribe.router, prefix=settings.api_prefix)
app.include_router(extract.router, prefix=settings.api_prefix)
app.include_router(export.router, prefix=settings.api_prefix)
app.include_router(search.router, prefix=settings.api_prefix)
app.include_router(job.router, prefix=settings.api_prefix)
app.include_router(privacy.router, prefix=settings.api_prefix)
app.include_router(cost.router, prefix=settings.api_prefix)
app.include_router(routing.router, prefix=settings.api_prefix)
app.include_router(budget.router, prefix=settings.api_prefix)
app.include_router(audit.router, prefix=settings.api_prefix)
app.include_router(billing.router, prefix=settings.api_prefix)
app.include_router(metrics.router)
app.include_router(plugins.router, prefix=settings.api_prefix)
app.include_router(explainability.router, prefix=settings.api_prefix)
app.include_router(compliance.router, prefix=settings.api_prefix)
app.include_router(autonomous.router, prefix=settings.api_prefix)
app.include_router(insights.router, prefix=settings.api_prefix)
app.include_router(suggestions.router, prefix=settings.api_prefix)

# Security Suite + new platform routers
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(security_router, prefix=settings.api_prefix)
app.include_router(monitoring_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(subscriptions_router, prefix=settings.api_prefix)
app.include_router(content_safety_router, prefix=settings.api_prefix)
app.include_router(kill_switch_router, prefix=settings.api_prefix)

# LockerPhycer Security Routers (now fully integrated into BYOS)
app.include_router(locker_security_router, prefix=settings.api_prefix)
app.include_router(locker_monitoring_router, prefix=settings.api_prefix)
app.include_router(locker_users_router, prefix=settings.api_prefix)
app.include_router(token_wallet_router, prefix=settings.api_prefix)

# AI Support Bot
app.include_router(support_bot_router, prefix=settings.api_prefix)
app.include_router(ai_router, prefix=settings.api_prefix)
app.include_router(workspace_router, prefix=settings.api_prefix)
app.include_router(public_status_router)
app.include_router(marketplace_v1_router, prefix=f"{settings.api_prefix}/marketplace")
app.include_router(edge_ingest_router, prefix=settings.api_prefix)
app.include_router(edge_mqtt_router, prefix=settings.api_prefix)
app.include_router(edge_control_router, prefix=settings.api_prefix)
app.include_router(edge_modbus_router, prefix=settings.api_prefix)
app.include_router(edge_snmp_router, prefix=settings.api_prefix)
app.include_router(edge_canary_router, prefix=settings.api_prefix)
app.include_router(resend_webhooks_router, prefix=settings.api_prefix)
app.include_router(qstash_webhooks_router, prefix=settings.api_prefix)
app.include_router(telemetry_router, prefix=settings.api_prefix)
app.include_router(pipelines_router, prefix=settings.api_prefix)
app.include_router(deployments_router, prefix=settings.api_prefix)
app.include_router(marketplace_automation_router, prefix=settings.api_prefix)
app.include_router(platform_pulse_router, prefix=settings.api_prefix)
app.include_router(internal_operators_router, prefix=settings.api_prefix)
app.include_router(internal_uacp_router, prefix=settings.api_prefix)

# Ollama exec + status (no api_prefix - /v1/exec and /status are top-level)
app.include_router(exec_router)

# Public Veklom Live Pipeline Theater SSE demo (no auth, IP rate-limited)
app.include_router(demo_pipeline_router, prefix=settings.api_prefix)


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": settings.app_version, "service": settings.app_name}


@app.get("/", include_in_schema=False)
async def root():
    """Landing page - serves landing/index.html."""
    html_path = os.path.join(os.path.dirname(__file__), "..", "..", "landing", "index.html")
    html_path = os.path.normpath(html_path)
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": f"{settings.api_prefix}/docs",
    }


@app.post("/api/webhooks/stripe", include_in_schema=False)
async def legacy_stripe_webhook(request: Request):
    """
    Backward-compatible Stripe webhook path.
    Keeps old dashboard endpoint working while canonical endpoint is
    /api/v1/subscriptions/webhook.
    """
    stripe_signature = request.headers.get("stripe-signature")
    db = SessionLocal()
    try:
        return await subscriptions_webhook_handler(
            request=request,
            stripe_signature=stripe_signature,
            db=db,
        )
    finally:
        db.close()


# Protected documentation routes - require auth, but docs viewing is not a billable event.
@app.get(f"{settings.api_prefix}/docs", include_in_schema=False)
async def protected_docs(request: Request, workspace_id: str = Depends(get_current_workspace)):
    """Swagger UI - authenticated operator documentation."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "..", "static", "swagger_ui.html"))


@app.get(f"{settings.api_prefix}/redoc", include_in_schema=False)
async def protected_redoc(request: Request, workspace_id: str = Depends(get_current_workspace)):
    """ReDoc UI - authenticated operator documentation."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "..", "static", "redoc.html"))


@app.get(f"{settings.api_prefix}/openapi.json", include_in_schema=False)
async def protected_openapi(request: Request, workspace_id: str = Depends(get_current_workspace)):
    """OpenAPI schema - requires authentication (free, no tokens)."""
    from fastapi.openapi.utils import get_openapi
    return get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )


# Serve landing + self-serve UI assets from backend/landing.
# Mounted last so API and health routes stay authoritative.
landing_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "landing"))
if os.path.isdir(landing_dir):
    app.mount("/", StaticFiles(directory=landing_dir, html=True), name="landing")
