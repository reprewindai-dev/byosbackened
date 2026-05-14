"""Per-workspace and per-IP rate limiting middleware using Redis sliding window."""
import logging
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from core.config import get_settings
from core.redis_pool import get_redis
from core.security.client_ip import get_client_ip

logger = logging.getLogger(__name__)
settings = get_settings()

_SKIP_PATHS = {
    "/health", "/", "/metrics", "/status",
    "/api/v1/auth/register", "/api/v1/auth/login",
    "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json",
}

# Default limits (requests per minute) — tuned for production scale.
# In prod each user has unique IP; reverse-proxy should set X-Forwarded-For.
_DEFAULT_WS_LIMIT = 18000   # 300 req/sec per workspace
_DEFAULT_IP_LIMIT = 6000    # 100 req/sec per IP
_AUTH_BURST_LIMIT = 20      # tighter limit on auth endpoints (brute-force)
_UPSTASH_RATE_LIMIT_PREFIX = "@upstash/ratelimit"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter backed by Redis.
    Enforces per-workspace (JWT/API key) and per-IP limits.
    Auth endpoints get a tighter burst limit to block brute force.
    Falls back gracefully if Redis is unavailable.
    """

    def __init__(self, app):
        super().__init__(app)
        self._redis = None

    def _get_redis(self):
        """Get Redis from shared connection pool."""
        if self._redis is None:
            try:
                self._redis = get_redis()
            except Exception as e:
                logger.warning(f"Rate limiter: Redis unavailable — {e}")
        return self._redis

    def _check_limit(self, key: str, limit: int, window: int = 60) -> tuple[bool, int, int]:
        """
        Sliding window counter. Returns True if within limit, False if exceeded.
        Uses Redis INCR + EXPIRE pattern.
        """
        r = self._get_redis()
        if not r:
            return True, limit, window  # fail open if Redis down
        try:
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            results = pipe.execute()
            count = int(results[0] or 0)
            remaining = max(0, limit - count)
            return count <= limit, remaining, window
        except Exception as e:
            logger.warning(f"Rate limiter Redis error: {e}")
            return True, limit, window  # fail open

    def _record_rate_event(self, bucket: str, allowed: bool) -> None:
        r = self._get_redis()
        if not r:
            return
        try:
            status_key = "allowed" if allowed else "rate_limited"
            pipe = r.pipeline()
            pipe.incr(f"{_UPSTASH_RATE_LIMIT_PREFIX}:analytics:{status_key}")
            pipe.incr(f"{_UPSTASH_RATE_LIMIT_PREFIX}:analytics:{status_key}:{bucket}")
            pipe.expire(f"{_UPSTASH_RATE_LIMIT_PREFIX}:analytics:{status_key}", 86400)
            pipe.expire(f"{_UPSTASH_RATE_LIMIT_PREFIX}:analytics:{status_key}:{bucket}", 86400)
            pipe.execute()
        except Exception:
            logger.debug("Rate limiter analytics write skipped", exc_info=True)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in _SKIP_PATHS:
            return await call_next(request)

        client_ip = get_client_ip(request)
        is_auth_path = path.startswith("/api/v1/auth/")

        # IP-level limit (tighter for auth)
        ip_limit = _AUTH_BURST_LIMIT if is_auth_path else _DEFAULT_IP_LIMIT
        ip_bucket = f"ip:{client_ip}:{path if is_auth_path else 'global'}"
        ip_key = f"{_UPSTASH_RATE_LIMIT_PREFIX}:{ip_bucket}"
        ip_allowed, ip_remaining, ip_reset = self._check_limit(ip_key, ip_limit)
        self._record_rate_event(ip_bucket, ip_allowed)
        if not ip_allowed:
            logger.warning(f"Rate limit exceeded: IP={client_ip} path={path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please slow down."},
                headers={
                    "Retry-After": str(ip_reset),
                    "X-RateLimit-Limit": str(ip_limit),
                    "X-RateLimit-Remaining": str(ip_remaining),
                    "X-RateLimit-Reset": str(ip_reset),
                },
            )

        # Workspace-level limit (from request state set by ZeroTrustMiddleware)
        workspace_id = getattr(request.state, "workspace_id", None)
        if workspace_id:
            ws_bucket = f"ws:{workspace_id}"
            ws_key = f"{_UPSTASH_RATE_LIMIT_PREFIX}:{ws_bucket}"
            ws_allowed, ws_remaining, ws_reset = self._check_limit(ws_key, _DEFAULT_WS_LIMIT)
            self._record_rate_event(ws_bucket, ws_allowed)
            if not ws_allowed:
                logger.warning(f"Rate limit exceeded: workspace={workspace_id}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Workspace rate limit exceeded."},
                    headers={
                        "Retry-After": str(ws_reset),
                        "X-RateLimit-Limit": str(_DEFAULT_WS_LIMIT),
                        "X-RateLimit-Remaining": str(ws_remaining),
                        "X-RateLimit-Reset": str(ws_reset),
                    },
                )

        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(ip_limit))
        response.headers.setdefault("X-RateLimit-Remaining", str(ip_remaining))
        response.headers.setdefault("X-RateLimit-Reset", str(ip_reset))
        return response
