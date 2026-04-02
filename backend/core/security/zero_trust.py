"""Zero-trust security middleware."""
import hashlib
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
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
    "/status",      # system health — no auth required
    "/v1/exec",     # uses its own X-API-Key + tenant RLS auth
    f"{settings.api_prefix}/auth/register",
    f"{settings.api_prefix}/auth/login",
    f"{settings.api_prefix}/auth/refresh",
    f"{settings.api_prefix}/subscriptions/plans",
    f"{settings.api_prefix}/subscriptions/webhook",
    f"{settings.api_prefix}/docs",
    f"{settings.api_prefix}/redoc",
    f"{settings.api_prefix}/openapi.json",
}


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    """
    Zero-trust middleware — verify every request.
    Supports both JWT Bearer tokens and API keys (byos_ prefix).
    Public paths skip authentication entirely.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Pass through public endpoints
        if path in _PUBLIC_PATHS or path.startswith(f"{settings.api_prefix}/docs"):
            return await call_next(request)

        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
            )

        # API key path (byos_ prefix) — resolve workspace from DB
        if token.startswith("byos_"):
            workspace_id = await self._resolve_api_key(request, token)
            request.state.workspace_id = workspace_id
            request.state.user_id = None
            request.state.is_superuser = False
            return await call_next(request)

        # JWT path
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        workspace_id = payload.get("workspace_id")
        if not workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workspace ID missing in token",
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
