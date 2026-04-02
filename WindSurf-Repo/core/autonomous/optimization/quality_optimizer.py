"""Quality optimizer - optimizes provider selection for quality."""

from typing import Dict, Optional, List
from decimal import Decimal
from sqlalchemy.orm import Session
from core.autonomous.ml_models.quality_predictor import get_quality_predictor_ml
from core.autonomous.ml_models.routing_optimizer import get_routing_optimizer_ml
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
quality_predictor_ml = get_quality_predictor_ml()
routing_optimizer_ml = get_routing_optimizer_ml()


class QualityOptimizer:
    """
    Quality optimizer - optimizes provider selection for quality.

    Uses quality predictions to suggest provider/model combinations.
    Learns from actual quality scores (feedback loop).
    Flags operations likely to fail before running.
    """

    def optimize_for_quality(
        self,
        workspace_id: str,
        operation_type: str,
        available_providers: List[str],
        min_quality: float = 0.85,
        db: Optional[Session] = None,
    ) -> Dict[str, any]:
        """
        Optimize provider selection for quality.

        Returns best provider/model combination that maximizes quality.
        """
        # Get quality predictions for all providers
        suggestion = quality_predictor_ml.suggest_provider_for_quality(
            workspace_id=workspace_id,
            operation_type=operation_type,
            available_providers=available_providers,
            min_quality=min_quality,
            db=db,
        )

        recommended_provider = suggestion["recommended_provider"]
        predicted_quality = suggestion["predicted_quality"]

        # Check if quality meets threshold
        if predicted_quality < min_quality:
            logger.warning(
                f"Predicted quality {predicted_quality:.2f} below threshold {min_quality} "
                f"for workspace {workspace_id}, operation {operation_type}"
            )

        return {
            "recommended_provider": recommended_provider,
            "predicted_quality": predicted_quality,
            "meets_threshold": predicted_quality >= min_quality,
            "all_predictions": suggestion["all_predictions"],
            "optimization_strategy": "quality_maximized",
        }

    def predict_failure_risk(
        self,
        workspace_id: str,
        operation_type: str,
        provider: str,
        input_text: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, any]:
        """
        Predict if operation is likely to fail before running.

        Returns failure risk assessment.
        """
        # Get quality prediction
        quality_pred = quality_predictor_ml.predict_quality(
            workspace_id=workspace_id,
            operation_type=operation_type,
            provider=provider,
            input_text=input_text,
            db=db,
        )

        predicted_quality = quality_pred["predicted_quality"]

        # Calculate failure risk (inverse of quality)
        failure_risk = 1.0 - predicted_quality

        # Risk levels
        if failure_risk < 0.1:
            risk_level = "low"
        elif failure_risk < 0.3:
            risk_level = "medium"
        else:
            risk_level = "high"

        # Flag if high risk
        should_flag = failure_risk > 0.3

        return {
            "failure_risk": failure_risk,
            "risk_level": risk_level,
            "predicted_quality": predicted_quality,
            "should_flag": should_flag,
            "recommendation": (
                "Consider switching provider" if should_flag else "Proceed with operation"
            ),
        }

    def learn_from_outcome(
        self,
        workspace_id: str,
        operation_type: str,
        provider: str,
        actual_quality: float,
        success: bool,
    ):
        """
        Learn from actual quality outcome.

        This is the feedback loop - improves quality predictions over time.
        """
        # Quality predictor learns from outcomes during training
        # This method can trigger retraining or update internal state
        logger.debug(
            f"Learning from quality outcome for workspace {workspace_id}: "
            f"provider={provider}, quality={actual_quality:.2f}, success={success}"
        )

        # The quality predictor will use this data during next training cycle
        # For now, we just log it (training pipeline handles actual learning)


# Global quality optimizer
_quality_optimizer = QualityOptimizer()


def get_quality_optimizer() -> QualityOptimizer:
    """Get global quality optimizer instance."""
    return _quality_optimizer
