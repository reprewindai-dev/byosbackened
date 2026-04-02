"""
Performance Optimization System
==============================

Comprehensive performance optimization including query optimization,
connection pooling, and performance monitoring.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from fastapi import Request, Response
import redis.asyncio as redis

from core.config import get_settings
from core.cache.redis_cache import cache_service

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    query_count: int = 0
    total_query_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    slow_queries: List[Dict[str, Any]] = None
    connection_pool_stats: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.slow_queries is None:
            self.slow_queries = []
        if self.connection_pool_stats is None:
            self.connection_pool_stats = {}

class DatabaseOptimizer:
    """Database performance optimization."""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self.metrics = PerformanceMetrics()
        self.slow_query_threshold = 1.0  # seconds
    
    def create_optimized_engine(self) -> Engine:
        """Create optimized database engine with connection pooling."""
        # Engine configuration for PostgreSQL
        engine_config = {
            "url": self.settings.database_url,
            "poolclass": QueuePool,
            "pool_size": 20,  # Base connection pool size
            "max_overflow": 30,  # Additional connections under load
            "pool_timeout": 30,  # Timeout to get connection from pool
            "pool_recycle": 3600,  # Recycle connections every hour
            "pool_pre_ping": True,  # Validate connections before use
            "echo": False,  # Set to True for SQL logging in debug
            "future": True,  # Use SQLAlchemy 2.0 style
            "isolation_level": "READ_COMMITTED",  # Appropriate isolation level
        }
        
        # Add PostgreSQL-specific optimizations
        if "postgresql" in self.settings.database_url:
            engine_config.update({
                "connect_args": {
                    "application_name": "sovereign_ai backend",
                    "connect_timeout": 10,
                    "command_timeout": 30,
                    "server_settings": {
                        "jit": "off",  # Disable JIT for small queries
                        "statement_timeout": "30000",  # 30 second query timeout
                        "idle_in_transaction_session_timeout": "60000",  # 1 minute
                    }
                }
            })
        
        self.engine = create_engine(**engine_config)
        
        # Register event listeners for monitoring
        self._register_event_listeners()
        
        # Create session factory
        self.session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )
        
        logger.info("✅ Optimized database engine created")
        return self.engine
    
    def _register_event_listeners(self):
        """Register SQLAlchemy event listeners for monitoring."""
        
        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_start_time'):
                query_time = time.time() - context._query_start_time
                self.metrics.query_count += 1
                self.metrics.total_query_time += query_time
                
                # Track slow queries
                if query_time > self.slow_query_threshold:
                    slow_query = {
                        "statement": statement[:200] + "..." if len(statement) > 200 else statement,
                        "parameters": str(parameters)[:100],
                        "execution_time": query_time,
                        "timestamp": time.time()
                    }
                    self.metrics.slow_queries.append(slow_query)
                    
                    # Keep only last 100 slow queries
                    if len(self.metrics.slow_queries) > 100:
                        self.metrics.slow_queries.pop(0)
                    
                    logger.warning(f"Slow query detected ({query_time:.3f}s): {statement[:100]}...")
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session with automatic cleanup."""
        if not self.session_factory:
            raise RuntimeError("Database engine not initialized")
        
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def execute_optimized_query(
        self, 
        session: Session, 
        query: str, 
        params: Dict[str, Any] = None,
        cache_ttl: int = 300
    ) -> Any:
        """Execute query with caching and optimization."""
        # Generate cache key
        cache_key = f"query:{hash(query)}:{hash(str(params))}"
        
        # Try cache first
        cached_result = await cache_service.get(cache_key)
        if cached_result is not None:
            self.metrics.cache_hits += 1
            return cached_result
        
        self.metrics.cache_misses += 1
        
        # Execute query
        start_time = time.time()
        result = session.execute(text(query), params or {})
        query_time = time.time() - start_time
        
        # Cache result if appropriate
        if query_time < 0.5 and cache_ttl > 0:  # Only cache fast queries
            await cache_service.set(cache_key, result.fetchall(), cache_ttl)
        
        return result
    
    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if not self.engine or not self.engine.pool:
            return {}
        
        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            "pool_timeout": pool.timeout(),
            "recycle_time": pool._recycle_time
        }
    
    async def analyze_slow_queries(self) -> Dict[str, Any]:
        """Analyze slow queries and provide optimization suggestions."""
        if not self.metrics.slow_queries:
            return {"message": "No slow queries detected"}
        
        # Group by query pattern
        query_patterns = {}
        for query in self.metrics.slow_queries:
            pattern = query["statement"][:50]  # First 50 chars as pattern
            if pattern not in query_patterns:
                query_patterns[pattern] = {
                    "count": 0,
                    "total_time": 0,
                    "avg_time": 0,
                    "max_time": 0,
                    "examples": []
                }
            
            pattern_data = query_patterns[pattern]
            pattern_data["count"] += 1
            pattern_data["total_time"] += query["execution_time"]
            pattern_data["max_time"] = max(pattern_data["max_time"], query["execution_time"])
            pattern_data["avg_time"] = pattern_data["total_time"] / pattern_data["count"]
            
            if len(pattern_data["examples"]) < 3:
                pattern_data["examples"].append(query["statement"])
        
        # Generate optimization suggestions
        suggestions = []
        for pattern, data in query_patterns.items():
            if data["count"] > 5 and data["avg_time"] > 2.0:
                suggestions.append({
                    "pattern": pattern,
                    "issue": "Frequently slow query",
                    "suggestion": "Consider adding an index or optimizing the query",
                    "impact": f"Runs {data['count']} times with avg {data['avg_time']:.2f}s"
                })
        
        return {
            "total_slow_queries": len(self.metrics.slow_queries),
            "query_patterns": query_patterns,
            "optimization_suggestions": suggestions
        }

