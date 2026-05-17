"""Content-Security-Policy and additional security headers middleware."""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Strict CSP for API responses. The landing/workspace SPA routes may need
# loosened policies; those are handled by the frontend's own meta tags.
_CSP_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self' https://api.veklom.com https://api.veklom.dev wss://api.veklom.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
])


class CSPHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds Content-Security-Policy, X-Content-Type-Options, X-Frame-Options,
    Referrer-Policy, and Permissions-Policy headers to every response.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Only add CSP to HTML/JSON responses (skip binary, streaming, etc.)
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type or "application/json" in content_type:
            response.headers.setdefault("Content-Security-Policy", _CSP_POLICY)

        # Always add hardening headers
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(self)",
        )
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")

        return response
