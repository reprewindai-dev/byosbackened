"""Metrics middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from core.metrics import get_metrics_collector
import time

metrics_collector = get_metrics_collector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request metrics."""

    async def dispatch(self, request: Request, call_next):
        """Track request duration and status."""
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Record metrics
        metrics_collector.record_request(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            duration=duration,
        )
        
        return response
