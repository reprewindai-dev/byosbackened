"""Edge message schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EdgeMessage(BaseModel):
    """Normalized edge payload used across connectors, rules, and output adapters."""

    source: str
    payload: dict[str, Any]
    protocol: str = "http"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def normalize(raw: dict[str, Any], *, source: str | None = None, protocol: str = "http") -> "EdgeMessage":
        """Normalize any raw payload into an edge message."""
        resolved_source = source or str(raw.get("device") or raw.get("source") or "unknown")
        return EdgeMessage(
            source=resolved_source,
            payload=raw,
            protocol=protocol,
            metadata=dict(raw.get("metadata", {}) if isinstance(raw.get("metadata"), dict) else {}),
        )
