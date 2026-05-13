"""Authenticated privacy-safe product telemetry ingestion."""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from db.models import ProductUsageEvent, User
from db.session import get_db

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

ALLOWED_EVENT_TYPES = {"page_view", "active_time", "feature_use", "api_surface", "checkout_intent"}


class TelemetryEvent(BaseModel):
    event_type: str
    surface: Optional[str] = None
    route: Optional[str] = None
    feature: Optional[str] = None
    duration_ms: int = Field(default=0, ge=0, le=24 * 60 * 60 * 1000)
    session_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TelemetryBatch(BaseModel):
    events: list[TelemetryEvent] = Field(default_factory=list, max_length=50)


def _safe_metadata(metadata: dict[str, Any]) -> str:
    allowed: dict[str, Any] = {}
    for key in ("referrer", "viewport", "source", "campaign", "tab_visible"):
        value = metadata.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            allowed[key] = value
    return json.dumps(allowed, sort_keys=True)[:2000]


@router.post("/events")
async def record_product_telemetry(
    payload: TelemetryBatch,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record behavioral usage signals without capturing prompts, files, or workspace content."""
    accepted = 0
    for event in payload.events:
        if event.event_type not in ALLOWED_EVENT_TYPES:
            continue
        db.add(
            ProductUsageEvent(
                workspace_id=current_user.workspace_id,
                user_id=current_user.id,
                session_id=(event.session_id or "")[:120] or None,
                event_type=event.event_type,
                surface=(event.surface or "")[:120] or None,
                route=(event.route or "")[:240] or None,
                feature=(event.feature or "")[:160] or None,
                duration_ms=event.duration_ms,
                metadata_json=_safe_metadata(event.metadata),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        )
        accepted += 1
    db.commit()
    return {"accepted": accepted}
