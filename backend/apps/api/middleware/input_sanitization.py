"""Input sanitization middleware — blocks common injection patterns on write endpoints."""
import logging
import re

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_SKIP_PATHS = {
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/billing/connect/webhook",
    "/api/v1/subscriptions/webhook",
    "/api/v1/resend/webhook",
    "/api/v1/qstash/webhook",
}

_SQL_INJECTION_PATTERNS = [
    re.compile(r"(?i)\b(UNION\s+SELECT|DROP\s+TABLE|DELETE\s+FROM|INSERT\s+INTO)\b"),
    re.compile(r"(?i);\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE)\b"),
    re.compile(r"(?i)'\s*(OR|AND)\s+'?\d*'?\s*=\s*'?\d*"),
    re.compile(r"(?i)--\s*$"),
]

_XSS_PATTERNS = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on(load|error|click|mouseover|focus|blur)\s*=", re.IGNORECASE),
    re.compile(r"<iframe[^>]*>", re.IGNORECASE),
]

_PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.\\"),
    re.compile(r"%2e%2e[/\\]", re.IGNORECASE),
]

_MAX_BODY_SCAN_SIZE = 64 * 1024  # only scan first 64KB


def _scan_text(text: str) -> str | None:
    """Return the attack category if a pattern matches, else None."""
    for pattern in _SQL_INJECTION_PATTERNS:
        if pattern.search(text):
            return "sql_injection"
    for pattern in _XSS_PATTERNS:
        if pattern.search(text):
            return "xss"
    for pattern in _PATH_TRAVERSAL_PATTERNS:
        if pattern.search(text):
            return "path_traversal"
    return None


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Scans request body and query params for injection patterns on write endpoints."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in _SKIP_PATHS or request.method not in _WRITE_METHODS:
            return await call_next(request)

        # Scan query parameters
        for key, value in request.query_params.items():
            threat = _scan_text(f"{key}={value}")
            if threat:
                logger.warning(
                    "Input sanitization blocked %s in query param: path=%s key=%s",
                    threat, path, key,
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Request blocked by input validation"},
                )

        # Scan body (only for JSON content)
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.body()
            if body and len(body) <= _MAX_BODY_SCAN_SIZE:
                text = body.decode("utf-8", errors="ignore")
                threat = _scan_text(text)
                if threat:
                    logger.warning(
                        "Input sanitization blocked %s in body: path=%s size=%d",
                        threat, path, len(body),
                    )
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Request blocked by input validation"},
                    )

        return await call_next(request)
