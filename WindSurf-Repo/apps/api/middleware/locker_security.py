"""
LockerPhycer Security Middleware — wired into WindSurf-Repo.
Provides: rate limiting, request validation, intrusion detection,
security headers, request tracking, and anomaly alerting.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import logging
import asyncio
from typing import Dict, List, Any
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class LockerSecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware from LockerPhycer:
    - Rate limiting (100 req/min per IP)
    - URL + header threat detection
    - 10 MB request body cap
    - Suspicious-activity anomaly alerting
    - Full security headers on every response
    """

    def __init__(self, app, debug: bool = False):
        super().__init__(app)
        self.debug = debug
        self.rate_limiter = _RateLimiter()
        self.request_tracker = _RequestTracker()
        self.ids = _IntrusionDetectionSystem()

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)

        # 1. Rate limit
        if not await self.rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded — slow down.",
            )

        # 2. Request validation (URL safety, headers, size)
        await self._validate_request(request, client_ip)

        # 3. Intrusion detection (SQL injection, XSS, path traversal, etc.)
        threat_report = self.ids.analyze_request(request)
        if threat_report["risk_score"] >= 20:
            logger.warning(
                f"[LockerSecurity] HIGH-RISK request blocked from {client_ip}: "
                f"threats={threat_report['threats']}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request blocked by security policy.",
            )
        elif threat_report["risk_score"] >= 5:
            logger.warning(
                f"[LockerSecurity] Suspicious request from {client_ip}: "
                f"risk_score={threat_report['risk_score']}"
            )

        # 4. Track request
        self.request_tracker.add_request(client_ip, str(request.url.path))

        # 5. Process
        start_time = time.time()
        response = await call_next(request)
        elapsed = time.time() - start_time

        # 6. Security headers
        response = _add_security_headers(response, is_production=not self.debug)

        # 7. Log slow / error responses
        if elapsed > 5.0:
            logger.warning(
                f"[LockerSecurity] Slow request: {request.method} {request.url.path} "
                f"took {elapsed:.2f}s from {client_ip}"
            )
        if response.status_code >= 400:
            logger.warning(
                f"[LockerSecurity] {response.status_code} {request.method} "
                f"{request.url.path} from {client_ip}"
            )
        if self.request_tracker.is_suspicious_activity(client_ip):
            logger.warning(
                f"[LockerSecurity] Suspicious activity pattern from {client_ip}"
            )

        return response

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"

    async def _validate_request(self, request: Request, client_ip: str):
        # URL safety
        url = str(request.url)
        if not (url.startswith("http://") or url.startswith("https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsafe URL detected.",
            )

        # Header injection check
        danger = ["<script", "javascript:", "data:", "vbscript:"]
        for hdr in ["X-Forwarded-Host", "X-Originating-IP"]:
            val = request.headers.get(hdr, "")
            if any(p in val.lower() for p in danger):
                logger.warning(f"[LockerSecurity] Header injection attempt from {client_ip}: {hdr}={val}")

        # Body size cap (10 MB)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request body exceeds 10 MB limit.",
            )


# ── Security Headers ──────────────────────────────────────────────────────────

def _add_security_headers(response: Response, is_production: bool = False) -> Response:
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    if is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


# ── Rate Limiter ──────────────────────────────────────────────────────────────

class _RateLimiter:
    """100 requests per minute per IP (in-memory)."""

    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def is_allowed(self, client_ip: str) -> bool:
        async with self.lock:
            now = time.time()
            cutoff = now - 60
            while self.requests[client_ip] and self.requests[client_ip][0] < cutoff:
                self.requests[client_ip].popleft()
            if len(self.requests[client_ip]) >= 100:
                return False
            self.requests[client_ip].append(now)
            return True


# ── Request Tracker ───────────────────────────────────────────────────────────

class _RequestTracker:
    """Track last 100 paths per IP, flag repeated hits on sensitive endpoints."""

    SENSITIVE = ["/admin", "/api/v1/users", "/api/v1/security", "/api/v1/auth"]

    def __init__(self):
        self.requests: Dict[str, List[str]] = defaultdict(list)
        self.lock = asyncio.Lock()

    def add_request(self, client_ip: str, path: str):
        asyncio.create_task(self._add(client_ip, path))

    async def _add(self, client_ip: str, path: str):
        async with self.lock:
            self.requests[client_ip].append(path)
            if len(self.requests[client_ip]) > 100:
                self.requests[client_ip] = self.requests[client_ip][-100:]

    def is_suspicious_activity(self, client_ip: str) -> bool:
        recent = self.requests.get(client_ip, [])[-10:]
        hits = sum(1 for p in recent if any(s in p for s in self.SENSITIVE))
        return hits >= 5


# ── Intrusion Detection ───────────────────────────────────────────────────────

class _IntrusionDetectionSystem:
    SIGNATURES = [
        {"name": "SQL Injection",    "patterns": ["union select", "drop table", "insert into", "delete from", "' or '1'='1"], "score": 15},
        {"name": "XSS",              "patterns": ["<script", "javascript:", "onerror=", "onload="],                            "score": 10},
        {"name": "Path Traversal",   "patterns": ["../", "..\\", "%2e%2e%2f", "%2e%2e/"],                                      "score": 15},
        {"name": "Command Injection","patterns": ["; rm ", "; cat ", "| nc ", "&& wget", "$(", "`"],                           "score": 20},
        {"name": "SSRF",             "patterns": ["169.254.169.254", "localhost", "127.0.0.1", "file://"],                     "score": 10},
    ]

    def analyze_request(self, request: Request) -> Dict[str, Any]:
        targets = [
            str(request.url.path),
            str(request.url.query),
        ]
        for header, value in request.headers.items():
            targets.append(f"{header}:{value}")

        threats: List[Dict] = []
        total_score = 0

        for target in targets:
            target_lower = target.lower()
            for sig in self.SIGNATURES:
                for pattern in sig["patterns"]:
                    if pattern in target_lower:
                        threats.append({"type": sig["name"], "pattern": pattern, "in": target[:80]})
                        total_score += sig["score"]
                        break  # one match per signature per target

        return {"threats": threats, "risk_score": total_score}
