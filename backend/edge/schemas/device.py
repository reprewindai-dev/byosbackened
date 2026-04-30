"""Device metadata compatibility schema."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class DeviceSchema(BaseModel):
    """Minimal device descriptor used by edge adapters."""

    device_id: str
    protocol: str = "http"
    metadata: dict = Field(default_factory=dict)
