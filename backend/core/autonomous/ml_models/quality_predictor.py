"""ML-powered quality prediction - predicts quality before running operations."""
from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import AIAuditLog
from core.autonomous.training.feature_engineering import get_feature_engineer
from core.autonomous.feature_flags import get_feature_flags
from core.config import get_settings
import logging
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import pickle
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
settings = get_settings()
feature_engineer = get_feature_engineer()
feature_flags = get_feature_flags()


class QualityPredictorML:
    """
    ML-powered quality predictor that learns per workspace.
    
    Predicts quality score before running operations.
    Suggests provider/model combinations that maximize quality.
    Learns from actual quality scores (feedback loop).
    """

    def __init__(self):
        self.models: Dict[str, Any] = {}  # workspace_id -> model
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    def predict_quality(
        self,
        workspace_id: str,
        operation_type: str,
        provider: str,
        model: Optional[str] = None,
        input_text: Optional[str] = None,
        input_tokens: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, any]:
        """
        Predict quality score before running operation.
        
        Returns predicted quality (0-1) with confidence.
        """
        # Check kill switch
        if not feature_flags.is_enabled("ml_cost_prediction_enabled"):
            logger.warning("ML quality prediction disabled via kill switch, using fallback")
            return self._fallback_prediction(provider, operation_type)
        
        # Load model for workspace (or use default if not trained)
        model_key = f"{workspace_id}:quality_predictor"
        
        if model_key not in self.models:
            # Try to load from S3
            if self._load_model_from_s3(model_key):
                logger.info(f"Loaded quality prediction model for workspace {workspace_id}")
            else:
                # No model yet - use rule-based fallback
                logger.debug(f"No quality model for workspace {workspace_id}, using fallback")
                return self._fallback_prediction(provider, operation_type)
        
        model_obj = self.models[model_key]
        
        # Extract features
        features = feature_engineer.extract_quality_features(
            operation_type=operation_type,
            provider=provider,
            model=model,
            input_text=input_text,
            input_tokens=input_tokens,
            workspace_id=workspace_id,
            db=db,
        )
        
        # Predict
        predicted_quality = model_obj["model"].predict([features])[0]
        predicted_quality = max(0.0, min(1.0, predicted_quality))  # Clamp to [0, 1]
        
        # Calculate confidence (based on model uncertainty)
        # For now, use ±0.05 as default confidence interval
        confidence_lower = max(0.0, predicted_quality - 0.05)
        confidence_upper = min(1.0, predicted_quality + 0.05)
        
        return {
            "predicted_quality": float(predicted_quality),
            "confidence_lower": confidence_lower,
            "confidence_upper": confidence_upper,
            "model_version": model_obj.get("version", "1.0"),
            "is_ml_prediction": True,
        }

    def suggest_provider_for_quality(
        self,
        workspace_id: str,
        operation_type: str,
        available_providers: List[str],
        min_quality: float = 0.85,
        db: Optional[Session] = None,
    ) -> Dict[str, any]:
        """
        Suggest provider/model combination that maximizes quality.
        
        Returns best provider with predicted quality.
        """
        best_provider = None
        best_quality = 0.0
        predictions = {}
        
        for provider in available_providers:
            pred = self.predict_quality(
                workspace_id=workspace_id,
                operation_type=operation_type,
                provider=provider,
                db=db,
            )
            
            predicted_quality = pred["predicted_quality"]
            predictions[provider] = pred
            
            if predicted_quality > best_quality and predicted_quality >= min_quality:
                best_quality = predicted_quality
                best_provider = provider
        
        if not best_provider:
            # Fallback to highest quality even if below threshold
            best_provider = max(predictions.keys(), key=lambda p: predictions[p]["predicted_quality"])
            best_quality = predictions[best_provider]["predicted_quality"]
        
        return {
            "recommended_provider": best_provider,
            "predicted_quality": best_quality,
            "all_predictions": predictions,
        }

    def train_model(
        self,
        db: Session,
        workspace_id: str,
        min_samples: int = 100,
    ) -> Dict[str, any]:
        """
        Train quality prediction model for workspace.
        
        Learns workspace-specific quality patterns.
        """
        # Check kill switch
        if not feature_flags.is_enabled("model_retraining_enabled"):
            logger.info("Model retraining disabled via kill switch")
            return {
                "trained": False,
                "reason": "Model retraining disabled via kill switch",
            }
        # Get historical operations with quality scores
        # Limit to last 30 days and max 10,000 samples
        cutoff = datetime.utcnow() - timedelta(days=30)
        logs = db.query(AIAuditLog).filter(
            AIAuditLog.workspace_id == workspace_id,
            AIAuditLog.actual_quality.isnot(None),
            AIAuditLog.created_at >= cutoff,  # Time-bound query
        ).limit(10000).all()
        
        if len(logs) < min_samples:
            logger.info(
                f"Not enough quality data for workspace {workspace_id}: "
                f"{len(logs)} < {min_samples}"
            )
            return {
                "trained": False,
                "reason": f"Need at least {min_samples} samples, have {len(logs)}",
            }
        
        # Prepare features and targets
        X = []
        y = []
        
        for log in logs:
            features = feature_engineer.extract_quality_features(
                operation_type=log.operation_type,
                provider=log.provider,
                model=log.model,
                input_tokens=log.input_tokens,
                workspace_id=workspace_id,
                db=db,
            )
            X.append(features)
            y.append(float(log.actual_quality))
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
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
        mae = mean_absolute_error(y_test, y_pred)
        
        # Generate version string
        model_version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Store model in memory
        model_key = f"{workspace_id}:quality_predictor"
        self.models[model_key] = {
            "model": model,
            "version": model_version,
            "mae": mae,
            "training_samples": len(X_train),
        }
        
        # Save to S3
        self._save_model_to_s3(model_key, self.models[model_key])
        
        # Store model metadata in database
        from db.models import MLModel
        from sqlalchemy import and_
        from decimal import Decimal
        
        # Check if there's an existing production model
        existing_production = db.query(MLModel).filter(
            and_(
                MLModel.workspace_id == workspace_id,
                MLModel.model_type == "quality_predictor",
                MLModel.is_production == True,
                MLModel.is_active == True,
            )
        ).first()
        
        # Create new model record (start as canary if production exists)
        is_production = existing_production is None
        is_active = True
        
        new_model = MLModel(
            workspace_id=workspace_id,
            model_type="quality_predictor",
            model_version=model_version,
            training_samples=len(X_train),
            test_samples=len(X_test),
            accuracy=Decimal(str(1.0 - mae)),  # Accuracy = 1 - MAE (for quality, lower MAE = higher accuracy)
            s3_key=f"ml_models/{model_key}.pkl",
            is_active=is_active,
            is_production=is_production,
        )
        db.add(new_model)
        
        # If there's an existing production model, compare performance
        if existing_production:
            old_mae = 1.0 - float(existing_production.accuracy) if existing_production.accuracy else 0.15
            
            # If new model is better (lower MAE), mark for promotion
            if mae < old_mae * 0.95:  # 5% improvement threshold
                logger.info(
                    f"New quality model performs better: MAE {mae:.4f} vs {old_mae:.4f}. "
                    f"Will promote after canary period."
                )
            else:
                logger.warning(
                    f"New quality model performs worse: MAE {mae:.4f} vs {old_mae:.4f}. "
                    f"Keeping old model in production."
                )
                new_model.is_active = False
        
        db.commit()
        db.refresh(new_model)
        
        logger.info(
            f"Trained quality prediction model for workspace {workspace_id}: "
            f"version={model_version}, MAE={mae:.4f}, samples={len(X_train)}, "
            f"is_production={is_production}"
        )
        
        return {
            "trained": True,
            "model_version": model_version,
            "mae": mae,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "is_production": is_production,
            "is_canary": not is_production,
        }

    def _fallback_prediction(
        self,
        provider: str,
        operation_type: str,
    ) -> Dict[str, any]:
        """Fallback to rule-based prediction if ML model not available."""
        # Simple rule-based quality estimates
        provider_quality = {
            "openai": 0.95,
            "huggingface": 0.85,
            "local": 0.80,
            "serpapi": 0.90,
        }
        
        predicted_quality = provider_quality.get(provider, 0.85)
        
        return {
            "predicted_quality": predicted_quality,
            "confidence_lower": predicted_quality - 0.1,
            "confidence_upper": predicted_quality + 0.1,
            "is_ml_prediction": False,
        }

    def _save_model_to_s3(self, model_key: str, model_data: Dict):
        """Save model to S3."""
        try:
            model_bytes = pickle.dumps(model_data)
            s3_key = f"ml_models/{model_key}.pkl"
            self.s3_client.put_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
                Body=model_bytes,
            )
            logger.debug(f"Saved quality model to S3: {s3_key}")
        except Exception as e:
            logger.error(f"Failed to save quality model to S3: {e}")

    def _load_model_from_s3(self, model_key: str, s3_key: Optional[str] = None) -> bool:
        """Load model from S3."""
        try:
            if s3_key is None:
                s3_key = f"ml_models/{model_key}.pkl"
            
            response = self.s3_client.get_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
            )
            model_data = pickle.loads(response['Body'].read())
            self.models[model_key] = model_data
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return False
            logger.error(f"Failed to load quality model from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load quality model from S3: {e}")
            return False
    
    def promote_canary_to_production(
        self,
        db: Session,
        workspace_id: str,
        canary_version: str,
    ) -> Dict[str, any]:
        """Promote canary quality model to production after validation."""
        from db.models import MLModel
        from sqlalchemy import and_
        
        canary_model = db.query(MLModel).filter(
            and_(
                MLModel.workspace_id == workspace_id,
                MLModel.model_type == "quality_predictor",
                MLModel.model_version == canary_version,
                MLModel.is_active == True,
            )
        ).first()
        
        if not canary_model:
            return {
                "promoted": False,
                "reason": f"Canary model {canary_version} not found",
            }
        
        production_model = db.query(MLModel).filter(
            and_(
                MLModel.workspace_id == workspace_id,
                MLModel.model_type == "quality_predictor",
                MLModel.is_production == True,
                MLModel.is_active == True,
            )
        ).first()
        
        if production_model:
            production_model.is_production = False
            production_model.is_active = False
        
        canary_model.is_production = True
        canary_model.is_active = True
        
        db.commit()
        
        logger.info(
            f"Promoted canary quality model {canary_version} to production for workspace {workspace_id}"
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
    ) -> Dict[str, any]:
        """Rollback to previous production quality model."""
        from db.models import MLModel
        from sqlalchemy import and_
        
        current_production = db.query(MLModel).filter(
            and_(
                MLModel.workspace_id == workspace_id,
                MLModel.model_type == "quality_predictor",
                MLModel.is_production == True,
                MLModel.is_active == True,
            )
        ).first()
        
        if not current_production:
            return {
                "rolled_back": False,
                "reason": "No production model found",
            }
        
        previous_production = db.query(MLModel).filter(
            and_(
                MLModel.workspace_id == workspace_id,
                MLModel.model_type == "quality_predictor",
                MLModel.is_production == True,
                MLModel.is_active == False,
            )
        ).order_by(MLModel.trained_at.desc()).first()
        
        if not previous_production:
            return {
                "rolled_back": False,
                "reason": "No previous production model found",
            }
        
        current_production.is_production = False
        current_production.is_active = False
        
        previous_production.is_production = True
        previous_production.is_active = True
        
        db.commit()
        
        logger.warning(
            f"Rolled back quality model to {previous_production.model_version} "
            f"for workspace {workspace_id} (was using {current_production.model_version})"
        )
        
        return {
            "rolled_back": True,
            "new_production_version": previous_production.model_version,
            "rolled_back_from_version": current_production.model_version,
        }


# Global instance
_quality_predictor_ml = QualityPredictorML()


def get_quality_predictor_ml() -> QualityPredictorML:
    """Get global quality predictor ML instance."""
    return _quality_predictor_ml
