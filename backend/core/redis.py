"""Redis connection utilities."""
import redis as redis_lib
from functools import lru_cache
from core.config import get_settings

settings = get_settings()


@lru_cache()
def get_redis() -> redis_lib.Redis:
    """Get cached Redis connection."""
    return redis_lib.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )


def get_redis_binary() -> redis_lib.Redis:
    """Get Redis connection without decoding (for binary data)."""
    return redis_lib.from_url(
        settings.redis_url,
        decode_responses=False,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
