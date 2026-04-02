"""Autonomous queue optimization - learns optimal priorities."""

from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QueueOptimizer:
    """
    Autonomous queue optimization.

    Learns optimal priorities per operation type per workspace.
    Auto-adjusts worker counts based on queue depth.
    """

    def __init__(self):
        # workspace_id:operation_type -> {priority, worker_count, queue_depth_avg}
        self.queue_configs: Dict[str, Dict] = {}

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

        if key not in self.queue_configs:
            # Default priorities
            defaults = {
                "transcribe": 5,
                "extract": 7,  # Higher priority (faster turnaround)
                "export": 3,  # Lower priority (can wait)
            }
            return defaults.get(operation_type, 5)

        return self.queue_configs[key].get("priority", 5)

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
            # Default: 1 worker per 10 items in queue
            return max(1, int(current_queue_depth / 10))

        config = self.queue_configs[key]

        # Learn optimal ratio
        ratio = config.get("worker_to_queue_ratio", 0.1)  # 1 worker per 10 items

        return max(1, int(current_queue_depth * ratio))

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

        This is the learning loop - improves worker allocation over time.
        """
        key = f"{workspace_id}:{operation_type}"

        if key not in self.queue_configs:
            self.queue_configs[key] = {
                "priority": 5,
                "worker_count": worker_count,
                "queue_depth_avg": queue_depth,
                "processing_time_avg": processing_time_avg,
                "worker_to_queue_ratio": worker_count / queue_depth if queue_depth > 0 else 0.1,
            }
        else:
            config = self.queue_configs[key]

            # Update moving averages
            alpha = 0.1
            config["queue_depth_avg"] = (
                alpha * queue_depth + (1 - alpha) * config["queue_depth_avg"]
            )
            config["processing_time_avg"] = (
                alpha * processing_time_avg + (1 - alpha) * config["processing_time_avg"]
            )

            # Update worker-to-queue ratio
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
