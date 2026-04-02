"""Data retention policies."""

from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session
from db.models import (
    Asset,
    Transcript,
    Export,
    Job,
    TrafficPattern,
    Anomaly,
    RoutingStrategy,
    SavingsReport,
)
from db.models.anomaly import AnomalyStatus
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def apply_retention_policy(
    db: Session, workspace_id: str, retention_days: int, dry_run: bool = False
) -> Dict[str, int]:
    """
    Apply data retention policy - delete data older than retention_days.

    Returns count of records deleted per table.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    deleted_counts = {}

    # Delete old assets
    old_assets = (
        db.query(Asset)
        .filter(Asset.workspace_id == workspace_id, Asset.created_at < cutoff_date)
        .all()
    )
    deleted_counts["assets"] = len(old_assets)
    if not dry_run:
        for asset in old_assets:
            db.delete(asset)

    # Delete old transcripts
    old_transcripts = (
        db.query(Transcript)
        .filter(Transcript.workspace_id == workspace_id, Transcript.created_at < cutoff_date)
        .all()
    )
    deleted_counts["transcripts"] = len(old_transcripts)
    if not dry_run:
        for transcript in old_transcripts:
            db.delete(transcript)

    # Delete old exports
    old_exports = (
        db.query(Export)
        .filter(Export.workspace_id == workspace_id, Export.created_at < cutoff_date)
        .all()
    )
    deleted_counts["exports"] = len(old_exports)
    if not dry_run:
        for export in old_exports:
            db.delete(export)

    # Delete old completed/failed jobs (keep pending/running)
    old_jobs = (
        db.query(Job)
        .filter(
            Job.workspace_id == workspace_id,
            Job.created_at < cutoff_date,
            Job.status.in_(["completed", "failed"]),
        )
        .all()
    )
    deleted_counts["jobs"] = len(old_jobs)
    if not dry_run:
        for job in old_jobs:
            db.delete(job)

    if not dry_run:
        db.commit()
        logger.info(f"Retention policy applied: workspace={workspace_id}, deleted={deleted_counts}")
    else:
        logger.info(
            f"Retention policy dry run: workspace={workspace_id}, would delete={deleted_counts}"
        )

    return deleted_counts


def delete_expired_data(db: Session, workspace_id: Optional[str] = None):
    """Delete expired data for all workspaces or specific workspace."""
    # Get retention policy from workspace settings (default: 90 days)
    retention_days = 90  # TODO: Get from workspace settings

    if workspace_id:
        apply_retention_policy(db, workspace_id, retention_days)
        apply_autonomous_data_retention(db, workspace_id=workspace_id)
    else:
        # Apply to all workspaces
        from db.models import Workspace

        workspaces = db.query(Workspace).all()
        for workspace in workspaces:
            apply_retention_policy(db, workspace.id, retention_days)

        # Apply autonomous data retention for all workspaces
        apply_autonomous_data_retention(db, workspace_id=None)
