"""Drift detection - detect data drift and concept drift."""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import CostPrediction, AIAuditLog, MLModel
from core.autonomous.training.feature_engineering import get_feature_engineer
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
feature_engineer = get_feature_engineer()


class DriftDetector:
    """
    Detect data drift and concept drift.

    Data drift: Feature distribution changes over time
    Concept drift: Model accuracy degrades over time
    """

    def detect_drift(
        self,
        workspace_id: str,
        model_type: str,  # "cost_predictor", "quality_predictor"
        db: Optional[Session] = None,
    ) -> Dict[str, any]:
        """
        Detect both data drift and concept drift.

        Returns drift detection results with recommendations.
        """
        # Lazy import heavy deps; if unavailable, degrade gracefully
        try:
            import numpy as np  # noqa: F401
            from scipy import stats  # noqa: F401
        except Exception:
            return {
                "drift_detected": False,
                "reason": "Drift detection dependencies unavailable/blocked",
            }

        if not db:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            # Get current production model
            production_model = (
                db.query(MLModel)
                .filter(
                    MLModel.workspace_id == workspace_id,
                    MLModel.model_type == model_type,
                    MLModel.is_production == True,
                    MLModel.is_active == True,
                )
                .first()
            )

            if not production_model:
                return {
                    "drift_detected": False,
                    "reason": "No production model found",
                }

            # Detect data drift
            data_drift = self._detect_data_drift(
                db=db,
                workspace_id=workspace_id,
                model_type=model_type,
                production_model=production_model,
            )

            # Detect concept drift
            concept_drift = self._detect_concept_drift(
                db=db,
                workspace_id=workspace_id,
                model_type=model_type,
                production_model=production_model,
            )

            # Combine results
            drift_detected = data_drift["drift_detected"] or concept_drift["drift_detected"]

            return {
                "drift_detected": drift_detected,
                "data_drift": data_drift,
                "concept_drift": concept_drift,
                "recommendation": ("Retrain model" if drift_detected else "No action needed"),
                "severity": (
                    max(
                        data_drift.get("severity", "low"),
                        concept_drift.get("severity", "low"),
                        key=lambda s: ["low", "medium", "high", "critical"].index(s),
                    )
                    if drift_detected
                    else "low"
                ),
            }
        finally:
            if should_close:
                db.close()

    def _detect_data_drift(
        self,
        db: Session,
        workspace_id: str,
        model_type: str,
        production_model: MLModel,
    ) -> Dict[str, any]:
        """
        Detect data drift by comparing feature distributions.

        Compares recent data (last 7 days) vs training data (when model was trained).
        """
        # Get training period (when model was trained)
        training_cutoff = production_model.trained_at - timedelta(days=30)
        training_end = production_model.trained_at

        # Get recent data (last 7 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=7)

        if model_type == "cost_predictor":
            # Get training data features
            training_predictions = (
                db.query(CostPrediction)
                .filter(
                    CostPrediction.workspace_id == workspace_id,
                    CostPrediction.created_at >= training_cutoff,
                    CostPrediction.created_at <= training_end,
                    CostPrediction.actual_cost.isnot(None),
                )
                .limit(1000)
                .all()
            )

            # Get recent data features
            recent_predictions = (
                db.query(CostPrediction)
                .filter(
                    CostPrediction.workspace_id == workspace_id,
                    CostPrediction.created_at >= recent_cutoff,
                    CostPrediction.actual_cost.isnot(None),
                )
                .limit(1000)
                .all()
            )

            if len(training_predictions) < 100 or len(recent_predictions) < 50:
                return {
                    "drift_detected": False,
                    "reason": "Insufficient data for drift detection",
                }

            # Extract features for both periods
            training_features = []
            for pred in training_predictions[:100]:  # Sample for performance
                features = feature_engineer.extract_cost_features(
                    operation_type=pred.operation_type,
                    provider=pred.provider,
                    input_tokens=pred.input_tokens,
                    estimated_output_tokens=pred.estimated_output_tokens,
                    model=pred.model,
                    time_of_day=pred.created_at.hour if pred.created_at else None,
                    workspace_id=workspace_id,
                    reference_time=pred.created_at,  # Use actual time for consistency
                )
                training_features.append(features)

            recent_features = []
            for pred in recent_predictions[:100]:  # Sample for performance
                features = feature_engineer.extract_cost_features(
                    operation_type=pred.operation_type,
                    provider=pred.provider,
                    input_tokens=pred.input_tokens,
                    estimated_output_tokens=pred.estimated_output_tokens,
                    model=pred.model,
                    time_of_day=pred.created_at.hour if pred.created_at else None,
                    workspace_id=workspace_id,
                    reference_time=pred.created_at,
                )
                recent_features.append(features)

            # Compare distributions using Kolmogorov-Smirnov test
            drift_scores = []
            for feature_idx in range(len(training_features[0])):
                training_values = [f[feature_idx] for f in training_features]
                recent_values = [f[feature_idx] for f in recent_features]

                # KS test for distribution comparison
                if len(training_values) > 0 and len(recent_values) > 0:
                    ks_statistic, p_value = stats.ks_2samp(training_values, recent_values)
                    drift_scores.append(
                        {
                            "feature_idx": feature_idx,
                            "ks_statistic": float(ks_statistic),
                            "p_value": float(p_value),
                            "drift_detected": p_value < 0.05,  # Significant drift
                        }
                    )

            # Determine if drift detected
            significant_drifts = [d for d in drift_scores if d["drift_detected"]]
            drift_detected = (
                len(significant_drifts) > len(drift_scores) * 0.2
            )  # >20% of features drifted

            severity = "low"
            if len(significant_drifts) > len(drift_scores) * 0.5:
                severity = "high"
            elif len(significant_drifts) > len(drift_scores) * 0.3:
                severity = "medium"

            return {
                "drift_detected": drift_detected,
                "severity": severity,
                "drifted_features_count": len(significant_drifts),
                "total_features": len(drift_scores),
                "drift_score": len(significant_drifts) / len(drift_scores) if drift_scores else 0.0,
                "feature_drifts": drift_scores[:10],  # Top 10
            }

        else:
            # For other model types, use similar approach
            return {
                "drift_detected": False,
                "reason": f"Data drift detection not implemented for {model_type}",
            }

    def _detect_concept_drift(
        self,
        db: Session,
        workspace_id: str,
        model_type: str,
        production_model: MLModel,
    ) -> Dict[str, any]:
        """
        Detect concept drift by monitoring prediction accuracy degradation.

        Compares recent prediction accuracy vs training accuracy.
        """
        # Get recent predictions with actuals
        recent_cutoff = datetime.utcnow() - timedelta(days=7)

        if model_type == "cost_predictor":
            recent_predictions = (
                db.query(CostPrediction)
                .filter(
                    CostPrediction.workspace_id == workspace_id,
                    CostPrediction.created_at >= recent_cutoff,
                    CostPrediction.actual_cost.isnot(None),
                    CostPrediction.predicted_cost.isnot(None),
                )
                .limit(1000)
                .all()
            )

            if len(recent_predictions) < 50:
                return {
                    "drift_detected": False,
                    "reason": "Insufficient recent predictions",
                }

            # Calculate recent MAPE
            errors = []
            for pred in recent_predictions:
                if pred.actual_cost and pred.predicted_cost:
                    error = abs(float(pred.actual_cost) - float(pred.predicted_cost)) / float(
                        pred.actual_cost
                    )
                    errors.append(error)

            if not errors:
                return {
                    "drift_detected": False,
                    "reason": "No prediction errors to analyze",
                }

            recent_mape = np.mean(errors) * 100  # Convert to percentage

            # Compare with training MAPE
            training_mape = float(production_model.mape) * 100 if production_model.mape else 5.0

            # Detect degradation (recent MAPE > training MAPE * 1.2 = 20% worse)
            degradation_ratio = recent_mape / training_mape if training_mape > 0 else 1.0
            drift_detected = degradation_ratio > 1.2

            severity = "low"
            if degradation_ratio > 2.0:
                severity = "critical"
            elif degradation_ratio > 1.5:
                severity = "high"
            elif degradation_ratio > 1.2:
                severity = "medium"

            return {
                "drift_detected": drift_detected,
                "severity": severity,
                "training_mape": training_mape,
                "recent_mape": recent_mape,
                "degradation_ratio": degradation_ratio,
                "degradation_percent": (degradation_ratio - 1.0) * 100,
            }

        elif model_type == "quality_predictor":
            # Similar approach for quality predictor
            recent_logs = (
                db.query(AIAuditLog)
                .filter(
                    AIAuditLog.workspace_id == workspace_id,
                    AIAuditLog.created_at >= recent_cutoff,
                    AIAuditLog.actual_quality.isnot(None),
                )
                .limit(1000)
                .all()
            )

            if len(recent_logs) < 50:
                return {
                    "drift_detected": False,
                    "reason": "Insufficient recent quality data",
                }

            # Calculate recent MAE (would need predicted quality stored)
            # For now, use a simplified approach
            return {
                "drift_detected": False,
                "reason": "Concept drift detection for quality_predictor needs predicted quality storage",
            }

        else:
            return {
                "drift_detected": False,
                "reason": f"Concept drift detection not implemented for {model_type}",
            }

    def should_retrain(
        self,
        workspace_id: str,
        model_type: str,
        db: Optional[Session] = None,
    ) -> bool:
        """
        Determine if model should be retrained based on drift detection.

        Returns True if significant drift detected.
        """
        drift_result = self.detect_drift(
            workspace_id=workspace_id,
            model_type=model_type,
            db=db,
        )

        if not drift_result.get("drift_detected"):
            return False

        # Retrain if medium or high severity drift
        severity = drift_result.get("severity", "low")
        return severity in ["medium", "high", "critical"]


# Global drift detector
_drift_detector = DriftDetector()


def get_drift_detector() -> DriftDetector:
    """Get global drift detector instance."""
    return _drift_detector
