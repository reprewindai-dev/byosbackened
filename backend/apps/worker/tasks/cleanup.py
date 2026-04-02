"""Data retention cleanup tasks."""
from celery import shared_task
from sqlalchemy.orm import Session
from db.session import SessionLocal
from core.privacy.data_retention import (
    apply_retention_policy,
    apply_autonomous_data_retention,
)
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


@shared_task(name="cleanup.expired_data")
def cleanup_expired_data(workspace_id: str = None, dry_run: bool = False):
    """
    Cleanup expired data for workspace or all workspaces.
    
    Runs retention policies for:
    - Standard tables (assets, transcripts, exports, jobs)
    - Autonomous tables (traffic_patterns, anomalies, routing_strategies, savings_reports)
    
    Args:
        workspace_id: Optional workspace ID. If None, applies to all workspaces.
        dry_run: If True, only report what would be deleted without actually deleting.
    
    Returns:
        Dictionary with deletion counts per table.
    """
    db = SessionLocal()
    try:
        # Apply standard retention (90 days default)
        retention_days = 90
        
        if workspace_id:
            standard_counts = apply_retention_policy(
                db=db,
                workspace_id=workspace_id,
                retention_days=retention_days,
                dry_run=dry_run,
            )
        else:
            # Apply to all workspaces
            from db.models import Workspace
            workspaces = db.query(Workspace).all()
            standard_counts = {}
            for workspace in workspaces:
                counts = apply_retention_policy(
                    db=db,
                    workspace_id=workspace.id,
                    retention_days=retention_days,
                    dry_run=dry_run,
                )
                # Aggregate counts
                for table, count in counts.items():
                    standard_counts[table] = standard_counts.get(table, 0) + count
        
        # Apply autonomous data retention
        autonomous_counts = apply_autonomous_data_retention(
            db=db,
            workspace_id=workspace_id,
            dry_run=dry_run,
        )
        
        # Combine counts
        all_counts = {**standard_counts, **autonomous_counts}
        
        logger.info(
            f"Cleanup completed: workspace={workspace_id or 'all'}, "
            f"dry_run={dry_run}, deleted={all_counts}"
        )
        
        return {
            "workspace_id": workspace_id,
            "dry_run": dry_run,
            "deleted_counts": all_counts,
        }
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        raise
    finally:
        db.close()


@shared_task(name="cleanup.autonomous_data")
def cleanup_autonomous_data(workspace_id: str = None, dry_run: bool = False):
    """
    Cleanup expired autonomous ML and edge architecture data.
    
    This is a focused task for autonomous tables only.
    Can be run more frequently than full cleanup.
    
    Args:
        workspace_id: Optional workspace ID. If None, applies to all workspaces.
        dry_run: If True, only report what would be deleted.
    
    Returns:
        Dictionary with deletion counts per table.
    """
    db = SessionLocal()
    try:
        counts = apply_autonomous_data_retention(
            db=db,
            workspace_id=workspace_id,
            dry_run=dry_run,
        )
        
        logger.info(
            f"Autonomous data cleanup completed: workspace={workspace_id or 'all'}, "
            f"dry_run={dry_run}, deleted={counts}"
        )
        
        return {
            "workspace_id": workspace_id,
            "dry_run": dry_run,
            "deleted_counts": counts,
        }
    except Exception as e:
        logger.error(f"Error during autonomous data cleanup: {e}", exc_info=True)
        raise
    finally:
        db.close()
