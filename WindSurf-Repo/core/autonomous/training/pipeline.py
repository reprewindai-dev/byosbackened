"""AutoML training pipeline - retrains models automatically."""

from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import SessionLocal
from core.autonomous.ml_models.cost_predictor import get_cost_predictor_ml
from core.autonomous.ml_models.routing_optimizer import get_routing_optimizer_ml
from core.autonomous.training.drift_detector import get_drift_detector
from core.autonomous.feature_flags import get_feature_flags
from db.models import Workspace
import logging

logger = logging.getLogger(__name__)
drift_detector = get_drift_detector()
feature_flags = get_feature_flags()


class TrainingPipeline:
    """
    AutoML training pipeline.

    Retrains models weekly/monthly as new data arrives.
    This is what makes the system "get better over time."
    """

    def __init__(self):
        self.cost_predictor = get_cost_predictor_ml()
        self.routing_optimizer = get_routing_optimizer_ml()

    def train_all_workspaces(
        self,
        min_samples: int = 100,
    ) -> Dict[str, any]:
        """
        Train models for all workspaces with enough data.

        This runs weekly/monthly via cron job.
        """
        db = SessionLocal()
        results = {
            "trained": [],
            "skipped": [],
            "errors": [],
        }

        try:
            # Get all workspaces (with limit to prevent unbounded queries)
            # Max 10,000 workspaces per batch
            workspaces = db.query(Workspace).filter(Workspace.is_active == True).limit(10000).all()

            for workspace in workspaces:
                try:
                    # Check kill switch
                    if not feature_flags.is_enabled("model_retraining_enabled"):
                        logger.info("Model retraining disabled via kill switch, skipping")
                        continue

                    # Check for drift before training
                    drift_result = drift_detector.detect_drift(
                        workspace_id=workspace.id,
                        model_type="cost_predictor",
                        db=db,
                    )

                    # Train cost prediction model
                    cost_result = self.cost_predictor.train_model(
                        db=db,
                        workspace_id=workspace.id,
                        min_samples=min_samples,
                    )

                    # Log drift detection results
                    if drift_result.get("drift_detected"):
                        logger.info(
                            f"Drift detected for workspace {workspace.id}: "
                            f"severity={drift_result.get('severity')}, "
                            f"triggered retraining"
                        )

                    if cost_result.get("trained"):
                        results["trained"].append(
                            {
                                "workspace_id": workspace.id,
                                "model": "cost_predictor",
                                "mape": cost_result.get("mape"),
                            }
                        )
                    else:
                        results["skipped"].append(
                            {
                                "workspace_id": workspace.id,
                                "model": "cost_predictor",
                                "reason": cost_result.get("reason"),
                            }
                        )

                    # Learn routing from history
                    for operation_type in ["transcribe", "extract", "chat"]:
                        self.routing_optimizer.learn_from_history(
                            db=db,
                            workspace_id=workspace.id,
                            operation_type=operation_type,
                        )

                except Exception as e:
                    logger.error(f"Error training models for workspace {workspace.id}: {e}")
                    results["errors"].append(
                        {
                            "workspace_id": workspace.id,
                            "error": str(e),
                        }
                    )

            logger.info(
                f"Training complete: {len(results['trained'])} trained, "
                f"{len(results['skipped'])} skipped, {len(results['errors'])} errors"
            )

        finally:
            db.close()

        return results

    def train_workspace(
        self,
        workspace_id: str,
        min_samples: int = 100,
    ) -> Dict[str, any]:
        """Train models for specific workspace."""
        db = SessionLocal()
        results = {}

        try:
            # Train cost prediction
            cost_result = self.cost_predictor.train_model(
                db=db,
                workspace_id=workspace_id,
                min_samples=min_samples,
            )
            results["cost_predictor"] = cost_result

            # Learn routing
            for operation_type in ["transcribe", "extract", "chat"]:
                self.routing_optimizer.learn_from_history(
                    db=db,
                    workspace_id=workspace_id,
                    operation_type=operation_type,
                )

            results["routing_optimizer"] = {"learned": True}

        finally:
            db.close()

        return results


# Global training pipeline
_training_pipeline = TrainingPipeline()


def get_training_pipeline() -> TrainingPipeline:
    """Get global training pipeline instance."""
    return _training_pipeline
