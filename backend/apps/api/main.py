"""FastAPI application — BYOS AI + Security Suite."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from core.config import get_settings
from core.logging import setup_logging
from core.security.zero_trust import ZeroTrustMiddleware
from apps.api.middleware.metrics import MetricsMiddleware
from apps.api.middleware.intelligent_routing import IntelligentRoutingMiddleware
from apps.api.middleware.edge_routing import EdgeRoutingMiddleware
from apps.api.middleware.budget_check import BudgetCheckMiddleware
from apps.api.middleware.rate_limit import RateLimitMiddleware
from apps.api.middleware.entitlement_check import EntitlementCheckMiddleware
from apps.api.middleware.token_deduction import TokenDeductionMiddleware
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
from apps.api.routers.locker_security import router as locker_security_router
from apps.api.routers.locker_monitoring import router as locker_monitoring_router
from apps.api.routers.locker_users import router as locker_users_router
from apps.api.routers.kill_switch import router as kill_switch_router
from apps.api.routers.token_wallet import router as token_wallet_router
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
setup_logging()

# Initialize providers
from core.providers.init import initialize_providers
initialize_providers()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "BYOS AI + Security Suite — Portable, secure, cost-intelligent AI backend. "
        "No lock-in. Swap hosts in a weekend. Built for agencies, enterprises, and privacy-first platforms."
    ),
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=None,  # Disabled - using protected custom route
    redoc_url=None,  # Disabled - using protected custom route
)


@app.on_event("startup")
async def startup_validation():
    """Validate production configuration on startup."""
    from core.security.secrets_validation import validate_production_config
    try:
        result = validate_production_config()
        logger.info("✅ Production configuration validated successfully")
        if result.get("warnings"):
            logger.warning(f"Configuration warnings: {len(result['warnings'])}")
    except ValueError as e:
        logger.critical(f"❌ PRODUCTION CONFIGURATION INVALID: {e}")
        raise


# ── Middleware stack (outermost = first to run) ───────────────────────────────
# 1. LockerPhycer Security (IDS, rate limiting, security headers) - First line of defense
app.add_middleware(LockerSecurityMiddleware)
# 2. Request security (request ID, IP blocking, brute force protection)
app.add_middleware(RequestSecurityMiddleware)
# 3. Rate limiting (Redis-backed)
app.add_middleware(RateLimitMiddleware)
# 4. Zero-trust authentication
app.add_middleware(ZeroTrustMiddleware)
app.add_middleware(EntitlementCheckMiddleware)
app.add_middleware(TokenDeductionMiddleware)
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

# ── Core AI + Cost Intelligence routers ──────────────────────────────────────
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

# ── Security Suite + new platform routers ────────────────────────────────────
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(security_router, prefix=settings.api_prefix)
app.include_router(monitoring_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(subscriptions_router, prefix=settings.api_prefix)
app.include_router(content_safety_router, prefix=settings.api_prefix)
app.include_router(kill_switch_router, prefix=settings.api_prefix)

# ── LockerPhycer Security Routers (now fully integrated into BYOS) ────────────
app.include_router(locker_security_router, prefix=settings.api_prefix)
app.include_router(locker_monitoring_router, prefix=settings.api_prefix)
app.include_router(locker_users_router, prefix=settings.api_prefix)
app.include_router(token_wallet_router, prefix=settings.api_prefix)

# ── Ollama exec + status (no api_prefix — /v1/exec and /status are top-level) ─
app.include_router(exec_router)


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": settings.app_version, "service": settings.app_name}


@app.get("/", include_in_schema=False)
async def root():
    """Landing page — serves public/index.html."""
    html_path = os.path.join(os.path.dirname(__file__), "..", "..", "public", "index.html")
    html_path = os.path.normpath(html_path)
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": f"{settings.api_prefix}/docs",
    }


# Protected documentation routes - require auth + tokens (100 tokens per view)
@app.get(f"{settings.api_prefix}/docs", include_in_schema=False)
async def protected_docs(request):
    """Swagger UI - requires authentication and 100 tokens per view."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "..", "static", "swagger_ui.html"))


@app.get(f"{settings.api_prefix}/redoc", include_in_schema=False)
async def protected_redoc(request):
    """ReDoc UI - requires authentication and 100 tokens per view."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "..", "static", "redoc.html"))
