"""Celery worker."""
from celery import Celery
from celery.schedules import crontab
from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "byos_ai_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    beat_schedule={
        # Full retention cleanup — daily at 02:00 UTC
        # Cleans up all expired data per workspace retention policies
        "retention-cleanup-daily": {
            "task": "retention_cleanup",
            "schedule": crontab(hour=2, minute=0),
            "kwargs": {"dry_run": False, "workspace_id": None},
        },
        # Focused autonomous table cleanup — every 6 hours
        # traffic_patterns > 90 days, resolved anomalies > 30 days
        "retention-cleanup-autonomous-6h": {
            "task": "retention_cleanup_autonomous_only",
            "schedule": crontab(hour="*/6", minute=30),
            "kwargs": {"dry_run": False, "retention_days": 90},
        },
    },
)
