"""FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from core.config import get_settings
from core.logging import setup_logging
from core.security.zero_trust import ZeroTrustMiddleware
from core.security.security_headers import SecurityHeadersMiddleware
from core.security.ddos_protection import DDoSProtectionMiddleware
from core.security.intrusion_middleware import IntrusionDetectionMiddleware
from apps.api.middleware.app_context import AppContextMiddleware
from apps.api.middleware.audit_events import AuditEventsMiddleware
from apps.api.middleware.metrics import MetricsMiddleware
from apps.api.middleware.intelligent_routing import IntelligentRoutingMiddleware
from apps.api.middleware.edge_routing import EdgeRoutingMiddleware
from apps.api.middleware.budget_check import BudgetCheckMiddleware
from apps.api.middleware.demo_gate import DemoGateMiddleware
from apps.api.middleware.locker_security import LockerSecurityMiddleware
from apps.api.routers import (
    apps,
    workspaces,
    workspace_secrets,
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
    anomalies,
    feedback,
    game,
    audit_events,
    sso_oidc,
    scim,
    dashboard,
    ai_router,
    environmental,
    signal_coherence,
    vctt,
    control_plane,
    ai_citizenship,
    governance,
    leads,
)
from apps.api.routers import content, subscription, disclaimer
from apps.api.routers import admin_payments, stripe_billing
from apps.api.routers import admin_scim
from apps.api.routers import security
from apps.api.routers import auth, admin, bitcoin_webhook, ai_recommendations
from apps.api.routers import user_uploads, admin_approval, live_streaming, leaderboard
from apps.api.routers.multi_tenant_llm import router as multi_tenant_llm_router
from apps.api.routers.ollama_services import router as ollama_services_router
from apps.api.routers.admin_research import router as admin_research_router
from apps.api.routers.public_content import router as public_content_router
from apps.api.routers.trapmaster_pro import (
    projects as trapmaster_projects,
    tracks as trapmaster_tracks,
    samples as trapmaster_samples,
    exports as trapmaster_exports,
)
from apps.api.routers.clipcrafter import (
    projects as clipcrafter_projects,
    clips as clipcrafter_clips,
    templates as clipcrafter_templates,
    renders as clipcrafter_renders,
)
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
    description="Portable BYOS AI Backend - No lock-in, swap hosts in a weekend. Secure, compliant, cost-intelligent.",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
)


@app.on_event("startup")
async def startup_validation():
    """Validate production configuration on startup."""
    # Temporarily disabled for development
    logger.info("Development mode - production validation disabled")
    return
    
    from core.security.secrets_validation import validate_production_config

    # Skip validation in debug mode for local development
    if settings.debug:
        logger.info("Debug mode enabled - skipping production validation")
        return

    try:
        result = validate_production_config()
        logger.info("✅ Production configuration validated successfully")
        if result.get("warnings"):
            logger.warning(f"Configuration warnings: {len(result['warnings'])}")
    except ValueError as e:
        logger.critical(f"❌ PRODUCTION CONFIGURATION INVALID: {e}")
        raise  # Fail fast - don't start in invalid state


# Security middleware (order matters - outermost first)
# 1. Security headers (CSP, HSTS, XSS protection, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# 2. DDoS protection (rate limiting, slowloris protection)
app.add_middleware(DDoSProtectionMiddleware)

# 3. Intrusion detection (validate input, detect threats)
app.add_middleware(IntrusionDetectionMiddleware)

# 4. Zero-trust authentication (verify every request)
app.add_middleware(ZeroTrustMiddleware)

# 5. Immutable audit events (append-only HTTP audit trail)
app.add_middleware(AuditEventsMiddleware)

# App context middleware (extract app from URL, must run after ZeroTrustMiddleware)
app.add_middleware(AppContextMiddleware)

# Metrics middleware (track requests)
app.add_middleware(MetricsMiddleware)

# Intelligent routing middleware
app.add_middleware(IntelligentRoutingMiddleware)

# Edge routing middleware
app.add_middleware(EdgeRoutingMiddleware)

# Budget check middleware
app.add_middleware(BudgetCheckMiddleware)

# LockerPhycer security: rate limiting, IDS, security headers, anomaly tracking
app.add_middleware(LockerSecurityMiddleware, debug=settings.debug)

# Demo gate middleware (after budget check, before CORS)
app.add_middleware(DemoGateMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include routers
app.include_router(apps.router, prefix=settings.api_prefix)
app.include_router(workspaces.router, prefix=settings.api_prefix)
app.include_router(workspace_secrets.router, prefix=settings.api_prefix)
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
app.include_router(autonomous.router, prefix=settings.api_prefix)
app.include_router(insights.router, prefix=settings.api_prefix)
app.include_router(suggestions.router, prefix=settings.api_prefix)
app.include_router(anomalies.router, prefix=settings.api_prefix)
app.include_router(feedback.router, prefix=settings.api_prefix)
app.include_router(audit_events.router, prefix=settings.api_prefix)
app.include_router(game.router, prefix=settings.api_prefix)
app.include_router(metrics.router)  # No prefix - /metrics is standard
app.include_router(plugins.router, prefix=settings.api_prefix)
app.include_router(explainability.router, prefix=settings.api_prefix)
app.include_router(compliance.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(ai_router.router, prefix=settings.api_prefix)
app.include_router(environmental.router, prefix=settings.api_prefix)
app.include_router(signal_coherence.router, prefix=settings.api_prefix)
app.include_router(vctt.router, prefix=settings.api_prefix)
app.include_router(control_plane.router, prefix=settings.api_prefix)
app.include_router(ai_citizenship.router, prefix=settings.api_prefix)

# Governance and leads routers (DOMINANCE SAAS DOCTRINE v4)
app.include_router(governance.router, prefix=settings.api_prefix)
app.include_router(leads.router, prefix=settings.api_prefix)

# TrapMaster Pro routes
app.include_router(trapmaster_projects.router, prefix=settings.api_prefix)
app.include_router(trapmaster_tracks.router, prefix=settings.api_prefix)
app.include_router(trapmaster_samples.router, prefix=settings.api_prefix)
app.include_router(trapmaster_exports.router, prefix=settings.api_prefix)

# ClipCrafter routes
app.include_router(clipcrafter_projects.router, prefix=settings.api_prefix)
app.include_router(clipcrafter_clips.router, prefix=settings.api_prefix)
app.include_router(clipcrafter_templates.router, prefix=settings.api_prefix)
app.include_router(clipcrafter_renders.router, prefix=settings.api_prefix)

# Game routes
app.include_router(game.router, prefix=f"{settings.api_prefix}/game")

# Public game routes (no auth required)
from apps.api.routers.game_public import router as game_public_router

app.include_router(game_public_router, prefix=settings.api_prefix)

# Premium content platform routes
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(sso_oidc.router, prefix=settings.api_prefix)
app.include_router(scim.router, prefix=settings.api_prefix)
app.include_router(content.router, prefix=settings.api_prefix)
app.include_router(subscription.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(admin_scim.router, prefix=settings.api_prefix)
app.include_router(disclaimer.router, prefix=settings.api_prefix)
app.include_router(bitcoin_webhook.router, prefix=settings.api_prefix)
app.include_router(admin_payments.router, prefix=settings.api_prefix)
app.include_router(stripe_billing.router, prefix=settings.api_prefix)
app.include_router(security.router, prefix=settings.api_prefix)
app.include_router(ai_recommendations.router, prefix=settings.api_prefix)
app.include_router(user_uploads.router, prefix=settings.api_prefix)
app.include_router(admin_approval.router, prefix=settings.api_prefix)
app.include_router(live_streaming.router, prefix=settings.api_prefix)
app.include_router(leaderboard.router, prefix=settings.api_prefix)

# Multi-tenant LLM execution endpoints
app.include_router(multi_tenant_llm_router, prefix="/api")

# Ollama AI services: tag, recommend, chat, analytics
app.include_router(ollama_services_router, prefix=settings.api_prefix)

# Admin research dashboard
app.include_router(admin_research_router, prefix=settings.api_prefix)

# Public platform: browse, search, trending, DMCA, subscription tiers
app.include_router(public_content_router, prefix=settings.api_prefix)

# Static files for game
static_dir = Path(__file__).parent.parent.parent / "static"
logger.info(f"Static directory: {static_dir}, exists: {static_dir.exists()}")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"Mounted static files from {static_dir}")

    @app.get("/game")
    async def game_page():
        """Serve the game HTML page."""
        game_file = static_dir / "game.html"
        logger.info(f"Game file: {game_file}, exists: {game_file.exists()}")
        if game_file.exists():
            return FileResponse(game_file)
        return {"error": f"Game file not found at {game_file}"}

    @app.get("/admin/research")
    async def admin_research_page():
        """Admin-only research dashboard."""
        f = static_dir / "admin" / "research.html"
        return FileResponse(f) if f.exists() else {"error": "Not found"}

    @app.get("/browse")
    async def browse_page():
        """Public content browse page."""
        f = static_dir / "browse.html"
        return FileResponse(f) if f.exists() else {"error": "Not found"}

    @app.get("/video")
    async def video_page():
        """Public video player page."""
        f = static_dir / "video.html"
        return FileResponse(f) if f.exists() else {"error": "Not found"}

    @app.get("/creators")
    async def creators_page():
        """Creator profile page."""
        f = static_dir / "creator.html"
        return FileResponse(f) if f.exists() else {"error": "Not found"}

    @app.get("/legal/terms")
    async def terms_page():
        f = static_dir / "legal" / "terms.html"
        return FileResponse(f) if f.exists() else {"error": "Not found"}

    @app.get("/legal/privacy")
    async def privacy_page():
        f = static_dir / "legal" / "privacy.html"
        return FileResponse(f) if f.exists() else {"error": "Not found"}

    @app.get("/legal/2257")
    async def compliance_2257_page():
        f = static_dir / "legal" / "2257.html"
        return FileResponse(f) if f.exists() else {"error": "Not found"}

else:
    logger.warning(f"Static directory not found: {static_dir}")


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": settings.app_version}


@app.get(f"{settings.api_prefix}/health")
async def health_api():
    """Health check with API prefix."""
    return {"status": "ok", "version": settings.app_version}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": f"{settings.api_prefix}/docs",
        "features": [
            "Cost Intelligence",
            "Intelligent Routing",
            "Compliance & Audit",
            "Privacy-by-Design",
            "Plugin System",
        ],
    }
