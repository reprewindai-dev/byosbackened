"""Data retention cleanup tasks."""

from celery import shared_task
from sqlalchemy.orm import Session
from db.session import SessionLocal, set_current_workspace_id
from core.privacy.data_retention import (
    apply_retention_policy,
    apply_autonomous_data_retention,
    get_workspace_retention_days,
)
from core.config import get_settings
import logging

from core.audit.event_logger import get_audit_event_logger

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
    # Defensive: ensure no tenant context is leaked into this worker task.
    set_current_workspace_id(None)

    db = SessionLocal()
    try:
        audit_logger = get_audit_event_logger()

        def _run_for_workspace(wid: str) -> dict:
            # Ensure any accidental unscoped reads are still forced into this tenant.
            set_current_workspace_id(wid)
            try:
                from db.models import Workspace

                w = db.query(Workspace).filter(Workspace.id == wid).first()
                org_id = w.organization_id if w else None

                retention_days = get_workspace_retention_days(db, wid)
                standard_counts = apply_retention_policy(
                    db=db,
                    workspace_id=wid,
                    retention_days=retention_days,
                    dry_run=dry_run,
                )
                autonomous_counts = apply_autonomous_data_retention(
                    db=db,
                    workspace_id=wid,
                    retention_days=retention_days,
                    dry_run=dry_run,
                )
                all_counts = {**standard_counts, **autonomous_counts}

                if not dry_run:
                    audit_logger.append_event(
                        db,
                        workspace_id=wid,
                        organization_id=org_id,
                        actor_user_id=None,
                        actor_type="system",
                        action="retention.purge",
                        resource_type="workspace",
                        resource_id=wid,
                        success=True,
                        status_code="200",
                        details={
                            "retention_days": retention_days,
                            "deleted_counts": all_counts,
                        },
                    )
                return all_counts
            finally:
                set_current_workspace_id(None)

        if workspace_id:
            all_counts = _run_for_workspace(workspace_id)
        else:
            from db.models import Workspace

            workspaces = db.query(Workspace).all()
            all_counts = {}
            for w in workspaces:
                counts = _run_for_workspace(w.id)
                for table, count in counts.items():
                    all_counts[table] = all_counts.get(table, 0) + count

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
