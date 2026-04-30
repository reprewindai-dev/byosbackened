"""MQTT connector stubs for future implementation."""

from __future__ import annotations

from typing import Any

from edge.schemas.edge_message import EdgeMessage


def normalize_mqtt_payload(payload: dict[str, Any], topic: str | None = None) -> EdgeMessage:
    """Normalize MQTT payload shape into the shared edge message model."""
    source = topic or "mqtt-unknown"
    return EdgeMessage.normalize(payload, source=source, protocol="mqtt")
