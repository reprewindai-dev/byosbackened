"""Feature engineering for ML models - extract features from historical data."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import CostPrediction, RoutingDecision, AIAuditLog
from decimal import Decimal
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Feature engineering for ML models.
    
    Extracts features from historical data to train better models.
    Creates workspace-specific features that capture patterns.
    """

    def extract_cost_features(
        self,
        operation_type: str,
        provider: str,
        input_tokens: int,
        estimated_output_tokens: int,
        model: Optional[str] = None,
        time_of_day: Optional[int] = None,
        workspace_id: Optional[str] = None,
        db: Optional[Session] = None,
        reference_time: Optional[datetime] = None,
    ) -> List[float]:
        """
        Extract features for cost prediction model.
        
        Features include:
        - Operation type (one-hot encoded)
        - Provider (one-hot encoded)
        - Token counts (input/output)
        - Time features (hour of day, day of week)
        - Historical patterns (avg cost for this operation/provider)
        - Workspace-specific features
        
        This function is IDEMPOTENT: calling it multiple times with the same inputs
        produces identical feature vectors. Use reference_time parameter to ensure
        deterministic time-based features.
        
        Args:
            reference_time: Optional datetime to use for time features (for idempotency).
                           If None, uses current time (non-deterministic).
        """
        features = []
        
        # Categorical features (one-hot encoded) - ORDERED for idempotency
        operation_types = sorted(["transcribe", "extract", "chat", "embed", "search"])
        providers = sorted(["huggingface", "openai", "local", "serpapi"])
        
        # One-hot encode operation type
        operation_encoded = [1.0 if op == operation_type else 0.0 for op in operation_types]
        features.extend(operation_encoded)
        
        # One-hot encode provider
        provider_encoded = [1.0 if p == provider else 0.0 for p in providers]
        features.extend(provider_encoded)
        
        # Numerical features (deterministic)
        features.append(float(input_tokens))
        features.append(float(estimated_output_tokens))
        features.append(float(estimated_output_tokens / input_tokens) if input_tokens > 0 else 0.0)  # Output/input ratio
        
        # Time features (use reference_time for idempotency)
        if time_of_day is not None:
            hour = time_of_day
        elif reference_time is not None:
            hour = reference_time.hour
        else:
            # Non-deterministic: use current time
            hour = datetime.utcnow().hour
        
        features.append(float(hour))
        # Encode hour as sin/cos for cyclical nature (deterministic given hour)
        features.append(np.sin(2 * np.pi * hour / 24))
        features.append(np.cos(2 * np.pi * hour / 24))
        
        # Day of week (0=Monday, 6=Sunday)
        if reference_time is not None:
            day_of_week = reference_time.weekday()
        else:
            day_of_week = datetime.utcnow().weekday()
        
        features.append(float(day_of_week))
        features.append(np.sin(2 * np.pi * day_of_week / 7))
        features.append(np.cos(2 * np.pi * day_of_week / 7))
        
        # Historical patterns (if workspace_id and db provided)
        # These are deterministic given the same data and time window
        if workspace_id and db:
            historical_features = self._extract_historical_features(
                db=db,
                workspace_id=workspace_id,
                operation_type=operation_type,
                provider=provider,
                reference_time=reference_time,
            )
            features.extend(historical_features)
        else:
            # Default historical features (zeros)
            features.extend([0.0, 0.0, 0.0, 0.0])  # avg_cost, std_cost, count, last_cost
        
        # Workspace-specific hash (deterministic - Python hash is stable within a process)
        if workspace_id:
            # Use deterministic hash (modulo to keep in [0, 1))
            workspace_hash = float(abs(hash(workspace_id)) % 100) / 100.0
            features.append(workspace_hash)
        else:
            features.append(0.0)
        
        return features

    def extract_routing_features(
        self,
        workspace_id: str,
        operation_type: str,
        available_providers: List[str],
        constraints: Dict,
        db: Optional[Session] = None,
    ) -> Dict[str, List[float]]:
        """
        Extract features for routing optimization.
        
        Returns features for each provider.
        """
        provider_features = {}
        
        for provider in available_providers:
            features = []
            
            # Provider encoding
            providers = ["huggingface", "openai", "local", "serpapi"]
            provider_encoded = [1.0 if p == provider else 0.0 for p in providers]
            features.extend(provider_encoded)
            
            # Operation type encoding
            operation_types = ["transcribe", "extract", "chat", "embed", "search"]
            operation_encoded = [1.0 if op == operation_type else 0.0 for op in operation_types]
            features.extend(operation_encoded)
            
            # Constraints
            features.append(float(constraints.get("max_cost", 0.01)) if constraints.get("max_cost") else 0.01)
            features.append(float(constraints.get("min_quality", 0.0)) if constraints.get("min_quality") else 0.0)
            features.append(float(constraints.get("max_latency_ms", 10000)) if constraints.get("max_latency_ms") else 10000.0)
            
            # Strategy encoding
            strategy = constraints.get("strategy", "cost_optimized")
            strategies = ["cost_optimized", "quality_optimized", "speed_optimized", "hybrid"]
            strategy_encoded = [1.0 if s == strategy else 0.0 for s in strategies]
            features.extend(strategy_encoded)
            
            # Historical performance (if db provided)
            if db:
                hist_features = self._extract_provider_historical_features(
                    db=db,
                    workspace_id=workspace_id,
                    operation_type=operation_type,
                    provider=provider,
                )
                features.extend(hist_features)
            else:
                # Default historical features
                features.extend([0.0, 0.0, 0.0, 0.0])  # avg_cost, avg_quality, avg_latency, success_rate
            
            provider_features[provider] = features
        
        return provider_features

    def _extract_historical_features(
        self,
        db: Session,
        workspace_id: str,
        operation_type: str,
        provider: str,
        days_back: int = 30,
        reference_time: Optional[datetime] = None,
    ) -> List[float]:
        """
        Extract historical cost features.
        
        IDEMPOTENT: Results are deterministic given the same data and time window.
        Uses reference_time for consistent cutoff calculation.
        """
        if reference_time is None:
            reference_time = datetime.utcnow()
        
        cutoff = reference_time - timedelta(days=days_back)
        
        # ORDER BY created_at for deterministic ordering
        predictions = db.query(CostPrediction).filter(
            CostPrediction.workspace_id == workspace_id,
            CostPrediction.operation_type == operation_type,
            CostPrediction.provider == provider,
            CostPrediction.created_at >= cutoff,
            CostPrediction.actual_cost.isnot(None),
        ).order_by(CostPrediction.created_at.asc()).limit(10000).all()  # Limit to prevent unbounded queries
        
        if not predictions:
            return [0.0, 0.0, 0.0, 0.0]
        
        # Extract costs in deterministic order
        costs = [float(p.actual_cost) for p in predictions]
        
        # Statistical features (deterministic given same data)
        avg_cost = np.mean(costs)
        std_cost = np.std(costs) if len(costs) > 1 else 0.0
        count = len(costs)
        # Last cost is deterministic due to ordering
        last_cost = float(predictions[-1].actual_cost) if predictions else 0.0
        
        return [avg_cost, std_cost, float(count), last_cost]

    def _extract_provider_historical_features(
        self,
        db: Session,
        workspace_id: str,
        operation_type: str,
        provider: str,
        days_back: int = 30,
        reference_time: Optional[datetime] = None,
    ) -> List[float]:
        """
        Extract historical routing features for provider.
        
        IDEMPOTENT: Results are deterministic given the same data and time window.
        """
        if reference_time is None:
            reference_time = datetime.utcnow()
        
        cutoff = reference_time - timedelta(days=days_back)
        
        # ORDER BY created_at for deterministic ordering
        decisions = db.query(RoutingDecision).filter(
            RoutingDecision.workspace_id == workspace_id,
            RoutingDecision.operation_type == operation_type,
            RoutingDecision.selected_provider == provider,
            RoutingDecision.created_at >= cutoff,
            RoutingDecision.actual_cost.isnot(None),
        ).order_by(RoutingDecision.created_at.asc()).limit(10000).all()  # Limit to prevent unbounded queries
        
        if not decisions:
            return [0.0, 0.0, 0.0, 0.0]
        
        # Extract in deterministic order
        costs = [float(d.actual_cost) for d in decisions if d.actual_cost]
        qualities = [
            float(d.actual_quality) for d in decisions
            if d.actual_quality is not None
        ]
        latencies = [
            d.actual_latency_ms for d in decisions
            if d.actual_latency_ms is not None
        ]
        successes = [
            1.0 if d.actual_cost and d.actual_cost > 0 else 0.0
            for d in decisions
        ]
        
        # Statistical features (deterministic given same data)
        avg_cost = np.mean(costs) if costs else 0.0
        avg_quality = np.mean(qualities) if qualities else 0.85
        avg_latency = np.mean(latencies) if latencies else 2000.0
        success_rate = np.mean(successes) if successes else 1.0
        
        return [avg_cost, avg_quality, avg_latency, success_rate]

    def extract_quality_features(
        self,
        operation_type: str,
        provider: str,
        model: Optional[str] = None,
        input_text: Optional[str] = None,
        input_tokens: Optional[int] = None,
        workspace_id: Optional[str] = None,
        db: Optional[Session] = None,
        reference_time: Optional[datetime] = None,
    ) -> List[float]:
        """
        Extract features for quality prediction.
        
        Features include:
        - Operation type
        - Provider/model combination
        - Input characteristics (length, complexity)
        - Historical quality patterns
        
        This function is IDEMPOTENT: calling it multiple times with the same inputs
        produces identical feature vectors.
        """
        features = []
        
        # Operation type encoding (ORDERED for idempotency)
        operation_types = sorted(["transcribe", "extract", "chat", "embed", "search"])
        operation_encoded = [1.0 if op == operation_type else 0.0 for op in operation_types]
        features.extend(operation_encoded)
        
        # Provider encoding (ORDERED for idempotency)
        providers = sorted(["huggingface", "openai", "local", "serpapi"])
        provider_encoded = [1.0 if p == provider else 0.0 for p in providers]
        features.extend(provider_encoded)
        
        # Model encoding (deterministic hash)
        if model:
            # Deterministic hash (abs + modulo to keep in [0, 1))
            model_hash = float(abs(hash(model)) % 100) / 100.0
            features.append(model_hash)
        else:
            features.append(0.0)
        
        # Input characteristics (deterministic)
        if input_text:
            features.append(float(len(input_text)))
            words = input_text.split()
            features.append(float(len(words)))  # Word count
            # Avg words per line (deterministic)
            lines = input_text.split('\n')
            avg_words_per_line = len(words) / len(lines) if lines else 1.0
            features.append(float(avg_words_per_line))
        elif input_tokens:
            features.append(float(input_tokens * 4))  # Approximate chars
            features.append(float(input_tokens))
            features.append(1.0)
        else:
            features.extend([0.0, 0.0, 0.0])
        
        # Historical quality (if db provided) - deterministic given same data
        if workspace_id and db:
            hist_quality = self._extract_historical_quality(
                db=db,
                workspace_id=workspace_id,
                operation_type=operation_type,
                provider=provider,
                reference_time=reference_time,
            )
            features.append(hist_quality)
        else:
            features.append(0.85)  # Default quality
        
        return features

    def _extract_historical_quality(
        self,
        db: Session,
        workspace_id: str,
        operation_type: str,
        provider: str,
        days_back: int = 30,
        reference_time: Optional[datetime] = None,
    ) -> float:
        """
        Extract historical average quality.
        
        IDEMPOTENT: Results are deterministic given the same data and time window.
        """
        if reference_time is None:
            reference_time = datetime.utcnow()
        
        cutoff = reference_time - timedelta(days=days_back)
        
        # ORDER BY created_at for deterministic ordering
        logs = db.query(AIAuditLog).filter(
            AIAuditLog.workspace_id == workspace_id,
            AIAuditLog.operation_type == operation_type,
            AIAuditLog.provider == provider,
            AIAuditLog.created_at >= cutoff,
            AIAuditLog.actual_quality.isnot(None),
        ).order_by(AIAuditLog.created_at.asc()).limit(10000).all()  # Limit to prevent unbounded queries
        
        if not logs:
            return 0.85  # Default
        
        # Extract in deterministic order
        qualities = [float(log.actual_quality) for log in logs if log.actual_quality]
        return np.mean(qualities) if qualities else 0.85


# Global feature engineer
_feature_engineer = FeatureEngineer()


def get_feature_engineer() -> FeatureEngineer:
    """Get global feature engineer instance."""
    return _feature_engineer
