"""JSONB field validators - use these before saving to database."""
from typing import Dict, Optional, Any
from core.autonomous.schemas.routing_strategy import validate_provider_weights
from core.autonomous.schemas.traffic_pattern import validate_pattern_data
from core.autonomous.schemas.anomaly import validate_anomaly_metadata
from core.autonomous.schemas.savings_report import (
    validate_breakdown_by_operation,
    validate_breakdown_by_provider,
)


def validate_routing_strategy_jsonb(
    provider_weights: Optional[Dict[str, float]],
) -> Optional[Dict[str, float]]:
    """
    Validate provider_weights JSONB field for RoutingStrategy.
    
    Usage:
        strategy = RoutingStrategy(
            workspace_id=workspace_id,
            operation_type="transcribe",
            provider_weights=validate_routing_strategy_jsonb({"openai": 0.7, "huggingface": 0.3}),
        )
    """
    if provider_weights is None:
        return None
    return validate_provider_weights(provider_weights)


def validate_traffic_pattern_jsonb(
    pattern_data: Dict[str, Any],
    pattern_type: str,
) -> Dict[str, Any]:
    """
    Validate pattern_data JSONB field for TrafficPattern.
    
    Usage:
        pattern = TrafficPattern(
            workspace_id=workspace_id,
            pattern_type="daily",
            pattern_data=validate_traffic_pattern_jsonb({"hour": 10, "count": 50}, "daily"),
        )
    """
    return validate_pattern_data(pattern_data, pattern_type)


def validate_anomaly_jsonb(
    metadata: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Validate metadata JSONB field for Anomaly.
    
    Usage:
        anomaly = Anomaly(
            workspace_id=workspace_id,
            anomaly_type=AnomalyType.COST_SPIKE,
            metadata=validate_anomaly_jsonb({"operation_type": "transcribe", "provider": "openai"}),
        )
    """
    return validate_anomaly_metadata(metadata)


def validate_savings_report_jsonb(
    breakdown_by_operation: Optional[Dict[str, Dict]],
    breakdown_by_provider: Optional[Dict[str, Dict]],
) -> tuple[Optional[Dict[str, Dict]], Optional[Dict[str, Dict]]]:
    """
    Validate breakdown JSONB fields for SavingsReport.
    
    Usage:
        op_breakdown, provider_breakdown = validate_savings_report_jsonb(
            {"transcribe": {"savings": 10.50, "count": 100}},
            {"openai": {"cost": 50.00, "savings": 10.00}},
        )
        report = SavingsReport(
            workspace_id=workspace_id,
            breakdown_by_operation=op_breakdown,
            breakdown_by_provider=provider_breakdown,
        )
    """
    validated_op = validate_breakdown_by_operation(breakdown_by_operation)
    validated_provider = validate_breakdown_by_provider(breakdown_by_provider)
    return validated_op, validated_provider
