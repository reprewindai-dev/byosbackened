"""Prometheus metrics collector."""

from prometheus_client import Counter, Histogram, Gauge
from typing import Optional
import time

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# Job metrics
job_duration_seconds = Histogram(
    "job_duration_seconds",
    "Job duration",
    ["job_type", "status"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

# AI provider metrics
ai_provider_calls_total = Counter(
    "ai_provider_calls_total",
    "Total AI provider calls",
    ["provider", "operation", "status"],
)

# Usage metrics
usage_metrics = Gauge(
    "usage_metrics",
    "Usage metrics",
    ["workspace_id", "metric_type"],
)


class MetricsCollector:
    """Collect and expose metrics."""

    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request."""
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

    def record_job(self, job_type: str, status: str, duration: float):
        """Record job execution."""
        job_duration_seconds.labels(job_type=job_type, status=status).observe(duration)

    def record_ai_call(self, provider: str, operation: str, status: str):
        """Record AI provider call."""
        ai_provider_calls_total.labels(provider=provider, operation=operation, status=status).inc()

    def record_usage(self, workspace_id: str, metric_type: str, value: float):
        """Record usage metric."""
        usage_metrics.labels(workspace_id=workspace_id, metric_type=metric_type).set(value)


# Global metrics collector
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get metrics collector instance."""
    return _metrics_collector
