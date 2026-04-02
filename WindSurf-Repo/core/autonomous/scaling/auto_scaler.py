"""Autonomous auto-scaling based on predictions."""

from typing import Dict, Optional
from datetime import datetime
from core.autonomous.prediction.traffic_predictor import get_traffic_predictor
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
traffic_predictor = get_traffic_predictor()


class AutoScaler:
    """
    Autonomous auto-scaling.

    Pre-scales infrastructure based on predicted traffic.
    Learns optimal scaling patterns per workspace.
    """

    def __init__(self):
        self.scaling_decisions: Dict[str, Dict] = {}  # workspace_id -> scaling config

    def should_scale_up(
        self,
        workspace_id: str,
        current_workers: int,
    ) -> Dict[str, any]:
        """
        Decide if we should scale up based on predictions.

        Returns scaling decision with reasoning.
        """
        # Predict traffic spike
        spike_prediction = traffic_predictor.predict_spike(
            workspace_id=workspace_id,
            hours_ahead=2,
        )

        if spike_prediction and spike_prediction.get("will_spike"):
            # Pre-scale before spike
            predicted_load = spike_prediction["predicted_requests"]
            normal_load = spike_prediction["normal_avg"]

            # Estimate workers needed (assume 100 requests per worker per hour)
            workers_needed = max(1, int(predicted_load / 100))

            if workers_needed > current_workers:
                return {
                    "should_scale": True,
                    "current_workers": current_workers,
                    "recommended_workers": workers_needed,
                    "reason": (
                        f"Traffic spike predicted in {spike_prediction['spike_time']}: "
                        f"{spike_prediction['predicted_requests']} requests "
                        f"({spike_prediction['spike_multiplier']:.1f}x normal)"
                    ),
                    "scale_up_by": workers_needed - current_workers,
                }

        return {
            "should_scale": False,
            "reason": "No spike predicted",
        }

    def should_scale_down(
        self,
        workspace_id: str,
        current_workers: int,
    ) -> Dict[str, any]:
        """
        Decide if we should scale down based on predictions.

        Saves costs by scaling down during low-traffic periods.
        """
        # Predict traffic for next 4 hours
        prediction = traffic_predictor.predict_traffic(
            workspace_id=workspace_id,
            hours_ahead=4,
        )

        if not prediction.get("predicted"):
            return {
                "should_scale": False,
                "reason": "Not enough data",
            }

        # Check if all hours are low traffic
        predictions = prediction["predictions"]
        max_requests = max(p["predicted_requests"] for p in predictions)

        # If max is less than 50 requests/hour, can scale down
        if max_requests < 50 and current_workers > 1:
            workers_needed = max(1, int(max_requests / 100))

            return {
                "should_scale": True,
                "current_workers": current_workers,
                "recommended_workers": workers_needed,
                "reason": f"Low traffic predicted: max {max_requests} requests/hour",
                "scale_down_by": current_workers - workers_needed,
            }

        return {
            "should_scale": False,
            "reason": "Traffic too high to scale down",
        }


# Global auto-scaler
_auto_scaler = AutoScaler()


def get_auto_scaler() -> AutoScaler:
    """Get global auto-scaler instance."""
    return _auto_scaler
