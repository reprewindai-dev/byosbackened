"""Intelligent routing middleware."""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from core.cost_intelligence import ProviderRouter, RoutingConstraints
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
provider_router = ProviderRouter()


class IntelligentRoutingMiddleware(BaseHTTPMiddleware):
    """Auto-route requests to optimal provider."""

    async def dispatch(self, request: Request, call_next):
        """Route request based on constraints."""
        # Only apply to AI operation endpoints
        if not request.url.path.startswith(f"{settings.api_prefix}/transcribe") and \
           not request.url.path.startswith(f"{settings.api_prefix}/extract"):
            return await call_next(request)
        
        # Get routing constraints from headers or workspace settings
        # For now, use default cost-optimized strategy
        constraints = RoutingConstraints(
            strategy="cost_optimized",
        )
        
        # Store routing decision in request state
        # (Actual routing happens in the endpoint handler)
        request.state.routing_constraints = constraints
        
        return await call_next(request)
