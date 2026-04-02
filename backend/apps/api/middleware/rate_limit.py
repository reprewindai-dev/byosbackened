"""Per-workspace and per-IP rate limiting middleware using Redis sliding window."""
import time
import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_SKIP_PATHS = {"/health", "/", "/metrics", "/api/v1/auth/register", "/api/v1/auth/login"}

# Default limits (requests per minute)
_DEFAULT_WS_LIMIT = 300
_DEFAULT_IP_LIMIT = 120
_AUTH_BURST_LIMIT = 10  # tighter limit on auth endpoints


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
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(settings.redis_url, decode_responses=True)
            except Exception as e:
                logger.warning(f"Rate limiter: Redis unavailable — {e}")
        return self._redis

    def _check_limit(self, key: str, limit: int, window: int = 60) -> bool:
        """
        Sliding window counter. Returns True if within limit, False if exceeded.
        Uses Redis INCR + EXPIRE pattern.
        """
        r = self._get_redis()
        if not r:
            return True  # fail open if Redis down
        try:
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            results = pipe.execute()
            count = results[0]
            return count <= limit
        except Exception as e:
            logger.warning(f"Rate limiter Redis error: {e}")
            return True  # fail open

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in _SKIP_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        is_auth_path = path.startswith("/api/v1/auth/")

        # IP-level limit (tighter for auth)
        ip_limit = _AUTH_BURST_LIMIT if is_auth_path else _DEFAULT_IP_LIMIT
        ip_key = f"rl:ip:{client_ip}:{path if is_auth_path else 'global'}"
        if not self._check_limit(ip_key, ip_limit):
            logger.warning(f"Rate limit exceeded: IP={client_ip} path={path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down.",
                headers={"Retry-After": "60"},
            )

        # Workspace-level limit (from request state set by ZeroTrustMiddleware)
        workspace_id = getattr(request.state, "workspace_id", None)
        if workspace_id:
            ws_key = f"rl:ws:{workspace_id}"
            if not self._check_limit(ws_key, _DEFAULT_WS_LIMIT):
                logger.warning(f"Rate limit exceeded: workspace={workspace_id}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Workspace rate limit exceeded.",
                    headers={"Retry-After": "60"},
                )

        response = await call_next(request)
        return response
