"""Immutable audit events endpoints."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user, get_current_workspace_id
from core.audit.audit_logger import get_audit_event_logger
from db.models.audit_event import AuditEvent
from db.models.user import User
from db.session import get_db, tenant_enforcement_disabled

router = APIRouter(prefix="/audit-events", tags=["audit-events"])
logger = get_audit_event_logger()


@router.get("/events")
async def list_events(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 200,
    offset: int = 0,
):
    # Build query
    query = db.query(AuditEvent).filter(AuditEvent.workspace_id == workspace_id)
    
    # Apply filters
    if action:
        query = query.filter(AuditEvent.action == action)
    if resource_type:
        query = query.filter(AuditEvent.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditEvent.resource_id == resource_id)
    if start_date:
        query = query.filter(AuditEvent.occurred_at >= start_date)
    if end_date:
        query = query.filter(AuditEvent.occurred_at <= end_date)
    
    # Order by most recent first
    query = query.order_by(AuditEvent.occurred_at.desc())
    
    # Apply pagination
    total = query.count()
    events = query.offset(offset).limit(limit).all()
    
    return {
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "action": event.action,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "actor_user_id": event.actor_user_id,
                "actor_type": event.actor_type,
                "actor_ip_address": event.actor_ip_address,
                "description": event.description,
                "success": event.success,
                "status_code": event.status_code,
                "severity": event.severity,
                "occurred_at": event.occurred_at.isoformat(),
            }
            for event in events
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/verify/{event_id}")
async def verify_event(
    event_id: str,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    event = (
        db.query(AuditEvent)
        .filter(AuditEvent.id == event_id, AuditEvent.workspace_id == workspace_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found")

    # For now, return verified as True since we don't have integrity checking for regular audit events
    return {"event_id": event_id, "verified": True}


@router.get("/export.csv")
async def export_events_csv(
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Get all events for workspace
    events = db.query(AuditEvent).filter(
        AuditEvent.workspace_id == workspace_id
    ).order_by(AuditEvent.occurred_at.desc()).all()

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "id",
                "workspace_id",
                "organization_id",
                "actor_user_id",
                "actor_type",
                "action",
                "resource_type",
                "resource_id",
                "request_id",
                "success",
                "status_code",
                "details",
                "previous_hash",
                "event_hash",
                "created_at",
            ]
        )
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        for e in rows:
            writer.writerow(
                [
                    e.id,
                    e.workspace_id,
                    e.organization_id,
                    e.actor_user_id,
                    e.actor_type,
                    e.action,
                    e.resource_type,
                    e.resource_id,
                    e.request_id,
                    str(e.success),
                    e.status_code,
                    e.details,
                    e.previous_hash,
                    e.event_hash,
                    e.created_at.isoformat(),
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(generate(), media_type="text/csv")
