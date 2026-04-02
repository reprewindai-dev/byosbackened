"""
Redis Caching Service for BYOS AI Backend
==========================================

Comprehensive Redis-based caching system for performance optimization
including query result caching, session management, and rate limiting.
"""

import json
import pickle
import hashlib
import logging
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
from functools import wraps
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import asyncio

from core.config import get_settings

logger = logging.getLogger(__name__)

class RedisCache:
    """Production-ready Redis caching service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[ConnectionPool] = None
        self.default_ttl = 3600  # 1 hour
        self.session_ttl = 86400  # 24 hours
        self.rate_limit_ttl = 60  # 1 minute
        
    async def connect(self) -> bool:
        """Initialize Redis connection with connection pooling."""
        try:
            # Create connection pool
            self.connection_pool = ConnectionPool.from_url(
                self.settings.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30
            )
            
            # Create Redis client
            self.redis_client = redis.Redis(
                connection_pool=self.connection_pool,
                decode_responses=False  # Handle binary data
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            # Fallback to in-memory cache
            self._fallback_cache = {}
            logger.warning("⚠️  Using in-memory fallback cache")
            return False
    
    async def disconnect(self):
        """Close Redis connections."""
        if self.redis_client:
            await self.redis_client.close()
        if self.connection_pool:
            await self.connection_pool.disconnect()
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key with namespace."""
        return f"byos:{prefix}:{identifier}"
    
    def _hash_data(self, data: Any) -> str:
        """Generate hash for cache key."""
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis_client:
                data = await self.redis_client.get(key)
                if data:
                    return pickle.loads(data)
            else:
                # Fallback to in-memory
                return self._fallback_cache.get(key)
            return None
        except Exception as e:
            logger.error(f"❌ Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL."""
        try:
            ttl = ttl or self.default_ttl
            serialized = pickle.dumps(value)
            
            if self.redis_client:
                await self.redis_client.setex(key, ttl, serialized)
            else:
                # Fallback to in-memory
                self._fallback_cache[key] = value
            return True
        except Exception as e:
            logger.error(f"❌ Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if self.redis_client:
                await self.redis_client.delete(key)
            else:
                # Fallback to in-memory
                self._fallback_cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"❌ Cache delete error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        try:
            if self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"❌ Cache clear pattern error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            if self.redis_client:
                return bool(await self.redis_client.exists(key))
            else:
                return key in self._fallback_cache
        except Exception as e:
            logger.error(f"❌ Cache exists error: {e}")
            return False
    
    # Specialized cache methods
    
    async def cache_query_result(self, query: str, result: Any, ttl: int = 3600) -> bool:
        """Cache database query result."""
        query_hash = self._hash_data(query)
        key = self._generate_key("query", query_hash)
        return await self.set(key, result, ttl)
    
    async def get_cached_query(self, query: str) -> Optional[Any]:
        """Get cached query result."""
        query_hash = self._hash_data(query)
        key = self._generate_key("query", query_hash)
        return await self.get(key)
    
    async def cache_ai_response(self, prompt: str, response: Any, ttl: int = 7200) -> bool:
        """Cache AI model response."""
        prompt_hash = self._hash_data(prompt)
        key = self._generate_key("ai_response", prompt_hash)
        return await self.set(key, response, ttl)
    
    async def get_cached_ai_response(self, prompt: str) -> Optional[Any]:
        """Get cached AI response."""
        prompt_hash = self._hash_data(prompt)
        key = self._generate_key("ai_response", prompt_hash)
        return await self.get(key)
    
    async def cache_user_session(self, user_id: str, session_data: Dict) -> bool:
        """Cache user session data."""
        key = self._generate_key("session", user_id)
        return await self.set(key, session_data, self.session_ttl)
    
    async def get_user_session(self, user_id: str) -> Optional[Dict]:
        """Get cached user session."""
        key = self._generate_key("session", user_id)
        return await self.get(key)
    
    async def cache_workspace_data(self, workspace_id: str, data: Any, ttl: int = 1800) -> bool:
        """Cache workspace data."""
        key = self._generate_key("workspace", workspace_id)
        return await self.set(key, data, ttl)
    
    async def get_cached_workspace_data(self, workspace_id: str) -> Optional[Any]:
        """Get cached workspace data."""
        key = self._generate_key("workspace", workspace_id)
        return await self.get(key)
    
    async def rate_limit_check(self, identifier: str, limit: int, window: int = 60) -> tuple[bool, int]:
        """Check rate limit with sliding window."""
        key = self._generate_key("rate_limit", identifier)
        current_time = int(datetime.now().timestamp())
        
        try:
            if self.redis_client:
                # Remove old entries
                await self.redis_client.zremrangebyscore(key, 0, current_time - window)
                
                # Count current requests
                count = await self.redis_client.zcard(key)
                
                if count < limit:
                    # Add current request
                    await self.redis_client.zadd(key, {str(current_time): current_time})
                    await self.redis_client.expire(key, window)
                    return True, limit - count - 1
                else:
                    return False, 0
            else:
                # Fallback to simple in-memory rate limiting
                return True, limit - 1
                
        except Exception as e:
            logger.error(f"❌ Rate limit error: {e}")
            return True, limit - 1  # Allow on error
    
    async def cache_dashboard_stats(self, workspace_id: str, stats: Dict, ttl: int = 300) -> bool:
        """Cache dashboard statistics."""
        key = self._generate_key("dashboard", workspace_id)
        return await self.set(key, stats, ttl)
    
    async def get_cached_dashboard_stats(self, workspace_id: str) -> Optional[Dict]:
        """Get cached dashboard stats."""
        key = self._generate_key("dashboard", workspace_id)
        return await self.get(key)
    
    async def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all cache entries for a user."""
        patterns = [
            f"byos:session:*{user_id}*",
            f"byos:dashboard:*{user_id}*",
            f"byos:user:*{user_id}*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            total_deleted += await self.clear_pattern(pattern)
        
        return total_deleted
    
    async def invalidate_workspace_cache(self, workspace_id: str) -> int:
        """Invalidate all cache entries for a workspace."""
        patterns = [
            f"byos:workspace:*{workspace_id}*",
            f"byos:dashboard:*{workspace_id}*",
            f"byos:query:*{workspace_id}*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            total_deleted += await self.clear_pattern(pattern)
        
        return total_deleted
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            if self.redis_client:
                info = await self.redis_client.info()
                return {
                    "connected": True,
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "hit_rate": (
                        info.get("keyspace_hits", 0) / 
                        max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
                    ) * 100
                }
            else:
                return {
                    "connected": False,
                    "fallback_cache_size": len(getattr(self, '_fallback_cache', {})),
                    "status": "Using in-memory fallback"
                }
        except Exception as e:
            logger.error(f"❌ Cache stats error: {e}")
            return {"connected": False, "error": str(e)}

# Global cache instance
cache_service = RedisCache()

# Decorators for easy caching

def cache_result(ttl: int = 3600, prefix: str = "result"):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_data = {
                "func": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            cache_key = cache_service._generate_key(prefix, cache_service._hash_data(cache_key_data))
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

def rate_limit(limit: int, window: int = 60):
    """Decorator for rate limiting."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get identifier (could be IP, user ID, etc.)
            identifier = kwargs.get("user_id", "anonymous")
            
            # Check rate limit
            allowed, remaining = await cache_service.rate_limit_check(identifier, limit, window)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {window} seconds."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

async def init_cache():
    """Initialize cache service."""
    success = await cache_service.connect()
    if success:
        logger.info("✅ Redis cache service initialized")
    else:
        logger.warning("⚠️  Redis unavailable, using fallback cache")
    return success
