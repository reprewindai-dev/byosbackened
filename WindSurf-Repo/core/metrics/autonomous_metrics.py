"""Autonomous-specific metrics - cost, latency, routing decisions per workspace+region."""

from prometheus_client import Histogram, Counter, Gauge
from typing import Optional
from decimal import Decimal
import time

# Cost metrics per workspace + region
autonomous_cost_histogram = Histogram(
    "autonomous_cost",
    "Cost per operation",
    ["workspace_id", "region", "operation_type"],
    buckets=[0.0001, 0.001, 0.01, 0.1, 1.0, 10.0],
)

# Latency metrics per workspace + region
autonomous_latency_histogram = Histogram(
    "autonomous_latency_ms",
    "Latency per operation in milliseconds",
    ["workspace_id", "region", "operation_type"],
    buckets=[10, 50, 100, 500, 1000, 2000, 5000, 10000],
)

# Routing decision distribution
routing_decisions_total = Counter(
    "routing_decisions_total",
    "Total routing decisions made",
    [
        "workspace_id",
        "provider",
        "operation_type",
        "decision_type",
    ],  # decision_type: ml, rule_based, fallback
)

# Error rates by provider and operation type
routing_errors_total = Counter(
    "routing_errors_total",
    "Total routing errors",
    ["workspace_id", "provider", "operation_type", "error_type"],
)

# Anomaly counts
anomalies_detected_total = Counter(
    "anomalies_detected_total",
    "Total anomalies detected",
    ["workspace_id", "anomaly_type", "severity"],
)

anomalies_remediated_total = Counter(
    "anomalies_remediated_total",
    "Total anomalies remediated",
    ["workspace_id", "anomaly_type", "remediation_result"],  # remediation_result: success, failure
)

# Remediation outcomes
remediation_success_rate = Gauge(
    "remediation_success_rate",
    "Success rate of auto-remediation",
    ["workspace_id", "anomaly_type"],
)

# ML model metrics
ml_model_accuracy = Gauge(
    "ml_model_accuracy",
    "ML model accuracy (MAPE for cost, accuracy for quality)",
    [
        "workspace_id",
        "model_type",
    ],  # model_type: cost_predictor, quality_predictor, routing_optimizer
)

ml_model_training_samples = Gauge(
    "ml_model_training_samples",
    "Number of samples used for training",
    ["workspace_id", "model_type"],
)

# Edge routing metrics
edge_routing_decisions_total = Counter(
    "edge_routing_decisions_total",
    "Total edge routing decisions",
    [
        "workspace_id",
        "region",
        "routing_reason",
    ],  # routing_reason: latency, cost, data_residency, learned
)

edge_latency_histogram = Histogram(
    "edge_latency_ms",
    "Latency to edge regions",
    ["workspace_id", "region"],
    buckets=[10, 50, 100, 200, 500, 1000, 2000],
)

# Queue depth metrics
queue_depth_gauge = Gauge(
    "queue_depth",
    "Current queue depth (number of pending tasks)",
    ["workspace_id", "operation_type"],
)


class AutonomousMetrics:
    """Collect autonomous-specific metrics."""

    def record_cost(
        self,
        workspace_id: str,
        region: str,
        operation_type: str,
        cost: Decimal,
    ):
        """Record cost metric."""
        autonomous_cost_histogram.labels(
            workspace_id=workspace_id,
            region=region,
            operation_type=operation_type,
        ).observe(float(cost))

    def record_latency(
        self,
        workspace_id: str,
        region: str,
        operation_type: str,
        latency_ms: int,
    ):
        """Record latency metric."""
        autonomous_latency_histogram.labels(
            workspace_id=workspace_id,
            region=region,
            operation_type=operation_type,
        ).observe(float(latency_ms))

    def record_routing_decision(
        self,
        workspace_id: str,
        provider: str,
        operation_type: str,
        decision_type: str,  # "ml", "rule_based", "fallback"
    ):
        """Record routing decision."""
        routing_decisions_total.labels(
            workspace_id=workspace_id,
            provider=provider,
            operation_type=operation_type,
            decision_type=decision_type,
        ).inc()

    def record_routing_error(
        self,
        workspace_id: str,
        provider: str,
        operation_type: str,
        error_type: str,  # "timeout", "rate_limit", "provider_error"
    ):
        """Record routing error."""
        routing_errors_total.labels(
            workspace_id=workspace_id,
            provider=provider,
            operation_type=operation_type,
            error_type=error_type,
        ).inc()

    def record_anomaly(
        self,
        workspace_id: str,
        anomaly_type: str,
        severity: str,
    ):
        """Record anomaly detection."""
        anomalies_detected_total.labels(
            workspace_id=workspace_id,
            anomaly_type=anomaly_type,
            severity=severity,
        ).inc()

    def record_remediation(
        self,
        workspace_id: str,
        anomaly_type: str,
        success: bool,
    ):
        """Record remediation outcome."""
        result = "success" if success else "failure"
        anomalies_remediated_total.labels(
            workspace_id=workspace_id,
            anomaly_type=anomaly_type,
            remediation_result=result,
        ).inc()

    def update_remediation_success_rate(
        self,
        workspace_id: str,
        anomaly_type: str,
        success_rate: float,
    ):
        """Update remediation success rate gauge."""
        remediation_success_rate.labels(
            workspace_id=workspace_id,
            anomaly_type=anomaly_type,
        ).set(success_rate)

    def update_ml_model_metrics(
        self,
        workspace_id: str,
        model_type: str,
        accuracy: float,
        training_samples: int,
    ):
        """Update ML model metrics."""
        ml_model_accuracy.labels(
            workspace_id=workspace_id,
            model_type=model_type,
        ).set(accuracy)

        ml_model_training_samples.labels(
            workspace_id=workspace_id,
            model_type=model_type,
        ).set(float(training_samples))

    def record_edge_routing(
        self,
        workspace_id: str,
        region: str,
        routing_reason: str,
    ):
        """Record edge routing decision."""
        edge_routing_decisions_total.labels(
            workspace_id=workspace_id,
            region=region,
            routing_reason=routing_reason,
        ).inc()

    def record_edge_latency(
        self,
        workspace_id: str,
        region: str,
        latency_ms: int,
    ):
        """Record edge latency measurement."""
        edge_latency_histogram.labels(
            workspace_id=workspace_id,
            region=region,
        ).observe(float(latency_ms))

    def record_queue_depth(
        self,
        workspace_id: str,
        operation_type: str,
        queue_depth: int,
    ):
        """Record queue depth metric."""
        queue_depth_gauge.labels(
            workspace_id=workspace_id,
            operation_type=operation_type,
        ).set(float(queue_depth))


# Global autonomous metrics collector
_autonomous_metrics = AutonomousMetrics()


def get_autonomous_metrics() -> AutonomousMetrics:
    """Get global autonomous metrics instance."""
    return _autonomous_metrics
