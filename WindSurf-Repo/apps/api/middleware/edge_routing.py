"""Edge routing middleware - automatically routes requests to optimal region."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.edge.routing_engine import get_edge_routing_engine
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
edge_routing_engine = get_edge_routing_engine()


class EdgeRoutingMiddleware(BaseHTTPMiddleware):
    """
    Edge routing middleware.

    Automatically routes requests to optimal region based on:
    - User geography (geo-IP)
    - Data residency requirements
    - Learned patterns
    - Latency and cost optimization
    """

    async def dispatch(self, request: Request, call_next):
        """Route request to optimal region."""
        # Only apply to AI operation endpoints
        ai_endpoints = [
            f"{settings.api_prefix}/transcribe",
            f"{settings.api_prefix}/extract",
            f"{settings.api_prefix}/chat",
        ]

        if not any(request.url.path.startswith(ep) for ep in ai_endpoints):
            return await call_next(request)

        # Extract workspace_id from request (if available)
        workspace_id = getattr(request.state, "workspace_id", None)

        # Extract user region from headers (geo-IP or user preference)
        user_region = request.headers.get("X-User-Region") or request.headers.get("CF-IPCountry")

        # Extract data residency from headers or workspace settings
        data_residency = request.headers.get("X-Data-Residency")

        # Extract operation type from path
        operation_type = "transcribe"
        if "/extract" in request.url.path:
            operation_type = "extract"
        elif "/chat" in request.url.path:
            operation_type = "chat"

        # Estimate input size (if available in headers)
        input_size_bytes = int(request.headers.get("Content-Length", 0))

        # Select optimal region
        if workspace_id:
            region_selection = edge_routing_engine.select_region(
                workspace_id=workspace_id,
                operation_type=operation_type,
                user_region=user_region,
                data_residency=data_residency,
                input_size_bytes=input_size_bytes,
                prioritize_latency=True,  # Default to latency optimization
            )

            # Store region selection in request state
            request.state.edge_region = region_selection["region"]
            request.state.edge_reasoning = region_selection["reasoning"]

            logger.debug(
                f"Edge routing: {operation_type} -> {region_selection['region']} "
                f"({region_selection['reasoning']})"
            )
        else:
            # No workspace_id, use default region
            request.state.edge_region = "us-east"
            request.state.edge_reasoning = "Default region (no workspace context)"

        # Add region header for downstream services
        request.headers.__dict__["_list"].append(
            (b"x-edge-region", request.state.edge_region.encode())
        )

        return await call_next(request)
