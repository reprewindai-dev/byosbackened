"""Autonomous queue optimization - learns optimal priorities."""
from typing import Dict
from core.incident.alerting import send_alert
import logging

logger = logging.getLogger(__name__)

# Backlog protection thresholds
QUEUE_DEPTH_ALERT_THRESHOLD = 1000    # Alert if queue depth exceeds this
QUEUE_DEPTH_SHED_THRESHOLD = 2000     # Reject new non-priority work above this
QUEUE_DEPTH_CRITICAL_THRESHOLD = 5000 # Alert critical + reject everything non-urgent

# Priority tiers (higher = more important)
PRIORITY_HIGH = 9    # Bypass backlog shed policy
PRIORITY_NORMAL = 5
PRIORITY_LOW = 2

# Default priorities per operation type
_DEFAULT_PRIORITIES: Dict[str, int] = {
    "transcribe": PRIORITY_NORMAL,
    "extract": 7,     # Higher priority — faster turnaround expected
    "export": PRIORITY_LOW,
}

# High-priority operation types that skip the shed policy
_HIGH_PRIORITY_OPERATIONS = {"extract"}


class QueueBacklogError(Exception):
    """Raised when queue is overloaded and request should be shed."""
    pass


class QueueOptimizer:
    """
    Autonomous queue optimization.

    Learns optimal priorities per operation type per workspace.
    Auto-adjusts worker counts based on queue depth.
    Enforces backlog protection: alerts at 1000, sheds load at 2000.
    """

    def __init__(self):
        # workspace_id:operation_type -> {priority, worker_count, queue_depth_avg}
        self.queue_configs: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Priority
    # ------------------------------------------------------------------

    def get_optimal_priority(
        self,
        workspace_id: str,
        operation_type: str,
    ) -> int:
        """
        Get optimal priority based on learned patterns.

        Returns priority (1-10, higher = more important).
        """
        key = f"{workspace_id}:{operation_type}"
        if key in self.queue_configs:
            return self.queue_configs[key].get("priority", PRIORITY_NORMAL)
        return _DEFAULT_PRIORITIES.get(operation_type, PRIORITY_NORMAL)

    def is_high_priority(self, operation_type: str) -> bool:
        """Return True if operation type bypasses shed policy."""
        return operation_type in _HIGH_PRIORITY_OPERATIONS

    # ------------------------------------------------------------------
    # Backlog protection
    # ------------------------------------------------------------------

    def check_backlog(
        self,
        workspace_id: str,
        operation_type: str,
        current_queue_depth: int,
    ) -> Dict:
        """
        Check queue depth and enforce backlog protection policy.

        Returns status dict. Raises QueueBacklogError if load should be shed.

        Policy:
          depth > QUEUE_DEPTH_CRITICAL_THRESHOLD → reject all non-high-priority + critical alert
          depth > QUEUE_DEPTH_SHED_THRESHOLD      → reject non-high-priority + warning alert
          depth > QUEUE_DEPTH_ALERT_THRESHOLD     → allow but fire alert
        """
        high_priority = self.is_high_priority(operation_type)

        if current_queue_depth > QUEUE_DEPTH_CRITICAL_THRESHOLD:
            send_alert(
                alert_type="queue_critical",
                severity="critical",
                message=(
                    f"Queue CRITICAL for workspace {workspace_id}: "
                    f"depth={current_queue_depth} > {QUEUE_DEPTH_CRITICAL_THRESHOLD}"
                ),
                workspace_id=workspace_id,
                metadata={
                    "queue_depth": current_queue_depth,
                    "operation_type": operation_type,
                    "threshold": QUEUE_DEPTH_CRITICAL_THRESHOLD,
                },
            )
            if not high_priority:
                raise QueueBacklogError(
                    f"Queue critically overloaded (depth={current_queue_depth}). "
                    f"Shedding {operation_type} work."
                )

        elif current_queue_depth > QUEUE_DEPTH_SHED_THRESHOLD:
            send_alert(
                alert_type="queue_overload",
                severity="high",
                message=(
                    f"Queue overloaded for workspace {workspace_id}: "
                    f"depth={current_queue_depth} > {QUEUE_DEPTH_SHED_THRESHOLD}"
                ),
                workspace_id=workspace_id,
                metadata={
                    "queue_depth": current_queue_depth,
                    "operation_type": operation_type,
                    "threshold": QUEUE_DEPTH_SHED_THRESHOLD,
                },
            )
            if not high_priority:
                raise QueueBacklogError(
                    f"Queue overloaded (depth={current_queue_depth}). "
                    f"Shedding {operation_type} work."
                )

        elif current_queue_depth > QUEUE_DEPTH_ALERT_THRESHOLD:
            send_alert(
                alert_type="queue_lag",
                severity="medium",
                message=(
                    f"Queue depth high for workspace {workspace_id}: "
                    f"depth={current_queue_depth} > {QUEUE_DEPTH_ALERT_THRESHOLD}"
                ),
                workspace_id=workspace_id,
                metadata={
                    "queue_depth": current_queue_depth,
                    "operation_type": operation_type,
                    "threshold": QUEUE_DEPTH_ALERT_THRESHOLD,
                },
            )
            logger.warning(
                f"Queue lag alert: workspace={workspace_id}, "
                f"operation={operation_type}, depth={current_queue_depth}"
            )

        return {
            "queue_depth": current_queue_depth,
            "shed_threshold": QUEUE_DEPTH_SHED_THRESHOLD,
            "alert_threshold": QUEUE_DEPTH_ALERT_THRESHOLD,
            "high_priority": high_priority,
            "accepted": True,
        }

    # ------------------------------------------------------------------
    # Worker scaling
    # ------------------------------------------------------------------

    def get_optimal_workers(
        self,
        workspace_id: str,
        operation_type: str,
        current_queue_depth: int,
    ) -> int:
        """
        Get optimal worker count based on queue depth.

        Learns optimal worker-to-queue ratio over time.
        """
        key = f"{workspace_id}:{operation_type}"

        if key not in self.queue_configs:
            return max(1, int(current_queue_depth / 10))

        ratio = self.queue_configs[key].get("worker_to_queue_ratio", 0.1)
        return max(1, int(current_queue_depth * ratio))

    # ------------------------------------------------------------------
    # Learning loop
    # ------------------------------------------------------------------

    def update_queue_metrics(
        self,
        workspace_id: str,
        operation_type: str,
        queue_depth: int,
        processing_time_avg: float,
        worker_count: int,
    ):
        """
        Update queue metrics for learning.

        Improves worker allocation over time.
        """
        key = f"{workspace_id}:{operation_type}"
        alpha = 0.1

        if key not in self.queue_configs:
            self.queue_configs[key] = {
                "priority": _DEFAULT_PRIORITIES.get(operation_type, PRIORITY_NORMAL),
                "worker_count": worker_count,
                "queue_depth_avg": float(queue_depth),
                "processing_time_avg": processing_time_avg,
                "worker_to_queue_ratio": worker_count / queue_depth if queue_depth > 0 else 0.1,
            }
        else:
            config = self.queue_configs[key]
            config["queue_depth_avg"] = (
                alpha * queue_depth + (1 - alpha) * config["queue_depth_avg"]
            )
            config["processing_time_avg"] = (
                alpha * processing_time_avg + (1 - alpha) * config["processing_time_avg"]
            )
            if queue_depth > 0:
                current_ratio = worker_count / queue_depth
                config["worker_to_queue_ratio"] = (
                    alpha * current_ratio + (1 - alpha) * config["worker_to_queue_ratio"]
                )


# Global queue optimizer
_queue_optimizer = QueueOptimizer()


def get_queue_optimizer() -> QueueOptimizer:
    """Get global queue optimizer instance."""
    return _queue_optimizer
