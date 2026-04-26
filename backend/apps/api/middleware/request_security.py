"""
Additional security middleware for request tracking and hardening.
- Request ID generation for audit trails
- IP blocking for repeated offenders
- Enhanced brute force protection
"""
import uuid
import time
import logging
from typing import Dict, Set
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from collections import defaultdict

logger = logging.getLogger(__name__)


class IPBlockList:
    """Track and block malicious IPs."""
    
    def __init__(self):
        self.blocked_ips: Dict[str, datetime] = {}
        self.failed_attempts: Dict[str, list] = defaultdict(list)
        self.block_duration = timedelta(hours=1)
        self.max_attempts = 5  # Failed auth attempts before block
        self.attempt_window = timedelta(minutes=15)
    
    def is_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked."""
        if ip not in self.blocked_ips:
            return False
        
        # Check if block has expired
        if datetime.utcnow() > self.blocked_ips[ip]:
            del self.blocked_ips[ip]
            return False
        
        return True
    
    def record_failed_attempt(self, ip: str, reason: str = "auth"):
        """Record a failed authentication attempt."""
        now = datetime.utcnow()
        cutoff = now - self.attempt_window
        
        # Clean old attempts
        self.failed_attempts[ip] = [
            t for t in self.failed_attempts[ip] 
            if t > cutoff
        ]
        
        # Add new attempt
        self.failed_attempts[ip].append(now)
        
        # Check if should block
        if len(self.failed_attempts[ip]) >= self.max_attempts:
            self.blocked_ips[ip] = now + self.block_duration
            logger.critical(f"IP {ip} blocked for 1 hour due to {len(self.failed_attempts[ip])} failed {reason} attempts")
    
    def clear_failed_attempts(self, ip: str):
        """Clear failed attempts (on successful auth)."""
        if ip in self.failed_attempts:
            del self.failed_attempts[ip]


class RequestSecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for request tracking and hardening.
    
    Features:
    - Request ID generation for audit trails
    - IP blocking for brute force protection
    - Security timing headers to prevent info leakage
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.ip_block_list = IPBlockList()
        self._sensitive_paths = {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with security tracking."""
        
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        request.state.client_ip = client_ip
        
        # Check if IP is blocked (for sensitive endpoints)
        if self._is_sensitive_endpoint(request.url.path):
            if self.ip_block_list.is_blocked(client_ip):
                logger.warning(f"Blocked IP {client_ip} attempted access to {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access temporarily blocked due to security policy"},
                )
        
        # Track request timing
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Request-ID"] = request_id
        
        # Add timing noise to prevent timing attacks (vary by up to 10ms)
        process_time = time.time() - start_time
        noise = (uuid.uuid4().int % 10) / 1000  # 0-10ms noise
        response.headers["X-Response-Time"] = f"{process_time + noise:.3f}"
        
        # Log security events for sensitive endpoints
        if self._is_sensitive_endpoint(request.url.path):
            if response.status_code >= 400:
                self.ip_block_list.record_failed_attempt(client_ip, "auth")
            else:
                self.ip_block_list.clear_failed_attempts(client_ip)
        
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
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint is sensitive (auth-related)."""
        return any(sensitive in path for sensitive in self._sensitive_paths)


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def get_client_ip_from_request(request: Request) -> str:
    """Get client IP from request state."""
    return getattr(request.state, "client_ip", "unknown")
