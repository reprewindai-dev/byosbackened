"""Learn optimal placement per workspace - creates non-portable intelligence."""

from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PlacementLearner:
    """
    Learn optimal placement per workspace.

    This creates the moat - learns which operations benefit from edge vs central.
    After months of learning, we know YOUR optimal placement.
    """

    def __init__(self):
        # workspace_id:operation_type -> {region: {latency_avg, cost_avg, success_rate}}
        self.placement_stats: Dict[str, Dict[str, Dict]] = {}

    def get_optimal_region(
        self,
        workspace_id: str,
        operation_type: str,
    ) -> Optional[str]:
        """
        Get optimal region based on learned patterns.

        Returns None if not enough data yet (use defaults).
        """
        key = f"{workspace_id}:{operation_type}"

        if key not in self.placement_stats:
            return None

        stats = self.placement_stats[key]

        # Find region with best combination of latency and cost
        best_region = None
        best_score = float("-inf")

        for region, metrics in stats.items():
            # Score = low latency + low cost + high success rate
            latency_score = 1.0 - min(metrics.get("latency_avg", 5000) / 10000, 1.0)
            cost_score = 1.0 - min(float(metrics.get("cost_avg", Decimal("0.01"))) / 0.01, 1.0)
            success_score = metrics.get("success_rate", 0.95)

            score = latency_score * 0.4 + cost_score * 0.3 + success_score * 0.3

            if score > best_score:
                best_score = score
                best_region = region

        return best_region

    def should_use_edge(
        self,
        workspace_id: str,
        operation_type: str,
    ) -> bool:
        """
        Decide if operation should use edge based on learned patterns.

        Returns True if learned patterns suggest edge is better.
        """
        optimal_region = self.get_optimal_region(workspace_id, operation_type)

        # Edge regions
        edge_regions = ["eu-west", "asia-pacific"]  # Not us-east (central)

        return optimal_region in edge_regions if optimal_region else False

    def update_outcome(
        self,
        workspace_id: str,
        operation_type: str,
        region: str,
        latency_ms: int,
        cost: Decimal,
        success: bool,
    ):
        """
        Update placement statistics with outcome.

        This is the learning loop - improves decisions over time.
        """
        key = f"{workspace_id}:{operation_type}"

        if key not in self.placement_stats:
            self.placement_stats[key] = {}

        if region not in self.placement_stats[key]:
            self.placement_stats[key][region] = {
                "latency_avg": latency_ms,
                "cost_avg": cost,
                "success_count": 1 if success else 0,
                "total_count": 1,
                "success_rate": 1.0 if success else 0.0,
            }
        else:
            metrics = self.placement_stats[key][region]

            # Update moving averages
            alpha = 0.1  # Learning rate
            metrics["latency_avg"] = int(alpha * latency_ms + (1 - alpha) * metrics["latency_avg"])
            metrics["cost_avg"] = alpha * cost + (1 - alpha) * metrics["cost_avg"]

            # Update success rate
            metrics["total_count"] += 1
            if success:
                metrics["success_count"] += 1
            metrics["success_rate"] = metrics["success_count"] / metrics["total_count"]

        logger.debug(
            f"Updated placement stats for {key}:{region}: "
            f"latency={metrics['latency_avg']}ms, cost=${metrics['cost_avg']}, "
            f"success_rate={metrics['success_rate']:.2%}"
        )


# Global placement learner
_placement_learner = PlacementLearner()


def get_placement_learner() -> PlacementLearner:
    """Get global placement learner instance."""
    return _placement_learner
