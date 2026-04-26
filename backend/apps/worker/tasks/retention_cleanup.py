"""
Celery scheduled task for data retention cleanup.

This task runs periodically to clean up expired data according to
workspace retention policies. It removes:
- Old assets, transcripts, exports, jobs (per workspace retention policy)
- Old traffic patterns, resolved anomalies, savings reports (autonomous data)
"""
from datetime import datetime
from apps.worker.worker import celery_app
from db.session import SessionLocal
from core.privacy.data_retention import delete_expired_data, apply_retention_policy, apply_autonomous_data_retention
from db.models import Workspace
import logging

logger = logging.getLogger(__name__)


@celery_app.task(
    name="retention_cleanup",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def retention_cleanup_task(self, workspace_id: str = None, dry_run: bool = False):
    """
    Run data retention cleanup for all workspaces or a specific workspace.
    
    Args:
        workspace_id: If provided, only clean up this workspace. Otherwise all.
        dry_run: If True, don't actually delete, just log what would be deleted.
    
    Returns:
        Dict with cleanup statistics per workspace.
    """
    db = SessionLocal()
    stats = {}
    
    try:
        if workspace_id:
            # Clean up specific workspace
            logger.info(f"Starting retention cleanup for workspace {workspace_id} (dry_run={dry_run})")
            result = delete_expired_data(db, workspace_id=workspace_id)
            stats[workspace_id] = result
            logger.info(f"Completed retention cleanup for workspace {workspace_id}: {result}")
        else:
            # Clean up all workspaces
            workspaces = db.query(Workspace).all()
            logger.info(f"Starting retention cleanup for {len(workspaces)} workspaces (dry_run={dry_run})")
            
            for workspace in workspaces:
                try:
                    result = delete_expired_data(db, workspace_id=workspace.id)
                    stats[workspace.id] = result
                    logger.info(f"Cleaned up workspace {workspace.id}: {result}")
                except Exception as e:
                    logger.error(f"Failed to clean up workspace {workspace.id}: {e}", exc_info=True)
                    stats[workspace.id] = {"error": str(e)}
                    # Continue with other workspaces
            
            logger.info(f"Completed retention cleanup for all workspaces")
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "dry_run": dry_run,
            "workspaces_processed": len(stats),
            "stats": stats,
        }
        
    except Exception as e:
        logger.error(f"Retention cleanup task failed: {e}", exc_info=True)
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }
    finally:
        db.close()


@celery_app.task(
    name="retention_cleanup_autonomous_only",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def retention_cleanup_autonomous_task(self, retention_days: int = 90, dry_run: bool = False):
    """
    Clean up only autonomous AI data (traffic patterns, anomalies, savings reports).
    This runs more frequently than full cleanup.
    
    Args:
        retention_days: Days to keep autonomous data (default 90)
        dry_run: If True, don't actually delete
    
    Returns:
        Dict with cleanup statistics.
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Starting autonomous data retention cleanup (days={retention_days}, dry_run={dry_run})")
        
        result = apply_autonomous_data_retention(
            db,
            workspace_id=None,  # All workspaces
            retention_days=retention_days,
            dry_run=dry_run,
        )
        
        logger.info(f"Completed autonomous data retention cleanup: {result}")
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "dry_run": dry_run,
            "retention_days": retention_days,
            "deleted_counts": result,
        }
        
    except Exception as e:
        logger.error(f"Autonomous retention cleanup task failed: {e}", exc_info=True)
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }
    finally:
        db.close()
