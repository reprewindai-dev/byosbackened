"""Queue backlog monitoring and load shedding."""

from typing import Dict, Optional, List
from datetime import datetime
from celery import Celery
from celery.result import AsyncResult
from core.config import get_settings
from core.incident.alerting import send_alert
from core.metrics.autonomous_metrics import get_autonomous_metrics
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
autonomous_metrics = get_autonomous_metrics()


class BacklogMonitor:
    """
    Monitor queue depth and implement load shedding.

    Alerts when queue depth exceeds thresholds.
    Rejects low-priority requests when backlog too high.
    """

    # Backlog thresholds
    WARNING_THRESHOLD = 500  # Alert at 500 items
    CRITICAL_THRESHOLD = 1000  # Alert at 1000 items
    LOAD_SHED_THRESHOLD = 2000  # Start load shedding at 2000 items

    def __init__(self, celery_app: Optional[Celery] = None):
        self.celery_app = celery_app
        self.last_alert_time: Dict[str, datetime] = {}  # operation_type -> last alert time
        self.alert_cooldown_seconds = 300  # 5 minutes between alerts

    def get_queue_depth(
        self,
        operation_type: str,
        queue_name: Optional[str] = None,
    ) -> int:
        """
        Get current queue depth for operation type.

        Returns number of pending tasks in queue.
        """
        if not self.celery_app:
            # If no celery app, return 0 (can't measure)
            return 0

        try:
            # Get queue name
            if queue_name is None:
                queue_name = f"celery"  # Default queue

            # Get queue length
            inspect = self.celery_app.control.inspect()
            active_queues = inspect.active_queues()

            if not active_queues:
                return 0

            # Sum up queue lengths across all workers
            total_depth = 0
            for worker, queues in active_queues.items():
                for queue_info in queues:
                    if queue_info.get("name") == queue_name:
                        # Get reserved tasks (in progress)
                        reserved = inspect.reserved()
                        if reserved and worker in reserved:
                            total_depth += len(reserved[worker])

            # Also check scheduled tasks
            scheduled = inspect.scheduled()
            if scheduled:
                for worker, tasks in scheduled.items():
                    total_depth += len(tasks)

            return total_depth

        except Exception as e:
            logger.error(f"Error getting queue depth: {e}")
            return 0

    def check_backlog(
        self,
        operation_type: str,
        queue_name: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Check queue backlog and alert if needed.

        Returns backlog status and any alerts triggered.
        """
        depth = self.get_queue_depth(operation_type, queue_name)

        # Record metric
        autonomous_metrics.record_queue_depth(
            workspace_id="system",  # System-wide metric
            operation_type=operation_type,
            queue_depth=depth,
        )

        status = "healthy"
        severity = None
        alert_triggered = False

        if depth >= self.LOAD_SHED_THRESHOLD:
            status = "critical"
            severity = "critical"
            alert_triggered = self._send_alert_if_needed(
                operation_type=operation_type,
                severity=severity,
                depth=depth,
                message=f"Queue backlog CRITICAL: {depth} items (threshold: {self.LOAD_SHED_THRESHOLD})",
            )
        elif depth >= self.CRITICAL_THRESHOLD:
            status = "critical"
            severity = "high"
            alert_triggered = self._send_alert_if_needed(
                operation_type=operation_type,
                severity=severity,
                depth=depth,
                message=f"Queue backlog HIGH: {depth} items (threshold: {self.CRITICAL_THRESHOLD})",
            )
        elif depth >= self.WARNING_THRESHOLD:
            status = "warning"
            severity = "medium"
            alert_triggered = self._send_alert_if_needed(
                operation_type=operation_type,
                severity=severity,
                depth=depth,
                message=f"Queue backlog WARNING: {depth} items (threshold: {self.WARNING_THRESHOLD})",
            )

        return {
            "operation_type": operation_type,
            "queue_depth": depth,
            "status": status,
            "severity": severity,
            "alert_triggered": alert_triggered,
            "thresholds": {
                "warning": self.WARNING_THRESHOLD,
                "critical": self.CRITICAL_THRESHOLD,
                "load_shed": self.LOAD_SHED_THRESHOLD,
            },
        }

    def _send_alert_if_needed(
        self,
        operation_type: str,
        severity: str,
        depth: int,
        message: str,
    ) -> bool:
        """Send alert if cooldown period has passed."""
        now = datetime.utcnow()
        last_alert = self.last_alert_time.get(operation_type)

        if last_alert:
            time_since_alert = (now - last_alert).total_seconds()
            if time_since_alert < self.alert_cooldown_seconds:
                return False  # Still in cooldown

        # Send alert
        send_alert(
            alert_type="queue_backlog",
            severity=severity,
            message=message,
            workspace_id=None,  # System-wide
            metadata={
                "operation_type": operation_type,
                "queue_depth": depth,
            },
        )

        self.last_alert_time[operation_type] = now
        return True

    def should_shed_load(
        self,
        operation_type: str,
        priority: int = 5,
        queue_name: Optional[str] = None,
    ) -> bool:
        """
        Determine if load should be shed (reject low-priority requests).

        Returns True if request should be rejected due to high backlog.
        """
        depth = self.get_queue_depth(operation_type, queue_name)

        if depth < self.LOAD_SHED_THRESHOLD:
            return False

        # Shed low-priority requests (priority < 5)
        if priority < 5:
            logger.warning(
                f"Load shedding: rejecting low-priority request "
                f"(operation_type={operation_type}, priority={priority}, queue_depth={depth})"
            )
            return True

        # Don't shed high-priority requests
        return False

    def get_backlog_stats(
        self,
        operation_types: Optional[List[str]] = None,
    ) -> Dict[str, Dict]:
        """
        Get backlog statistics for all operation types.

        Returns dictionary of operation_type -> backlog status.
        """
        if operation_types is None:
            operation_types = ["transcribe", "extract", "export", "chat"]

        stats = {}
        for op_type in operation_types:
            stats[op_type] = self.check_backlog(op_type)

        return stats


# Global backlog monitor (needs celery app to be set)
_backlog_monitor: Optional[BacklogMonitor] = None


def get_backlog_monitor(celery_app: Optional[Celery] = None) -> BacklogMonitor:
    """Get global backlog monitor instance."""
    global _backlog_monitor

    if _backlog_monitor is None:
        _backlog_monitor = BacklogMonitor(celery_app=celery_app)
    elif celery_app and _backlog_monitor.celery_app != celery_app:
        # Update celery app if provided
        _backlog_monitor.celery_app = celery_app

    return _backlog_monitor
