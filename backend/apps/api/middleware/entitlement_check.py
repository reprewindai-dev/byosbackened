"""Entitlement check middleware - enforces plan-based access control."""
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import Subscription, Workspace, PlanTier, SubscriptionStatus
from core.redis_pool import get_redis

logger = logging.getLogger(__name__)

# Plan hierarchy (higher index = higher tier)
PLAN_HIERARCHY = ["starter", "pro", "sovereign", "enterprise"]

# Public endpoints that don't require entitlement checks
PUBLIC_ENDPOINTS = {
    "/health",
    "/",
    "/status",
    "/metrics",
    # Docs now require payment - 10% free tier available
    # "/api/v1/docs",  # LOCKED - requires starter+ plan
    # "/api/v1/redoc",  # LOCKED - requires starter+ plan
    "/api/v1/openapi.json",  # Still public for SDK generation
    "/api/v1/register",
    "/api/v1/login",
    "/api/v1/refresh",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/subscriptions/plans",
    "/api/v1/subscriptions/webhook",
}

# Endpoint to plan tier mapping
# Keys are (method, path) tuples or just path for all methods
# Values are the minimum required plan tier
ENDPOINT_PLAN_REQUIREMENTS: Dict[str, str] = {
    # Auth - all plans
    "/api/v1/me": "starter",
    "/api/v1/logout": "starter",
    "/api/v1/mfa": "starter",
    "/api/v1/api-keys": "starter",
    "/api/v1/auth/me": "starter",
    "/api/v1/auth/refresh": "starter",
    "/api/v1/auth/logout": "starter",
    "/api/v1/auth/mfa": "starter",
    "/api/v1/auth/api-keys": "starter",
    
    # Cost - starter+
    "/api/v1/cost/predict": "starter",
    "/api/v1/cost/history": "starter",
    
    # Content safety - starter+
    "/api/v1/content-safety/scan": "starter",
    "/api/v1/content-safety/age-verification": "starter",
    
    # Routing - pro+
    "/api/v1/routing/policy": "pro",
    "/api/v1/routing/test": "pro",
    
    # Budget - pro+
    "/api/v1/budget": "pro",
    
    # Billing - pro+
    "/api/v1/billing": "pro",
    
    # Insights - pro+
    "/api/v1/insights": "pro",
    
    # Autonomous - pro+ (most), sovereign+ (quality optimize/failure-risk), enterprise (train)
    "/api/v1/autonomous/cost/predict": "pro",
    "/api/v1/autonomous/routing/select": "pro",
    "/api/v1/autonomous/routing/update": "pro",
    "/api/v1/autonomous/quality/predict": "pro",
    "/api/v1/autonomous/quality/optimize": "sovereign",
    "/api/v1/autonomous/quality/failure-risk": "sovereign",
    "/api/v1/autonomous/train": "enterprise",
    
    # Explainability - pro+
    "/api/v1/explain": "pro",
    
    # Privacy - sovereign+
    "/api/v1/privacy/export": "sovereign",
    "/api/v1/privacy/delete": "sovereign",
    
    # Audit - sovereign+
    "/api/v1/audit": "sovereign",
    
    # Compliance - sovereign+
    "/api/v1/compliance": "sovereign",
    
    # Security suite - sovereign+
    "/api/v1/security": "sovereign",
    
    "/api/v1/locker/security": "sovereign",
    
    # Kill switch - sovereign+
    "/api/v1/cost/kill-switch": "sovereign",
    
    # Plugins - sovereign+
    "/api/v1/plugins": "sovereign",
    
    # Monitoring - pro+ (dashboard), starter (health)
    "/api/v1/monitoring/dashboard": "pro",
    "/api/v1/monitoring/metrics": "pro",
    
    # Admin - enterprise
    "/api/v1/admin": "enterprise",
    
    # Documentation - starter+ (was public, now paywalled)
    "/api/v1/docs": "starter",
    "/api/v1/redoc": "starter",
}


class EntitlementCheckMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce plan-based access control.
    
    Checks if the requesting workspace has the required subscription tier
    to access the requested endpoint.
    """
    
    def __init__(self, app, endpoint_catalog: Optional[Dict] = None):
        super().__init__(app)
        self.endpoint_catalog = endpoint_catalog or ENDPOINT_PLAN_REQUIREMENTS
    
    def _get_required_plan(self, method: str, path: str) -> Optional[str]:
        """
        Get the minimum required plan tier for an endpoint.
        Returns None if no specific tier required (defaults to starter).
        """
        # Try exact match first
        key = f"{method.upper()} {path}"
        if key in self.endpoint_catalog:
            return self.endpoint_catalog[key]
        
        # Try path-only match
        if path in self.endpoint_catalog:
            return self.endpoint_catalog[path]
        
        # Try prefix match for nested paths
        for endpoint_path, plan in self.endpoint_catalog.items():
            if path.startswith(endpoint_path):
                return plan
        
        # Default: starter tier required
        return "starter"
    
    def _has_entitlement(self, current_plan: str, required_plan: str) -> bool:
        """
        Check if current plan meets or exceeds the required plan.
        """
        try:
            current_idx = PLAN_HIERARCHY.index(current_plan.lower())
            required_idx = PLAN_HIERARCHY.index(required_plan.lower())
            return current_idx >= required_idx
        except ValueError:
            # Unknown plan, default to requiring starter
            return required_plan == "starter"
    
    def _get_cached_plan(self, workspace_id: str) -> Optional[str]:
        """Get cached plan from Redis."""
        try:
            redis = get_redis()
            key = f"workspace:plan:{workspace_id}"
            plan = redis.get(key)
            if plan:
                return plan.decode()
        except Exception as e:
            logger.warning(f"Failed to get cached plan: {e}")
        return None
    
    def _cache_plan(self, workspace_id: str, plan: str, ttl: int = 300):
        """Cache plan in Redis with TTL."""
        try:
            redis = get_redis()
            key = f"workspace:plan:{workspace_id}"
            redis.setex(key, ttl, plan)
        except Exception as e:
            logger.warning(f"Failed to cache plan: {e}")

    def _resolve_current_plan(self, request: Request, workspace_id: str) -> str:
        """
        Resolve the current effective plan for the request.

        Workspace owners, admins, and superusers are treated as enterprise so
        the signed-in control plane can access the full surface without getting
        trapped by subscription gates.
        """
        if getattr(request.state, "is_superuser", False):
            return "enterprise"

        role = str(getattr(request.state, "role", "") or "").lower()
        if role in {"admin", "owner"}:
            return "enterprise"

        cached_plan = self._get_cached_plan(workspace_id)
        current_plan = cached_plan
        cache_ttl = 300

        if not current_plan:
            # Look up subscription from database
            db = SessionLocal()
            try:
                subscription = db.query(Subscription).filter(
                    Subscription.workspace_id == workspace_id
                ).first()

                if subscription and subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}:
                    current_plan = subscription.plan.value
                else:
                    workspace = db.query(Workspace).filter(
                        Workspace.id == workspace_id
                    ).first()
                    if workspace and workspace.license_tier:
                        license_tier = str(workspace.license_tier).lower()
                        license_expires_at = workspace.license_expires_at
                        if license_tier in PLAN_HIERARCHY and (
                            not license_expires_at or license_expires_at > datetime.utcnow()
                        ):
                            current_plan = license_tier
                            if license_expires_at:
                                remaining = int((license_expires_at - datetime.utcnow()).total_seconds())
                                if remaining > 0:
                                    cache_ttl = min(cache_ttl, remaining)
                        else:
                            current_plan = "starter"
                    else:
                        # No active subscription or trial license - default to starter
                        current_plan = "starter"

                # Cache the result
                self._cache_plan(workspace_id, current_plan, ttl=cache_ttl)
            finally:
                db.close()

        return current_plan
    
    async def dispatch(self, request: Request, call_next):
        """
        Check entitlement before processing request.
        """
        path = request.url.path
        method = request.method
        
        # Skip public endpoints
        if path in PUBLIC_ENDPOINTS:
            return await call_next(request)
        
        # Skip if already checked by FastPathMiddleware
        if getattr(request.state, "skip_entitlement", False):
            return await call_next(request)
        
        # Get workspace_id from request state (set by ZeroTrustMiddleware)
        workspace_id = getattr(request.state, "workspace_id", None)
        if not workspace_id:
            # No authentication, let it pass (auth middleware will handle it)
            return await call_next(request)
        
        # Get required plan for this endpoint
        required_plan = self._get_required_plan(method, path)
        if not required_plan:
            return await call_next(request)

        current_plan = self._resolve_current_plan(request, workspace_id)
        
        # Check entitlement
        if not self._has_entitlement(current_plan, required_plan):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"This endpoint requires {required_plan} plan or higher",
                    "current_plan": current_plan,
                    "required_plan": required_plan,
                    "upgrade_url": "/api/v1/subscriptions/plans"
                },
                headers={
                    "X-Required-Plan": required_plan,
                    "X-Current-Plan": current_plan
                }
            )
        
        # Store plan in request state for downstream use
        request.state.current_plan = current_plan
        
        return await call_next(request)
