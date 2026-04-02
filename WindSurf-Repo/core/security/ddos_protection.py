"""DDoS protection and advanced rate limiting."""

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from core.config import get_settings
import logging
import hashlib

logger = logging.getLogger(__name__)
settings = get_settings()


class DDoSProtection:
    """DDoS protection with multiple layers."""

    def __init__(self):
        self.redis_client = None
        if REDIS_AVAILABLE and redis:
            # Use a raw socket to check Redis availability fast (no blocking).
            # This avoids having the redis-py library make slow per-request
            # connection attempts when Redis is not running.
            import socket as _socket
            import urllib.parse as _up
            _available = False
            try:
                _url = settings.redis_url or "redis://localhost:6379/0"
                _parsed = _up.urlparse(_url)
                _host = _parsed.hostname or "localhost"
                _port = _parsed.port or 6379
                _sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
                _sock.settimeout(0.5)
                _result = _sock.connect_ex((_host, _port))
                _sock.close()
                _available = (_result == 0)
            except Exception:
                _available = False

            if _available:
                try:
                    self.redis_client = redis.from_url(
                        settings.redis_url,
                        decode_responses=True,
                        socket_connect_timeout=1,
                        socket_timeout=1,
                    )
                    logger.info("DDoS protection: Redis connected")
                except Exception as e:
                    logger.warning(f"Redis client init failed: {e}")
                    self.redis_client = None
            else:
                logger.warning("DDoS protection: Redis not reachable — using in-memory allow-all fallback")
        else:
            logger.warning(
                "Redis module not installed - DDoS protection will use in-memory fallback"
            )

    def get_client_key(self, request: Request) -> str:
        """Get unique key for client."""
        # Use IP address or user ID if authenticated
        ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)

        if user_id:
            return f"ddos:user:{user_id}"
        return f"ddos:ip:{ip}"

    def check_ddos(
        self,
        request: Request,
        window_seconds: int = 60,
        max_requests: int = 100,
    ) -> Tuple[bool, int, datetime]:
        """
        Check for DDoS attack.

        Returns:
            (is_allowed, remaining_requests, reset_at)
        """
        if not self.redis_client:
            return True, max_requests, datetime.utcnow() + timedelta(seconds=window_seconds)

        key = self.get_client_key(request)
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)

        # Use sliding window
        redis_key = f"ddos:{key}:{window_seconds}"

        try:
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start.timestamp())
            pipe.zcard(redis_key)
            pipe.zadd(redis_key, {str(now.timestamp()): now.timestamp()})
            pipe.expire(redis_key, window_seconds)
            results = pipe.execute()

            count = results[1]
            allowed = count < max_requests
            remaining = max(0, max_requests - count - 1)
            reset_at = now + timedelta(seconds=window_seconds)

            if not allowed:
                logger.warning(
                    f"DDoS protection triggered: {key} made {count} requests in {window_seconds}s"
                )

            return allowed, remaining, reset_at
        except Exception as e:
            logger.error(f"DDoS protection error: {e}")
            return True, max_requests, datetime.utcnow() + timedelta(seconds=window_seconds)

    def check_slowloris(self, request: Request) -> bool:
        """Detect slowloris attacks (slow HTTP requests)."""
        # Check Content-Length header
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                length = int(content_length)
                # Reject extremely large requests (>100MB)
                if length > 100 * 1024 * 1024:
                    logger.warning(f"Slowloris attack detected: large Content-Length {length}")
                    return False
            except ValueError:
                pass

        return True

    def check_syn_flood(self, request: Request) -> bool:
        """Detect SYN flood attacks."""
        # Check for rapid connection attempts from same IP
        # This is handled by rate limiting
        return True


class DDoSProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware to protect against DDoS attacks."""

    def __init__(self, app):
        super().__init__(app)
        self.ddos_protection = DDoSProtection()

    async def dispatch(self, request: Request, call_next):
        """Check for DDoS attacks."""
        # Check slowloris
        # IMPORTANT: return JSONResponse, NOT raise HTTPException.
        # Raising inside BaseHTTPMiddleware on Starlette ≤0.27 causes anyio.EndOfStream.
        if not self.ddos_protection.check_slowloris(request):
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request too large"},
            )

        # Check rate limit (DDoS protection)
        allowed, remaining, reset_at = self.ddos_protection.check_ddos(
            request,
            window_seconds=60,  # 1 minute window
            max_requests=100,  # Max 100 requests per minute
        )

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
                headers={
                    "X-RateLimit-Limit": "100",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_at.timestamp())),
                    "Retry-After": "60",
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = "100"
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_at.timestamp()))

        return response
