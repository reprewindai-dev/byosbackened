"""Zero-trust security middleware."""
import hashlib
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional
from core.security.auth_utils import decode_access_token
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Paths that do not require authentication
_PUBLIC_PATHS = {
    "/health",
    "/",
    "/metrics",
    "/status",      # system health ? no auth required
    "/status.html",
    "/status/data", # public demo status payload
    "/api/v1/edge/demo/summary",
    "/api/v1/edge/demo/infrastructure",
    "/v1/exec",     # uses its own X-API-Key + tenant RLS auth
    f"{settings.api_prefix}/register",
    f"{settings.api_prefix}/login",
    f"{settings.api_prefix}/refresh",
    f"{settings.api_prefix}/auth/register",
    f"{settings.api_prefix}/auth/login",
    f"{settings.api_prefix}/auth/refresh",
    f"{settings.api_prefix}/subscriptions/plans",
    f"{settings.api_prefix}/subscriptions/webhook",
    f"{settings.api_prefix}/auth/github/login",
    f"{settings.api_prefix}/auth/github/callback",
    f"{settings.api_prefix}/support/chat",
    f"{settings.api_prefix}/payments/webhook",
    # Docs now require auth + tokens (100 per view)
    # f"{settings.api_prefix}/docs",      # LOCKED - requires auth + 100 tokens
    # f"{settings.api_prefix}/redoc",     # LOCKED - requires auth + 100 tokens
    # f"{settings.api_prefix}/openapi.json",  # LOCKED - requires auth
}

# Public web-surface prefixes (landing + marketplace UI).
_PUBLIC_PREFIXES = (
    "/marketplace",
    "/vendor",
    "/signup",
    "/login",
    "/dashboard",
    "/blog",
    "/legal",
    "/app",
    "/.well-known",
)

_PUBLIC_STATIC_SUFFIXES = (
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".ico",
    ".webmanifest",
    ".xml",
    ".txt",
)


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    """
    Zero-trust middleware ? verify every request.
    Supports both JWT Bearer tokens and API keys (byos_ prefix).
    Public paths skip authentication entirely.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()
        # Normalize trailing slash ? but preserve "/" as-is so it matches
        # _PUBLIC_PATHS. rstrip("/") would turn "/" into "" (empty string).
        if len(path) > 1:
            path = path.rstrip("/")

        # Block path traversal attempts
        if ".." in path or "//" in path:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid request path"},
            )

        # Pass through public endpoints
        if path in _PUBLIC_PATHS:
            return await call_next(request)

        # Public marketplace browsing endpoints (read-only)
        if method == "GET":
            listings_base = f"{settings.api_prefix}/listings"
            if path == listings_base or path.startswith(listings_base + "/"):
                return await call_next(request)

        if path.endswith(_PUBLIC_STATIC_SUFFIXES):
            return await call_next(request)

        for prefix in _PUBLIC_PREFIXES:
            if path == prefix or path.startswith(prefix + "/"):
                return await call_next(request)
        
        # Require authentication for all other endpoints
        # Allow root endpoint without auth for public info
        if path == "/":
            return await call_next(request)
        
        authorization = request.headers.get("Authorization")
        if not authorization:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authorization header required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            scheme, token = authorization.split(" ", 1)
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

        # API key path (byos_ prefix) ? resolve workspace from DB
        if token.startswith("byos_"):
            try:
                workspace_id = await self._resolve_api_key(request, token)
            except HTTPException as e:
                return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
            request.state.workspace_id = workspace_id
            request.state.user_id = None
            request.state.is_superuser = False
            return await call_next(request)

        # JWT path
        payload = decode_access_token(token)
        if not payload:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
            )

        workspace_id = payload.get("workspace_id")
        if not workspace_id:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Workspace ID missing in token"},
            )

        request.state.workspace_id = workspace_id
        request.state.user_id = payload.get("user_id")
        request.state.is_superuser = payload.get("is_superuser", False)
        request.state.role = payload.get("role", "user")

        logger.debug(
            f"Authenticated: workspace={workspace_id} user={payload.get('user_id')} path={path}"
        )

        return await call_next(request)

    async def _resolve_api_key(self, request: Request, raw_key: str) -> str:
        """Validate API key against DB and return workspace_id."""
        from datetime import datetime
        from db.session import SessionLocal
        from db.models import APIKey

        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        db = SessionLocal()
        try:
            api_key = db.query(APIKey).filter(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
            ).first()
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                )
            if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key expired",
                )
            api_key.last_used_at = datetime.utcnow()
            db.commit()
            return api_key.workspace_id
        finally:
            db.close()
