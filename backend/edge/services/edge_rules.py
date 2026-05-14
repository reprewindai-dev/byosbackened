"""Edge rule engine primitives."""

from __future__ import annotations

from edge.schemas.edge_message import EdgeMessage


def apply_rules(msg: EdgeMessage) -> EdgeMessage:
    """Run lightweight CPU-only rules before routing."""
    temperature = msg.payload.get("temperature")
    try:
        if temperature is not None and float(temperature) > 80:
            msg.metadata["alert"] = True
            msg.metadata["alert_reason"] = "temperature_threshold"
    except (TypeError, ValueError):
        # Ignore malformed numeric values but preserve processing
        msg.metadata["data_quality_issue"] = "invalid_temperature_type"

    if msg.payload.get("severity") == "critical":
            msg.metadata["alert"] = True
            msg.metadata["alert_reason"] = "critical_severity"

    metric_value = msg.payload.get("value")
    try:
        if metric_value is not None and float(metric_value) > 80:
            msg.metadata["alert"] = True
            msg.metadata["alert_reason"] = "value_threshold"
    except (TypeError, ValueError):
        # keep compatibility with legacy numeric fields that cannot be parsed
        msg.metadata["data_quality_issue"] = msg.metadata.get("data_quality_issue", "invalid_value_type")

    return msg
