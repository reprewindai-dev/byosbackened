"""
Cache Integration Middleware
===========================

Redis cache integration for FastAPI with automatic query caching,
session management, and performance optimization.
"""

import time
import logging
from typing import Callable, Any, Optional
from functools import wraps
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from core.cache.redis_cache import cache_service

logger = logging.getLogger(__name__)

class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic caching and performance optimization."""
    
    def __init__(self, app, cache_ttl: int = 300):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.cacheable_methods = {"GET"}
        self.cacheable_paths = {
            "/api/v1/dashboard/stats",
            "/api/v1/dashboard/system-status",
            "/api/v1/ai/providers",
            "/api/v1/workspaces",
            "/api/v1/billing/report"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Check cache for GET requests
        if request.method in self.cacheable_methods:
            cached_response = await cache_service.get(cache_key)
            if cached_response:
                logger.debug(f"Cache hit: {request.url}")
                return Response(
                    content=cached_response["content"],
                    status_code=cached_response["status_code"],
                    headers=cached_response["headers"],
                    media_type=cached_response["media_type"]
                )
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Cache GET responses
        if (
            request.method in self.cacheable_methods and
            response.status_code == 200 and
            request.url.path in self.cacheable_paths
        ):
            cache_data = {
                "content": response.body,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "media_type": response.media_type
            }
            await cache_service.set(cache_key, cache_data, self.cache_ttl)
            logger.debug(f"Cached response: {request.url} (took {process_time:.3f}s)")
        
        # Add cache headers
        response.headers["X-Process-Time"] = str(process_time)
        if cache_service.redis_client:
            response.headers["X-Cache-Status"] = "Redis"
        else:
            response.headers["X-Cache-Status"] = "Fallback"
        
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        path = request.url.path
        query_params = str(sorted(request.query_params.items()))
        user_id = getattr(request.state, "user_id", "anonymous")
        workspace_id = getattr(request.state, "workspace_id", "default")
        
        key_data = f"{path}:{query_params}:{user_id}:{workspace_id}"
        return cache_service._generate_key("http", cache_service._hash_data(key_data))

def cached_endpoint(ttl: int = 300, prefix: str = "endpoint"):
    """Decorator for caching FastAPI endpoints."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            cache_key_data = {
                "func": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            cache_key = cache_service._generate_key(prefix, cache_service._hash_data(cache_key_data))
            
            # Try cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for endpoint: {func.__name__}")
                return cached_result
            
            # Execute and cache
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl)
            logger.debug(f"Cached endpoint result: {func.__name__}")
            return result
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str):
    """Decorator to invalidate cache pattern after function execution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            result = await func(*args, **kwargs)
            
            # Invalidate cache pattern
            await cache_service.clear_pattern(f"byos:*{pattern}*")
            logger.debug(f"Invalidated cache pattern: {pattern}")
            
            return result
        return wrapper
    return decorator
