"""Data retention policies."""
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session
from db.models import (
    Asset, Transcript, Export, Job,
    TrafficPattern, Anomaly, RoutingStrategy, SavingsReport,
)
from db.models.anomaly import AnomalyStatus
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def apply_retention_policy(
    db: Session,
    workspace_id: str,
    retention_days: int,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Apply data retention policy - delete data older than retention_days.
    
    Returns count of records deleted per table.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    deleted_counts = {}
    
    # Delete old assets
    old_assets = db.query(Asset).filter(
        Asset.workspace_id == workspace_id,
        Asset.created_at < cutoff_date
    ).all()
    deleted_counts["assets"] = len(old_assets)
    if not dry_run:
        for asset in old_assets:
            db.delete(asset)
    
    # Delete old transcripts
    old_transcripts = db.query(Transcript).filter(
        Transcript.workspace_id == workspace_id,
        Transcript.created_at < cutoff_date
    ).all()
    deleted_counts["transcripts"] = len(old_transcripts)
    if not dry_run:
        for transcript in old_transcripts:
            db.delete(transcript)
    
    # Delete old exports
    old_exports = db.query(Export).filter(
        Export.workspace_id == workspace_id,
        Export.created_at < cutoff_date
    ).all()
    deleted_counts["exports"] = len(old_exports)
    if not dry_run:
        for export in old_exports:
            db.delete(export)
    
    # Delete old completed/failed jobs (keep pending/running)
    old_jobs = db.query(Job).filter(
        Job.workspace_id == workspace_id,
        Job.created_at < cutoff_date,
        Job.status.in_(["completed", "failed"])
    ).all()
    deleted_counts["jobs"] = len(old_jobs)
    if not dry_run:
        for job in old_jobs:
            db.delete(job)
    
    if not dry_run:
        db.commit()
        logger.info(f"Retention policy applied: workspace={workspace_id}, deleted={deleted_counts}")
    else:
        logger.info(f"Retention policy dry run: workspace={workspace_id}, would delete={deleted_counts}")
    
    return deleted_counts


def get_workspace_retention_days(db: Session, workspace_id: str) -> int:
    """Get retention days from workspace settings or return default."""
    from db.models import Workspace
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if workspace and hasattr(workspace, 'settings') and workspace.settings:
        # Try to get retention from workspace settings JSON
        import json
        try:
            settings = json.loads(workspace.settings) if isinstance(workspace.settings, str) else workspace.settings
            retention = settings.get('data_retention_days')
            if retention and isinstance(retention, int) and retention > 0:
                return retention
        except (json.JSONDecodeError, AttributeError):
            pass
    
    # Return default from global settings
    return getattr(settings, 'data_retention_days', 90)


def apply_autonomous_data_retention(
    db: Session,
    workspace_id: Optional[str] = None,
    retention_days: int = 90,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Apply retention to autonomous AI data (traffic patterns, anomalies, savings reports).
    
    Returns count of records deleted per table.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    deleted_counts = {}
    
    # Delete old traffic patterns
    if workspace_id:
        old_patterns = db.query(TrafficPattern).filter(
            TrafficPattern.workspace_id == workspace_id,
            TrafficPattern.created_at < cutoff_date
        ).all()
    else:
        old_patterns = db.query(TrafficPattern).filter(
            TrafficPattern.created_at < cutoff_date
        ).all()
    
    deleted_counts["traffic_patterns"] = len(old_patterns)
    if not dry_run:
        for pattern in old_patterns:
            db.delete(pattern)
    
    # Delete old resolved anomalies (keep unresolved for investigation)
    if workspace_id:
        old_anomalies = db.query(Anomaly).filter(
            Anomaly.workspace_id == workspace_id,
            Anomaly.status == AnomalyStatus.RESOLVED,
            Anomaly.detected_at < cutoff_date
        ).all()
    else:
        old_anomalies = db.query(Anomaly).filter(
            Anomaly.status == AnomalyStatus.RESOLVED,
            Anomaly.detected_at < cutoff_date
        ).all()
    
    deleted_counts["resolved_anomalies"] = len(old_anomalies)
    if not dry_run:
        for anomaly in old_anomalies:
            db.delete(anomaly)
    
    # Delete old savings reports
    if workspace_id:
        old_reports = db.query(SavingsReport).filter(
            SavingsReport.workspace_id == workspace_id,
            SavingsReport.period_end < cutoff_date
        ).all()
    else:
        old_reports = db.query(SavingsReport).filter(
            SavingsReport.period_end < cutoff_date
        ).all()
    
    deleted_counts["old_savings_reports"] = len(old_reports)
    if not dry_run:
        for report in old_reports:
            db.delete(report)
    
    # Delete old routing strategies that are inactive
    if workspace_id:
        old_strategies = db.query(RoutingStrategy).filter(
            RoutingStrategy.workspace_id == workspace_id,
            RoutingStrategy.is_active == False,
            RoutingStrategy.created_at < cutoff_date
        ).all()
    else:
        old_strategies = db.query(RoutingStrategy).filter(
            RoutingStrategy.is_active == False,
            RoutingStrategy.created_at < cutoff_date
        ).all()
    
    deleted_counts["inactive_routing_strategies"] = len(old_strategies)
    if not dry_run:
        for strategy in old_strategies:
            db.delete(strategy)
    
    if not dry_run:
        db.commit()
        logger.info(f"Autonomous data retention applied: workspace={workspace_id}, deleted={deleted_counts}")
    else:
        logger.info(f"Autonomous data retention dry run: workspace={workspace_id}, would delete={deleted_counts}")
    
    return deleted_counts


def delete_expired_data(db: Session, workspace_id: Optional[str] = None):
    """Delete expired data for all workspaces or specific workspace."""
    if workspace_id:
        # Get retention from workspace settings
        retention_days = get_workspace_retention_days(db, workspace_id)
        apply_retention_policy(db, workspace_id, retention_days)
        apply_autonomous_data_retention(db, workspace_id=workspace_id, retention_days=retention_days)
    else:
        # Apply to all workspaces with individual retention settings
        from db.models import Workspace
        workspaces = db.query(Workspace).all()
        for workspace in workspaces:
            retention_days = get_workspace_retention_days(db, workspace.id)
            apply_retention_policy(db, workspace.id, retention_days)
        
        # Apply autonomous data retention for all workspaces (uses default)
        apply_autonomous_data_retention(db, workspace_id=None)
