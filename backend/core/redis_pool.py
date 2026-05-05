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
            raise redis.ConnectionError("Redis service hostname is only resolvable inside the container network")
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
        logger.info("[RedisPool] Connection pool closed")


def check_redis_health() -> bool:
    """Check if Redis is reachable."""
    try:
        r = get_redis()
        return r.ping()
    except Exception as e:
        logger.warning(f"[RedisPool] Health check failed: {e}")
        return False
