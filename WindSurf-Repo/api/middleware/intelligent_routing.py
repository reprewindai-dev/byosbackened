"""Intelligent routing middleware."""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from core.cost_intelligence import ProviderRouter, RoutingConstraints
from core.config import get_settings
import logging
import json
from db.session import SessionLocal
from db.models import RoutingPolicy
from core.security import decode_access_token

logger = logging.getLogger(__name__)
settings = get_settings()
provider_router = ProviderRouter()


class IntelligentRoutingMiddleware(BaseHTTPMiddleware):
    """Auto-route requests to optimal provider."""

    async def dispatch(self, request: Request, call_next):
        """Route request based on constraints."""
        # Only apply to AI operation endpoints
        if not request.url.path.startswith(
            f"{settings.api_prefix}/transcribe"
        ) and not request.url.path.startswith(f"{settings.api_prefix}/extract"):
            return await call_next(request)

        # Get routing constraints from workspace policy
        workspace_id = getattr(request.state, "workspace_id", None)
        if not workspace_id:
            auth = request.headers.get("authorization")
            if auth:
                try:
                    scheme, token = auth.split()
                    if scheme.lower() == "bearer":
                        payload = decode_access_token(token)
                        if payload:
                            workspace_id = payload.get("workspace_id")
                except Exception:
                    workspace_id = None
        constraints = RoutingConstraints(strategy="cost_optimized")
        allowed_providers = None
        enforcement_mode = "strict"
        policy_id = None
        policy_version = None

        if workspace_id:
            db = SessionLocal()
            try:
                policy = (
                    db.query(RoutingPolicy)
                    .filter(
                        RoutingPolicy.workspace_id == workspace_id,
                        RoutingPolicy.enabled == True,
                    )
                    .first()
                )

                if policy:
                    policy_id = policy.id
                    policy_version = (
                        str(policy.version)
                        if getattr(policy, "version", None) is not None
                        else None
                    )
                    policy_constraints = {}
                    if policy.constraints_json:
                        try:
                            policy_constraints = json.loads(policy.constraints_json)
                        except Exception:
                            policy_constraints = {}

                    constraints = RoutingConstraints(
                        max_cost=(
                            policy_constraints.get("max_cost")
                            and float(policy_constraints.get("max_cost"))
                            or None
                        ),
                        min_quality=policy_constraints.get("min_quality"),
                        max_latency_ms=policy_constraints.get("max_latency_ms"),
                        strategy=policy.strategy or "cost_optimized",
                    )

                    # Optional allowlist/denylist support if present in JSON
                    allowed_providers = policy_constraints.get("allowed_providers")
                    enforcement_mode = policy_constraints.get("enforcement_mode") or "strict"
            finally:
                db.close()

        # Store routing decision in request state
        # (Actual routing happens in the endpoint handler)
        request.state.routing_constraints = constraints
        request.state.allowed_providers = allowed_providers
        request.state.policy_enforcement_mode = enforcement_mode
        request.state.policy_id = policy_id
        request.state.policy_version = policy_version

        return await call_next(request)
