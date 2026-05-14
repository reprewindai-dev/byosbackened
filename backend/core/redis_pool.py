"""
Centralized Redis connection pool for BYOS backend.

Provides a shared connection pool for high-concurrency scenarios.
Prevents connection exhaustion at scale (5000+ concurrent users).
"""
import redis
from core.config import get_settings
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
settings = get_settings()

# Global connection pool - shared across all modules
_redis_pool: redis.Redis = None
_upstash_rest_pool = None


class RestRedisPipeline:
    """Small pipeline adapter for Upstash Redis REST clients."""

    def __init__(self, client):
        self.client = client
        self.operations = []

    def incr(self, key: str):
        self.operations.append(("incr", (key,), {}))
        return self

    def expire(self, key: str, seconds: int):
        self.operations.append(("expire", (key, seconds), {}))
        return self

    def execute(self):
        results = []
        for method, args, kwargs in self.operations:
            results.append(getattr(self.client, method)(*args, **kwargs))
        self.operations = []
        return results


class RestRedisAdapter:
    """Compatibility wrapper for the subset of Redis APIs this app uses."""

    def __init__(self, client):
        self.client = client

    def pipeline(self):
        return RestRedisPipeline(self.client)

    def incr(self, key: str):
        return self.client.incr(key)

    def expire(self, key: str, seconds: int):
        return self.client.expire(key, seconds)

    def setex(self, key: str, seconds: int, value: str):
        return self.client.set(key, value, ex=seconds)

    def set(self, key: str, value: str, ex: int | None = None):
        return self.client.set(key, value, ex=ex)

    def get(self, key: str):
        return self.client.get(key)

    def lpush(self, key: str, value: str):
        return self.client.lpush(key, value)

    def ltrim(self, key: str, start: int, stop: int):
        return self.client.ltrim(key, start, stop)

    def lrange(self, key: str, start: int, stop: int):
        return self.client.lrange(key, start, stop)

    def publish(self, key: str, value: str):
        logger.debug("Upstash Redis REST publish skipped for channel=%s", key)
        return 0

    def ping(self):
        result = self.client.ping()
        return bool(result)

    def close(self):
        return None


def get_upstash_rest_redis():
    """Get an Upstash Redis REST client adapter."""
    global _upstash_rest_pool
    if _upstash_rest_pool is None:
        if not settings.upstash_redis_rest_url or not settings.upstash_redis_rest_token:
            raise redis.ConnectionError("Upstash Redis REST credentials are not configured")
        try:
            from upstash_redis import Redis
        except Exception as exc:
            raise redis.ConnectionError("upstash-redis package is not installed") from exc
        _upstash_rest_pool = RestRedisAdapter(
            Redis(url=settings.upstash_redis_rest_url, token=settings.upstash_redis_rest_token)
        )
        logger.info("[RedisPool] Initialized Upstash Redis REST fallback")
    return _upstash_rest_pool


def get_redis() -> redis.Redis:
    """
    Get Redis client from shared connection pool.
    
    Uses connection pooling for efficient resource usage at scale.
    Thread-safe and async-safe.
    """
    global _redis_pool
    
    if _redis_pool is None:
        parsed = urlparse(settings.redis_url or "")
        inside_docker = Path("/.dockerenv").exists() or os.getenv("DOCKER_CONTAINER") == "true"
        if parsed.hostname == "redis" and not inside_docker:
            return get_upstash_rest_redis()
        _redis_pool = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.75,
            max_connections=100,  # Support 100 concurrent connections
            retry_on_timeout=False,
            health_check_interval=30,
        )
        logger.info("[RedisPool] Initialized connection pool (max_connections=100)")
    
    return _redis_pool


def close_redis_pool():
    """Close all connections in the pool - call on shutdown."""
    global _redis_pool
    if _redis_pool:
        _redis_pool.close()
        _redis_pool = None
    global _upstash_rest_pool
    if _upstash_rest_pool:
        _upstash_rest_pool.close()
        _upstash_rest_pool = None
        logger.info("[RedisPool] Connection pool closed")


def check_redis_health() -> bool:
    """Check if Redis is reachable."""
    try:
        r = get_redis()
        return r.ping()
    except Exception as e:
        logger.warning(f"[RedisPool] Health check failed: {e}")
        return False
