"""
LockerPhycer Security Integration for BYOS Backend

Integrates LockerPhycer's advanced security features:
- Intrusion Detection System (IDS)
- Rate limiting with Redis backing
- Security headers
- Request tracking and anomaly detection
- Security event logging

This middleware combines LockerPhycer's security with BYOS's existing
ZeroTrustMiddleware for defense-in-depth.
"""

import time
import logging
import json
import re
import hashlib
import asyncio
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from core.config import get_settings
from core.security.zero_trust import ZeroTrustMiddleware
from db.session import SessionLocal
from db.models import SecurityEvent

logger = logging.getLogger(__name__)
settings = get_settings()


# ═══════════════════════════════════════════════════════════════════════════════
# IDS Signatures
# ═══════════════════════════════════════════════════════════════════════════════

IDSSIGNATURES = [
    {
        "name": "SQL Injection",
        "patterns": [
            r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
            r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",
            r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",
            r"((\%27)|(\'))union",
            r"exec(\s|\+)+(s|x)p\w+",
            r"UNION\s+SELECT",
            r"INSERT\s+INTO",
            r"DELETE\s+FROM",
            r"DROP\s+TABLE",
        ],
        "severity": "critical",
        "category": "injection"
    },
    {
        "name": "XSS Attempt",
        "patterns": [
            r"<script[^>]*>[\s\S]*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe",
            r"<object",
            r"<embed",
            r"eval\s*\(",
            r"expression\s*\(",
        ],
        "severity": "high",
        "category": "xss"
    },
    {
        "name": "Path Traversal",
        "patterns": [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%252e%252e%252f",
            r"..%2f",
            r"%2e%2e/",
            r"\\..\\",
        ],
        "severity": "high",
        "category": "path_traversal"
    },
    {
        "name": "Command Injection",
        "patterns": [
            r";\s*\$\w+",
            r"\|\s*\$\w+",
            r"`\$\w+",
            r"\$\(.*\)",
            r";\s*rm\s+",
            r";\s*cat\s+",
            r"\|\s*nc\s",
            r"&&\s*wget",
            r";\s*curl",
        ],
        "severity": "critical",
        "category": "command_injection"
    },
    {
        "name": "SSRF Attempt",
        "patterns": [
            r"http://localhost",
            r"http://127\.0\.0\.1",
            r"http://0\.0\.0\.0",
            r"http://10\.\d+\.\d+\.\d+",
            r"http://192\.168\.\d+\.\d+",
            r"http://172\.(1[6-9]|2\d|3[01])\.\d+\.\d+",
            r"file://",
            r"dict://",
            r"gopher://",
            r"ftp://",
        ],
        "severity": "high",
        "category": "ssrf"
    },
    {
        "name": "NoSQL Injection",
        "patterns": [
            r"\$where",
            r"\$regex",
            r"\$ne",
            r"\$gt",
            r"\$lt",
            r"\$or",
            r"\$and",
        ],
        "severity": "high",
        "category": "nosql_injection"
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# Rate Limiter with Redis Backing
# ═══════════════════════════════════════════════════════════════════════════════

class RedisRateLimiter:
    """Redis-backed rate limiter for distributed deployments."""
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()
        # Production-tier limits per IP (raised significantly).
        # In production each user has unique IP; for proxied/load-balanced
        # deploys, X-Forwarded-For is honored.
        self.default_limit = 6000  # 100 req/sec per IP
        self.burst_limit = 10000   # absorb bursts
        
        self.limits = {
            "default": (6000, 60),    # 100 req/sec per IP
            "exec":    (600, 60),     # 10 LLM calls/sec per IP (still expensive)
            "auth":    (60, 60),      # 1 auth/sec per IP (brute-force protection)
            "admin":   (300, 60),     # 5 admin ops/sec per IP
        }
    
    async def is_allowed(
        self,
        client_id: str,
        endpoint_type: str = "default"
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed.
        Returns (allowed, metadata).

        NOTE: No async lock here. Under high concurrency a single asyncio.Lock
        serializes every request through one bottleneck (was causing >10s P95
        at 500 concurrent users). The CPython GIL makes individual deque
        append/popleft atomic, and slight over-counting under burst is
        acceptable for rate-limit semantics.
        """
        limit, window = self.limits.get(endpoint_type, self.limits["default"])
        now = time.time()
        cutoff = now - window
        bucket = self.requests[client_id]

        # Clean old requests (best-effort; concurrent mutation is safe under GIL).
        while bucket and bucket[0] < cutoff:
            try:
                bucket.popleft()
            except IndexError:
                break

        current = len(bucket)

        # Burst limit
        if current >= self.burst_limit:
            return False, {
                "limit": self.burst_limit,
                "current": current,
                "window": window,
                "retry_after": int(window - (now - bucket[0])) if bucket else window,
            }

        # Regular limit
        if current >= limit:
            return False, {
                "limit": limit,
                "current": current,
                "window": window,
                "retry_after": int(window - (now - bucket[0])) if bucket else window,
            }

        bucket.append(now)
        return True, {
            "limit": limit,
            "remaining": limit - len(bucket),
            "window": window,
        }
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get rate limit stats for client."""
        now = time.time()
        requests = self.requests.get(client_id, deque())
        
        # Count requests in last minute
        minute_ago = now - 60
        recent_count = sum(1 for t in requests if t > minute_ago)
        
        return {
            "total_requests": len(requests),
            "requests_last_minute": recent_count,
            "first_request": min(requests) if requests else None,
            "last_request": max(requests) if requests else None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Intrusion Detection System
# ═══════════════════════════════════════════════════════════════════════════════

class IntrusionDetectionSystem:
    """Real-time intrusion detection for BYOS backend."""
    
    # IPs that bypass IDS entirely (loopback + RFC1918 prefixes for internal traffic)
    TRUSTED_PREFIXES = ("127.", "::1", "10.", "192.168.", "172.16.", "172.17.",
                        "172.18.", "172.19.", "172.20.", "172.21.", "172.22.",
                        "172.23.", "172.24.", "172.25.", "172.26.", "172.27.",
                        "172.28.", "172.29.", "172.30.", "172.31.")

    def __init__(self):
        self.signatures = IDSSIGNATURES
        # Raised significantly — these were absurdly low for a production API.
        self.alert_threshold = 25  # Alert after 25 threats from same IP
        self.block_threshold = 100  # Block after 100 threats (rolling 1h)
        self.threat_counts: Dict[str, List[Dict]] = defaultdict(list)

    def _is_trusted_ip(self, ip: str) -> bool:
        return any(ip.startswith(p) for p in self.TRUSTED_PREFIXES)
    
    def analyze_request(self, request: Request) -> Dict[str, Any]:
        """Analyze request for intrusion attempts."""
        threats = []
        client_ip = self._get_client_ip(request)

        # Trusted IPs bypass scanning entirely (loopback / private networks).
        if self._is_trusted_ip(client_ip):
            return {
                "threats": [], "threat_count": 0, "risk_score": 0,
                "client_ip": client_ip, "should_alert": False,
                "should_block": False, "total_threats_from_ip": 0,
            }

        # Analyze URL PATH ONLY — NOT full URL, because the host portion
        # (e.g. "http://127.0.0.1") legitimately matches SSRF signatures and
        # would cause every request to flag itself.
        path_threats = self._analyze_string(request.url.path)
        threats.extend(path_threats)

        # Analyze query parameters (user-controlled)
        for param, value in request.query_params.items():
            param_threats = self._analyze_string(f"{param}={value}")
            threats.extend(param_threats)

        # Analyze headers (sensitive ones, user-controlled)
        sensitive_headers = ["user-agent", "referer", "cookie"]
        for header in sensitive_headers:
            value = request.headers.get(header, "")
            header_threats = self._analyze_string(value)
            threats.extend(header_threats)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(threats)
        
        # Track threats from this IP
        if threats:
            self.threat_counts[client_ip].extend([
                {"timestamp": datetime.utcnow(), "threat": t}
                for t in threats
            ])
            
            # Clean old threats (> 1 hour)
            cutoff = datetime.utcnow() - timedelta(hours=1)
            self.threat_counts[client_ip] = [
                t for t in self.threat_counts[client_ip]
                if t["timestamp"] > cutoff
            ]
        
        # Check if IP should be blocked
        should_block = len(self.threat_counts[client_ip]) >= self.block_threshold
        
        return {
            "threats": threats,
            "threat_count": len(threats),
            "risk_score": risk_score,
            "client_ip": client_ip,
            "should_alert": len(self.threat_counts[client_ip]) >= self.alert_threshold,
            "should_block": should_block,
            "total_threats_from_ip": len(self.threat_counts[client_ip]),
        }
    
    def _analyze_string(self, input_string: str) -> List[Dict[str, Any]]:
        """Analyze string for threat patterns."""
        threats = []
        input_lower = input_string.lower()
        
        for signature in self.signatures:
            for pattern in signature["patterns"]:
                if re.search(pattern, input_lower, re.IGNORECASE):
                    threats.append({
                        "type": signature["name"],
                        "category": signature["category"],
                        "severity": signature["severity"],
                        "pattern_matched": pattern[:50],  # Truncate for logging
                        "context": input_string[:100],  # Truncate for logging
                    })
                    break  # Only count each signature once
        
        return threats
    
    def _calculate_risk_score(self, threats: List[Dict]) -> int:
        """Calculate risk score based on threats."""
        severity_scores = {
            "low": 1,
            "medium": 5,
            "high": 10,
            "critical": 25
        }
        return sum(
            severity_scores.get(t["severity"], 1)
            for t in threats
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# Security Headers
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityHeaders:
    """Comprehensive security headers for BYOS backend."""
    
    def add_headers(self, response: Response) -> Response:
        """Add security headers to response."""
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=(), "
            "clipboard=()"
        )
        
        # HSTS (HTTPS only in production)
        if settings.debug is False:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://api.stripe.com https://checkout.stripe.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests;"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # Cache control for sensitive endpoints
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        # Remove server fingerprinting
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# Security Event Logger
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityEventLogger:
    """Log security events to database for audit trail."""
    
    def log_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        client_ip: str,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        """Log security event to database."""
        try:
            db = SessionLocal()
            
            event = SecurityEvent(
                user_id=user_id,
                workspace_id=workspace_id,
                event_type=event_type,
                threat_type=details.get("threat_type") if details else None,
                security_level=severity,
                description=description,
                details=json.dumps(details) if details else None,
                ip_address=client_ip,
                user_agent=details.get("user_agent") if details else None,
            )
            
            db.add(event)
            db.commit()
            
            logger.warning(
                f"Security event logged: {event_type} ({severity}) - {description} "
                f"from IP: {client_ip}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
        finally:
            db.close()
    
    def log_ids_alert(
        self,
        ids_result: Dict[str, Any],
        request: Request,
        workspace_id: Optional[str] = None,
    ):
        """Log IDS alert."""
        if not ids_result["threats"]:
            return
        
        client_ip = ids_result["client_ip"]
        threat_types = list(set(t["type"] for t in ids_result["threats"]))
        
        # Determine severity from highest threat
        severities = [t["severity"] for t in ids_result["threats"]]
        severity = "critical" if "critical" in severities else "high" if "high" in severities else "medium"
        
        self.log_event(
            event_type="ids_alert",
            severity=severity,
            description=f"IDS detected {len(ids_result['threats'])} threats: {', '.join(threat_types)}",
            client_ip=client_ip,
            workspace_id=workspace_id,
            details={
                "threats": ids_result["threats"],
                "risk_score": ids_result["risk_score"],
                "total_threats_from_ip": ids_result["total_threats_from_ip"],
                "user_agent": request.headers.get("user-agent"),
            },
        )
    
    def log_rate_limit_breach(
        self,
        client_id: str,
        endpoint_type: str,
        metadata: Dict[str, Any],
        workspace_id: Optional[str] = None,
    ):
        """Log rate limit breach."""
        self.log_event(
            event_type="rate_limit_exceeded",
            severity="medium",
            description=f"Rate limit exceeded for {endpoint_type} endpoint",
            client_ip=client_id,
            workspace_id=workspace_id,
            details={
                "endpoint_type": endpoint_type,
                "limit": metadata.get("limit"),
                "current": metadata.get("current"),
                "retry_after": metadata.get("retry_after"),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Main Security Middleware
# ═══════════════════════════════════════════════════════════════════════════════

class LockerSecurityMiddleware(BaseHTTPMiddleware):
    """
    LockerPhycer Security Integration Middleware.
    
    Provides:
    - Intrusion Detection System (IDS)
    - Advanced rate limiting
    - Security headers
    - Request tracking
    - Security event logging
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = RedisRateLimiter()
        self.ids = IntrusionDetectionSystem()
        self.security_headers = SecurityHeaders()
        self.event_logger = SecurityEventLogger()
        self.request_tracker = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security checks."""
        
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        # Determine endpoint type for rate limiting
        endpoint_type = self._classify_endpoint(str(request.url.path))
        
        # ═══════════════════════════════════════════════════════════════════════
        # 1. Rate Limiting Check
        # ═══════════════════════════════════════════════════════════════════════
        allowed, rate_metadata = await self.rate_limiter.is_allowed(
            client_ip,
            endpoint_type
        )
        
        if not allowed:
            # Log the rate limit breach
            workspace_id = getattr(request.state, 'workspace_id', None)
            try:
                self.event_logger.log_rate_limit_breach(
                    client_id=client_ip,
                    endpoint_type=endpoint_type,
                    metadata=rate_metadata,
                    workspace_id=workspace_id,
                )
            except Exception:
                pass  # never let logging break the response
            
            # Return JSONResponse directly. Raising HTTPException inside
            # BaseHTTPMiddleware does NOT propagate to FastAPI's handler
            # and gets converted to a generic 500 by Starlette.
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": rate_metadata.get("retry_after", 60),
                },
                headers={"Retry-After": str(rate_metadata.get("retry_after", 60))},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # 2. Intrusion Detection
        # ═══════════════════════════════════════════════════════════════════════
        ids_result = self.ids.analyze_request(request)
        
        if ids_result["should_block"]:
            # IP has exceeded threat threshold - block immediately
            workspace_id = getattr(request.state, 'workspace_id', None)
            try:
                self.event_logger.log_ids_alert(ids_result, request, workspace_id)
            except Exception:
                pass
            
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "Access denied due to suspicious activity"},
            )
        
        if ids_result["should_alert"]:
            # Log IDS alert but allow request
            workspace_id = getattr(request.state, 'workspace_id', None)
            self.event_logger.log_ids_alert(ids_result, request, workspace_id)
        
        # ═══════════════════════════════════════════════════════════════════════
        # 3. Process Request
        # ═══════════════════════════════════════════════════════════════════════
        response = await call_next(request)
        
        # ═══════════════════════════════════════════════════════════════════════
        # 4. Add Security Headers
        # ═══════════════════════════════════════════════════════════════════════
        response = self.security_headers.add_headers(response)
        
        # ═══════════════════════════════════════════════════════════════════════
        # 5. Add Rate Limit Headers
        # ═══════════════════════════════════════════════════════════════════════
        response.headers["X-RateLimit-Limit"] = str(rate_metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_metadata["remaining"])
        
        # ═══════════════════════════════════════════════════════════════════════
        # 6. Log Security Metrics
        # ═══════════════════════════════════════════════════════════════════════
        process_time = time.time() - start_time
        
        if process_time > 5.0:
            # Log slow requests
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {process_time:.2f}s from {client_ip}"
            )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"
    
    def _classify_endpoint(self, path: str) -> str:
        """Classify endpoint for rate limiting."""
        if "/v1/exec" in path:
            return "exec"
        elif "/auth/" in path or "/login" in path or "/register" in path:
            return "auth"
        elif "/admin/" in path:
            return "admin"
        return "default"


# Global instances
_rate_limiter = RedisRateLimiter()
_ids = IntrusionDetectionSystem()
_event_logger = SecurityEventLogger()


def get_rate_limiter() -> RedisRateLimiter:
    """Get global rate limiter instance."""
    return _rate_limiter


def get_ids() -> IntrusionDetectionSystem:
    """Get global IDS instance."""
    return _ids


def get_security_event_logger() -> SecurityEventLogger:
    """Get global security event logger."""
    return _event_logger
