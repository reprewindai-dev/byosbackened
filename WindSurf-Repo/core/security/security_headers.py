"""Comprehensive security headers middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi import Request
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Content Security Policy (CSP) - Prevent XSS attacks
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
            "img-src 'self' data: https: http:; "
            "connect-src 'self' https://api.coinbase.com https://commerce.coinbase.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests;"
        )

        # Security headers
        security_headers = {
            # Prevent XSS attacks
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",  # Prevent clickjacking
            "X-XSS-Protection": "1; mode=block",
            # Content Security Policy
            "Content-Security-Policy": csp,
            # Strict Transport Security (HSTS) - Force HTTPS
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            # Referrer Policy - Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions Policy (formerly Feature Policy)
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "accelerometer=()"
            ),
            # Cross-Origin policies
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
            # Prevent MIME type sniffing
            "X-Download-Options": "noopen",
            "X-Permitted-Cross-Domain-Policies": "none",
        }

        # Add all security headers
        for header, value in security_headers.items():
            response.headers[header] = value

        return response