class QueryOptimizer:
    """Query optimization utilities."""
    
    @staticmethod
    def optimize_select_query(table: str, columns: List[str], 
                             where_clause: str = None, 
                             order_by: str = None,
                             limit: int = None,
                             offset: int = None) -> str:
        """Generate optimized SELECT query."""
        query_parts = [f"SELECT {', '.join(columns)} FROM {table}"]
        
        if where_clause:
            query_parts.append(f"WHERE {where_clause}")
        
        if order_by:
            query_parts.append(f"ORDER BY {order_by}")
        
        if limit:
            query_parts.append(f"LIMIT {limit}")
        
        if offset:
            query_parts.append(f"OFFSET {offset}")
        
        return " ".join(query_parts)
    
    @staticmethod
    def add_query_hints(query: str, hints: List[str]) -> str:
        """Add query hints for optimization."""
        if not hints:
            return query
        
        hint_str = "/* " + " ".join(hints) + " */"
        return f"{hint_str} {query}"
    
    @staticmethod
    def create_index_suggestion(table: str, columns: List[str], 
                               query_type: str = "btree") -> str:
        """Generate index creation suggestion."""
        index_name = f"idx_{table}_{'_'.join(columns)}"
        columns_str = ", ".join(columns)
        return f"CREATE INDEX CONCURRENTLY {index_name} ON {table} USING {query_type} ({columns_str});"

class PerformanceMonitor:
    """Performance monitoring and metrics."""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.request_times: List[float] = []
        self.endpoint_stats: Dict[str, Dict[str, float]] = {}
    
    async def track_request(self, request: Request, response: Response):
        """Track request performance."""
        # Get request processing time
        process_time = float(response.headers.get("X-Process-Time", 0))
        
        self.request_times.append(process_time)
        
        # Keep only last 1000 request times
        if len(self.request_times) > 1000:
            self.request_times.pop(0)
        
        # Track endpoint stats
        endpoint = request.url.path
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
                "max_time": 0,
                "min_time": float('inf')
            }
        
        stats = self.endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_time"] += process_time
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["max_time"] = max(stats["max_time"], process_time)
        stats["min_time"] = min(stats["min_time"], process_time)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.request_times:
            return {"message": "No performance data available"}
        
        # Calculate statistics
        avg_time = sum(self.request_times) / len(self.request_times)
        max_time = max(self.request_times)
        min_time = min(self.request_times)
        
        # Calculate percentiles
        sorted_times = sorted(self.request_times)
        p50 = sorted_times[len(sorted_times) // 2]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        return {
            "requests": {
                "total": len(self.request_times),
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "p50": p50,
                "p95": p95,
                "p99": p99
            },
            "database": {
                "query_count": self.metrics.query_count,
                "avg_query_time": self.metrics.total_query_time / max(1, self.metrics.query_count),
                "cache_hits": self.metrics.cache_hits,
                "cache_misses": self.metrics.cache_misses,
                "cache_hit_rate": self.metrics.cache_hits / max(1, self.metrics.cache_hits + self.metrics.cache_misses) * 100
            },
            "slow_queries": len(self.metrics.slow_queries),
            "connection_pool": self.metrics.connection_pool_stats,
            "top_endpoints": sorted(
                self.endpoint_stats.items(),
                key=lambda x: x[1]["avg_time"],
                reverse=True
            )[:10]
        }

class CacheOptimizer:
    """Cache optimization strategies."""
    
    def __init__(self):
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    async def optimize_cache_strategy(self, endpoint: str, 
                                    response_time: float,
                                    cache_ttl: int = 300) -> int:
        """Dynamically optimize cache TTL based on performance."""
        # Increase cache TTL for slow endpoints
        if response_time > 1.0:
            return min(cache_ttl * 2, 3600)  # Max 1 hour
        # Decrease cache TTL for fast endpoints
        elif response_time < 0.1:
            return max(cache_ttl // 2, 60)  # Min 1 minute
        
        return cache_ttl
    
    async def warm_cache(self, endpoints: List[str]):
        """Warm up cache for frequently accessed endpoints."""
        for endpoint in endpoints:
            try:
                # This would make actual requests to warm cache
                logger.info(f"Warming cache for endpoint: {endpoint}")
            except Exception as e:
                logger.error(f"Failed to warm cache for {endpoint}: {e}")

# Global instances
db_optimizer = DatabaseOptimizer()
query_optimizer = QueryOptimizer()
performance_monitor = PerformanceMonitor()
cache_optimizer = CacheOptimizer()

# Performance monitoring middleware
class PerformanceMiddleware:
    """Middleware for performance monitoring."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Start timing
        start_time = time.time()
        
        # Process request
        await self.app(scope, receive, send)
        
        # Track performance
        process_time = time.time() - start_time
        
        # This would be integrated with FastAPI request/response handling
        logger.debug(f"Request processed in {process_time:.3f}s")

# Decorator for performance monitoring
def monitor_performance(func: Callable) -> Callable:
    """Decorator to monitor function performance."""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 1.0:
                logger.warning(f"Slow function {func.__name__}: {execution_time:.3f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper

async def initialize_performance_optimization():
    """Initialize performance optimization systems."""
    # Create optimized database engine
    db_optimizer.create_optimized_engine()
    
    # Initialize cache
    await cache_service.connect()
    
    logger.info("✅ Performance optimization initialized")

async def get_performance_metrics() -> Dict[str, Any]:
    """Get comprehensive performance metrics."""
    return {
        "database": db_optimizer.metrics.__dict__,
        "connection_pool": db_optimizer.get_connection_pool_stats(),
        "performance": performance_monitor.get_performance_summary(),
        "cache": await cache_service.get_cache_stats()
    }
