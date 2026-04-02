"""Incident response procedures."""

from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import IncidentLog, IncidentStatus, IncidentSeverity
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class IncidentResponse:
    """Handle incidents."""

    def create_incident(
        self,
        db: Session,
        incident_type: str,
        severity: IncidentSeverity,
        title: str,
        description: str,
        workspace_id: Optional[str] = None,
    ) -> IncidentLog:
        """Create incident log."""
        incident = IncidentLog(
            workspace_id=workspace_id,
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            status=IncidentStatus.OPEN,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        logger.critical(f"Incident created: {incident.id} - {title} [{severity.value}]")

        return incident

    def resolve_incident(
        self,
        db: Session,
        incident_id: str,
        resolution: str,
    ) -> IncidentLog:
        """Resolve incident."""
        incident = db.query(IncidentLog).filter(IncidentLog.id == incident_id).first()
        if not incident:
            raise ValueError(f"Incident not found: {incident_id}")

        incident.status = IncidentStatus.RESOLVED
        incident.resolution = resolution
        incident.resolved_at = datetime.utcnow()
        db.commit()
        db.refresh(incident)

        logger.info(f"Incident resolved: {incident_id}")

        return incident
