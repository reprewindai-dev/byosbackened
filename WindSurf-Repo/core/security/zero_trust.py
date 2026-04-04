"""Zero-trust security middleware."""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional

# Import from parent module file directly to avoid circular import
import importlib.util
from pathlib import Path

_parent_security = Path(__file__).parent.parent / "security.py"
spec = importlib.util.spec_from_file_location("core_security_parent", _parent_security)
security_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(security_module)
decode_access_token = security_module.decode_access_token
from core.config import get_settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()


# Privacy: Don't log IPs or user agents if disabled
def get_client_ip(request: Request) -> Optional[str]:
    """Get client IP (only if logging enabled)."""
    if not settings.log_user_ips:
        return None
    # Even if logging enabled, obfuscate IP for privacy
    if request.client:
        # Return obfuscated IP (first 3 octets masked)
        ip_parts = request.client.host.split(".")
        if len(ip_parts) == 4:
            return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.xxx"  # Mask last octet
        return request.client.host
    return None


def get_user_agent(request: Request) -> Optional[str]:
    """Get user agent (only if logging enabled)."""
    if not settings.log_user_agents:
        return None
    # Even if logging enabled, don't log full user agent for privacy
    ua = request.headers.get("user-agent", "")
    if ua:
        # Only log browser type, not full version
        if "Mobile" in ua or "iPhone" in ua or "Android" in ua:
            return "Mobile Browser"
        return "Desktop Browser"
    return None


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    """Zero-trust middleware - verify every request."""

    async def dispatch(self, request: Request, call_next):
        """Process request with zero-trust verification."""
        # Skip authentication for health checks and public endpoints
        public_paths = [
            "/health",
            "/api/v1/health",
            "/",
            "/metrics",
            "/game",  # Game frontend
            "/static",  # Static files
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",  # API docs
            "/api/v1/login",
            "/api/v1/login-json",
            "/api/v1/auth/login-json",
            "/api/v1/auth/login",     # Auth login
            "/api/v1/auth/register",  # Auth endpoints
            "/api/v1/content/categories/list",  # Public categories
            "/api/v1/subscription/pricing",  # Public pricing
            "/api/v1/bitcoin/webhook",  # Bitcoin webhook (called by Coinbase)
            "/api/v1/ai/status",        # Ollama health check (public)
            "/api/v1/admin/approval/creator-apply",  # Creator sign-up (public form)
            # Public platform — no auth required for browsing
            "/browse",
            "/video",
            "/creators",
            "/admin/research",
            "/legal/terms",
            "/legal/privacy",
            "/legal/2257",
        ]

        # Also skip if path starts with /static or /docs or public game endpoints
        path = request.url.path
        if (
            path in public_paths
            or path.startswith("/static/")
            or path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/openapi.json")
            or path.startswith("/api/v1/game/public")
            or path.startswith("/api/v1/public/")   # public platform API
            or path.startswith("/api/v1/ads/")       # ExoClick NeverBlock proxy (public)
            or path.startswith("/legal/")            # legal pages
        ):  # Public leaderboard
            return await call_next(request)

        # Verify authentication
        # IMPORTANT: Use return JSONResponse, NOT raise HTTPException.
        # Raising inside BaseHTTPMiddleware on Starlette ≤0.27 causes
        # anyio.EndOfStream to propagate to the ASGI transport layer.
        authorization = request.headers.get("Authorization")
        if not authorization:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authorization header required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid authentication scheme"},
                )
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization header format"},
            )

        # Decode and verify token
        payload = decode_access_token(token)
        if not payload:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
            )

        # Verify workspace_id exists
        workspace_id = payload.get("workspace_id")
        if not workspace_id:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Workspace ID missing in token"},
            )

        # Add security context to request state
        request.state.workspace_id = workspace_id
        request.state.user_id = payload.get("user_id")
        request.state.is_superuser = payload.get("is_superuser", False)

        # Log security event
        logger.info(
            f"Authenticated request: workspace={workspace_id}, "
            f"user={payload.get('user_id')}, path={request.url.path}"
        )

        return await call_next(request)
