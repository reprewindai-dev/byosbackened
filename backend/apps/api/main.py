"""FastAPI application — BYOS AI + Security Suite."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import get_settings
from core.logging import setup_logging
from core.security.zero_trust import ZeroTrustMiddleware
from apps.api.middleware.metrics import MetricsMiddleware
from apps.api.middleware.intelligent_routing import IntelligentRoutingMiddleware
from apps.api.middleware.edge_routing import EdgeRoutingMiddleware
from apps.api.middleware.budget_check import BudgetCheckMiddleware
from apps.api.middleware.rate_limit import RateLimitMiddleware
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
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
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
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ZeroTrustMiddleware)
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


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": settings.app_version, "service": settings.app_name}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": f"{settings.api_prefix}/docs",
        "features": [
            "Authentication & MFA",
            "API Key Management",
            "Cost Intelligence & Intelligent Routing",
            "GDPR-Compliant Cryptographic Audit Trails",
            "Privacy-by-Design & PII Detection",
            "Security Suite: Threat Detection & Zero-Trust",
            "Monitoring: Real-time Health & Metrics",
            "Content Safety & Age Verification",
            "Stripe Subscription Management",
            "Plugin System",
            "Multi-Tenant Workspaces",
        ],
    }
