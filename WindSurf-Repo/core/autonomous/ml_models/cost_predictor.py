"""ML-powered cost prediction - learns per workspace."""

import pickle
from typing import Dict, Optional, List, Any
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import CostPrediction
from core.config import get_settings
from core.tracing.tracer import get_tracer
from core.autonomous.feature_flags import get_feature_flags
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
settings = get_settings()
tracer = get_tracer()
feature_flags = get_feature_flags()


class CostPredictorML:
    """
    ML-powered cost predictor that learns per workspace.

    Each workspace gets its own model, learning THEIR patterns over time.
    This creates non-portable intelligence - switching = losing years of tuning.
    """

    def __init__(self):
        self.models: Dict[str, Any] = {}  # workspace_id -> model
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    def predict_cost(
        self,
        workspace_id: str,
        operation_type: str,
        provider: str,
        input_tokens: int,
        estimated_output_tokens: int,
        model: Optional[str] = None,
        time_of_day: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Predict cost using workspace-specific ML model.

        Supports canary deployment: routes 10% of traffic to canary model if available.
        Falls back to rule-based if model not trained yet.
        """
        import random

        # Load models for workspace
        model_key = f"{workspace_id}:cost_predictor"

        # Check for canary model if db provided
        use_canary = False
        if db:
            from db.models import MLModel
            from sqlalchemy import and_

            # Check for active canary model
            canary_model = (
                db.query(MLModel)
                .filter(
                    and_(
                        MLModel.workspace_id == workspace_id,
                        MLModel.model_type == "cost_predictor",
                        MLModel.is_active == True,
                        MLModel.is_production == False,  # Canary is not production
                    )
                )
                .order_by(MLModel.trained_at.desc())
                .first()
            )

            # Route 10% of traffic to canary
            if canary_model and random.random() < 0.1:
                use_canary = True
                canary_key = f"{workspace_id}:cost_predictor:canary:{canary_model.model_version}"

                # Load canary model if not in memory
                if canary_key not in self.models:
                    if self._load_model_from_s3(
                        canary_key, s3_key=f"ml_models/{canary_model.s3_key}"
                    ):
                        logger.debug(
                            f"Loaded canary model {canary_model.model_version} for workspace {workspace_id}"
                        )
                    else:
                        use_canary = False  # Fallback to production if canary can't load

        # Load production model if not using canary
        if not use_canary:
            if model_key not in self.models:
                # Try to load from S3
                if self._load_model_from_s3(model_key):
                    logger.info(f"Loaded ML model for workspace {workspace_id}")
                else:
                    # No model yet - use rule-based fallback
                    logger.debug(f"No ML model for workspace {workspace_id}, using fallback")
                    return self._fallback_prediction(
                        provider, operation_type, input_tokens, estimated_output_tokens, model
                    )

        # Get model object (canary or production)
        if use_canary:
            model_obj = self.models.get(canary_key)
            model_version = canary_model.model_version
            is_canary = True
        else:
            model_obj = self.models[model_key]
            model_version = model_obj.get("version", "1.0")
            is_canary = False

        if not model_obj:
            # Fallback if canary failed to load
            return self._fallback_prediction(
                provider, operation_type, input_tokens, estimated_output_tokens, model
            )

        # Lazy import heavy ML deps (avoids import-time native DLL load failures in some envs)
        try:
            import numpy as np  # noqa: F401
        except Exception:
            return self._fallback_prediction(
                provider, operation_type, input_tokens, estimated_output_tokens, model
            )

        # Prepare features
        features = self._extract_features(
            operation_type,
            provider,
            input_tokens,
            estimated_output_tokens,
            model,
            time_of_day,
            workspace_id,
        )

        # Predict
        predicted_cost = model_obj["model"].predict([features])[0]

        # Calculate confidence interval (based on model uncertainty)
        # For now, use ±5% as default
        confidence_lower = Decimal(str(predicted_cost * 0.95))
        confidence_upper = Decimal(str(predicted_cost * 1.05))

        return {
            "predicted_cost": Decimal(str(predicted_cost)),
            "confidence_lower": confidence_lower,
            "confidence_upper": confidence_upper,
            "model_version": model_version,
            "is_ml_prediction": True,
            "is_canary": is_canary,
        }

    def train_model(
        self,
        db: Session,
        workspace_id: str,
        min_samples: int = 100,
    ) -> Dict[str, Any]:
        """
        Train ML model for workspace using historical data.

        This is what creates the moat - learns workspace-specific patterns.
        """
        # Check kill switch
        if not feature_flags.is_enabled("model_retraining_enabled"):
            logger.info("Model retraining disabled via kill switch")
            return {
                "trained": False,
                "reason": "Model retraining disabled via kill switch",
            }
        # Get historical predictions with actuals
        # Limit to last 30 days and max 10,000 samples
        cutoff = datetime.utcnow() - timedelta(days=30)
        predictions = (
            db.query(CostPrediction)
            .filter(
                CostPrediction.workspace_id == workspace_id,
                CostPrediction.actual_cost.isnot(None),  # Only use completed predictions
                CostPrediction.created_at >= cutoff,  # Time-bound query
            )
            .limit(10000)
            .all()
        )

        if len(predictions) < min_samples:
            logger.info(
                f"Not enough data for workspace {workspace_id}: "
                f"{len(predictions)} < {min_samples}"
            )
            return {
                "trained": False,
                "reason": f"Need at least {min_samples} samples, have {len(predictions)}",
            }

        # Prepare features and targets
        X = []
        y = []

        for pred in predictions:
            features = self._extract_features(
                pred.operation_type,
                pred.provider,
                pred.input_tokens,
                pred.estimated_output_tokens,
                pred.model,
                pred.created_at.hour if pred.created_at else None,
                workspace_id,
            )
            X.append(features)
            y.append(float(pred.actual_cost))

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train model
        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        mape = mean_absolute_percentage_error(y_test, y_pred)

        # Generate version string
        model_version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Store model in memory
        model_key = f"{workspace_id}:cost_predictor"
        self.models[model_key] = {
            "model": model,
            "version": model_version,
            "mape": mape,
            "training_samples": len(X_train),
        }

        # Save to S3 (non-portable - can't export easily)
        self._save_model_to_s3(model_key, self.models[model_key])

        # Store model metadata in database
        from db.models import MLModel
        from sqlalchemy import and_

        # Check if there's an existing production model
        existing_production = (
            db.query(MLModel)
            .filter(
                and_(
                    MLModel.workspace_id == workspace_id,
                    MLModel.model_type == "cost_predictor",
                    MLModel.is_production == True,
                    MLModel.is_active == True,
                )
            )
            .first()
        )

        # Create new model record (start as canary if production exists)
        is_production = existing_production is None
        is_active = True

        new_model = MLModel(
            workspace_id=workspace_id,
            model_type="cost_predictor",
            model_version=model_version,
            training_samples=len(X_train),
            test_samples=len(X_test),
            mape=Decimal(str(mape)),
            s3_key=f"ml_models/{model_key}.pkl",
            is_active=is_active,
            is_production=is_production,
        )
        db.add(new_model)

        # If there's an existing production model, compare performance
        if existing_production:
            old_mape = float(existing_production.mape) if existing_production.mape else 1.0

            # If new model is better (lower MAPE), mark for promotion
            if mape < old_mape * 0.95:  # 5% improvement threshold
                logger.info(
                    f"New model performs better: MAPE {mape:.2%} vs {old_mape:.2%}. "
                    f"Will promote after canary period."
                )
                # Keep as canary for now (will be promoted after validation)
            else:
                logger.warning(
                    f"New model performs worse: MAPE {mape:.2%} vs {old_mape:.2%}. "
                    f"Keeping old model in production."
                )
                # Don't activate new model if it's worse
                new_model.is_active = False

        db.commit()
        db.refresh(new_model)

        logger.info(
            f"Trained cost prediction model for workspace {workspace_id}: "
            f"version={model_version}, MAPE={mape:.2%}, samples={len(X_train)}, "
            f"is_production={is_production}"
        )

        return {
            "trained": True,
            "model_version": model_version,
            "mape": mape,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "is_production": is_production,
            "is_canary": not is_production,
        }

    def _extract_features(
        self,
        operation_type: str,
        provider: str,
        input_tokens: int,
        estimated_output_tokens: int,
        model: Optional[str],
        time_of_day: Optional[int],
        workspace_id: str,
    ) -> List[float]:
        """Extract features for ML model."""
        # Encode categorical features
        operation_types = ["transcribe", "extract", "chat", "embed", "search"]
        providers = ["huggingface", "openai", "local", "serpapi"]

        # One-hot encode operation type
        operation_encoded = [1.0 if op == operation_type else 0.0 for op in operation_types]

        # One-hot encode provider
        provider_encoded = [1.0 if p == provider else 0.0 for p in providers]

        # Numerical features
        features = [
            float(input_tokens),
            float(estimated_output_tokens),
            float(time_of_day) if time_of_day else 12.0,  # Default to noon
            float(len(workspace_id)) % 10,  # Workspace hash (for workspace-specific patterns)
        ]

        return operation_encoded + provider_encoded + features

    def _fallback_prediction(
        self,
        provider: str,
        operation_type: str,
        input_tokens: int,
        estimated_output_tokens: int,
        model: Optional[str],
    ) -> Dict[str, Any]:
        """Fallback to rule-based prediction if ML model not available."""
        # Simple rule-based (from existing CostCalculator logic)
        if provider == "openai":
            input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * Decimal("0.15")
            output_cost = (Decimal(estimated_output_tokens) / Decimal(1_000_000)) * Decimal("0.60")
            predicted_cost = input_cost + output_cost
        elif provider == "huggingface":
            predicted_cost = Decimal("0.00")
        else:
            predicted_cost = Decimal("0.001")

        return {
            "predicted_cost": predicted_cost,
            "confidence_lower": predicted_cost * Decimal("0.95"),
            "confidence_upper": predicted_cost * Decimal("1.05"),
            "is_ml_prediction": False,
        }

    def _save_model_to_s3(self, model_key: str, model_data: Dict):
        """Save model to S3 (non-portable - creates lock-in)."""
        try:
            # Serialize model
            model_bytes = pickle.dumps(model_data)

            # Save to S3
            s3_key = f"ml_models/{model_key}.pkl"
            self.s3_client.put_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
                Body=model_bytes,
            )
            logger.debug(f"Saved model to S3: {s3_key}")
        except Exception as e:
            logger.error(f"Failed to save model to S3: {e}")

    def _load_model_from_s3(self, model_key: str, s3_key: Optional[str] = None) -> bool:
        """Load model from S3."""
        try:
            if s3_key is None:
                s3_key = f"ml_models/{model_key}.pkl"

            response = self.s3_client.get_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
            )
            model_data = pickle.loads(response["Body"].read())
            self.models[model_key] = model_data
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return False
            logger.error(f"Failed to load model from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load model from S3: {e}")
            return False

    def promote_canary_to_production(
        self,
        db: Session,
        workspace_id: str,
        canary_version: str,
    ) -> Dict[str, Any]:
        """
        Promote canary model to production after validation period.

        This is called after canary model has been validated (e.g., after 7 days).
        """
        from db.models import MLModel
        from sqlalchemy import and_

        # Get canary model
        canary_model = (
            db.query(MLModel)
            .filter(
                and_(
                    MLModel.workspace_id == workspace_id,
                    MLModel.model_type == "cost_predictor",
                    MLModel.model_version == canary_version,
                    MLModel.is_active == True,
                )
            )
            .first()
        )

        if not canary_model:
            return {
                "promoted": False,
                "reason": f"Canary model {canary_version} not found",
            }

        # Get current production model
        production_model = (
            db.query(MLModel)
            .filter(
                and_(
                    MLModel.workspace_id == workspace_id,
                    MLModel.model_type == "cost_predictor",
                    MLModel.is_production == True,
                    MLModel.is_active == True,
                )
            )
            .first()
        )

        # Demote old production model
        if production_model:
            production_model.is_production = False
            production_model.is_active = False  # Archive old model

        # Promote canary to production
        canary_model.is_production = True
        canary_model.is_active = True

        db.commit()

        logger.info(
            f"Promoted canary model {canary_version} to production for workspace {workspace_id}"
        )

        return {
            "promoted": True,
            "new_production_version": canary_version,
            "old_production_version": production_model.model_version if production_model else None,
        }

    def rollback_to_previous_model(
        self,
        db: Session,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """
        Rollback to previous production model if current model performs poorly.

        This is called when production model shows degradation.
        """
        from db.models import MLModel
        from sqlalchemy import and_

        # Get current production model
        current_production = (
            db.query(MLModel)
            .filter(
                and_(
                    MLModel.workspace_id == workspace_id,
                    MLModel.model_type == "cost_predictor",
                    MLModel.is_production == True,
                    MLModel.is_active == True,
                )
            )
            .first()
        )

        if not current_production:
            return {
                "rolled_back": False,
                "reason": "No production model found",
            }

        # Get previous production model (most recent inactive production)
        previous_production = (
            db.query(MLModel)
            .filter(
                and_(
                    MLModel.workspace_id == workspace_id,
                    MLModel.model_type == "cost_predictor",
                    MLModel.is_production == True,
                    MLModel.is_active == False,
                )
            )
            .order_by(MLModel.trained_at.desc())
            .first()
        )

        if not previous_production:
            return {
                "rolled_back": False,
                "reason": "No previous production model found",
            }

        # Deactivate current model
        current_production.is_production = False
        current_production.is_active = False

        # Reactivate previous model
        previous_production.is_production = True
        previous_production.is_active = True

        db.commit()

        logger.warning(
            f"Rolled back to previous model {previous_production.model_version} "
            f"for workspace {workspace_id} (was using {current_production.model_version})"
        )

        return {
            "rolled_back": True,
            "new_production_version": previous_production.model_version,
            "rolled_back_from_version": current_production.model_version,
        }


# Global instance
_cost_predictor_ml = CostPredictorML()


def get_cost_predictor_ml() -> CostPredictorML:
    """Get global cost predictor ML instance."""
    return _cost_predictor_ml
