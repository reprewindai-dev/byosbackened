"""Advanced rate limiting."""
import redis
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimiter:
    """Redis-based rate limiter with sliding window."""

    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> Tuple[bool, int, datetime]:
        """
        Check rate limit.
        
        Returns:
        - allowed: bool
        - remaining: int
        - reset_at: datetime
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Use sliding window algorithm
        redis_key = f"rate_limit:{key}:{window_seconds}"
        
        # Count requests in window
        pipe = self.redis_client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, window_start.timestamp())
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {str(now.timestamp()): now.timestamp()})
        pipe.expire(redis_key, window_seconds)
        results = pipe.execute()
        
        count = results[1]
        allowed = count < limit
        remaining = max(0, limit - count - 1)  # -1 because we just added current request
        reset_at = now + timedelta(seconds=window_seconds)
        
        return allowed, remaining, reset_at

    def check_multi_window(
        self,
        key: str,
        limits: Dict[str, int],  # {"minute": 60, "hour": 1000, "day": 10000}
    ) -> Tuple[bool, int, datetime]:
        """
        Check rate limit across multiple windows.
        
        Returns most restrictive limit.
        """
        results = []
        for window_name, limit in limits.items():
            window_seconds = {
                "minute": 60,
                "hour": 3600,
                "day": 86400,
            }.get(window_name, 60)
            
            allowed, remaining, reset_at = self.check_rate_limit(
                f"{key}:{window_name}",
                limit,
                window_seconds,
            )
            results.append((allowed, remaining, reset_at))
        
        # Return most restrictive (first False, or lowest remaining)
        if not all(r[0] for r in results):
            # At least one limit exceeded
            failed = [r for r in results if not r[0]]
            return False, failed[0][1], failed[0][2]
        
        # All passed, return lowest remaining
        min_remaining = min(r[1] for r in results)
        min_reset = min(r[2] for r in results, key=lambda x: x.timestamp())
        return True, min_remaining, min_reset
