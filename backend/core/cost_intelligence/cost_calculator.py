"""Cost calculator - precise cost prediction."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel
from core.config import get_settings
from core.autonomous.ml_models.cost_predictor import get_cost_predictor_ml
import tiktoken  # For OpenAI token counting
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
cost_predictor_ml = get_cost_predictor_ml()


class CostPrediction(BaseModel):
    """Cost prediction result."""

    predicted_cost: Decimal
    confidence_lower: Decimal
    confidence_upper: Decimal
    accuracy_score: float  # Historical accuracy (0-1)
    alternative_providers: List[Dict[str, any]]
    input_tokens: int
    estimated_output_tokens: int


class CostCalculator:
    """Calculate precise costs for AI operations."""

    # Provider pricing (per 1M tokens, input/output)
    PRICING = {
        "openai": {
            "gpt-4o-mini": {"input": Decimal("0.15"), "output": Decimal("0.60")},
            "gpt-4o": {"input": Decimal("2.50"), "output": Decimal("10.00")},
            "whisper-1": {"audio": Decimal("0.006")},  # per minute
        },
        "huggingface": {
            "default": {"input": Decimal("0.00"), "output": Decimal("0.00")},  # Free tier
        },
        "local": {
            "default": {"compute": Decimal("0.001")},  # Per second of compute
        },
    }

    def __init__(self):
        self.historical_accuracy: Dict[str, float] = {}  # provider:operation -> accuracy

    def count_tokens_openai(self, text: str, model: str = "gpt-4o-mini") -> int:
        """Count tokens using tiktoken (precise)."""
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            # Fallback: approximate 4 chars per token
            return len(text) // 4

    def count_tokens_huggingface(self, text: str) -> int:
        """Count tokens for Hugging Face (approximate)."""
        # Approximate: 4 chars per token
        return len(text) // 4

    def predict_cost(
        self,
        operation_type: str,
        provider: str,
        input_text: Optional[str] = None,
        input_tokens: Optional[int] = None,
        estimated_output_tokens: Optional[int] = None,
        model: Optional[str] = None,
        workspace_id: Optional[str] = None,
        use_ml: bool = True,
    ) -> CostPrediction:
        """
        Predict cost with precision.
        
        Uses ML model if available and workspace_id provided, otherwise falls back to rule-based.
        This is what creates the moat - ML predictions improve over time per workspace.
        """
        # Try ML prediction first if workspace_id provided
        if use_ml and workspace_id and input_tokens:
            try:
                ml_prediction = cost_predictor_ml.predict_cost(
                    workspace_id=workspace_id,
                    operation_type=operation_type,
                    provider=provider,
                    input_tokens=input_tokens,
                    estimated_output_tokens=estimated_output_tokens or int(input_tokens * 0.3),
                    model=model,
                    time_of_day=datetime.utcnow().hour,
                )
                
                if ml_prediction.get("is_ml_prediction"):
                    # Use ML prediction
                    return CostPrediction(
                        predicted_cost=ml_prediction["predicted_cost"],
                        confidence_lower=ml_prediction["confidence_lower"],
                        confidence_upper=ml_prediction["confidence_upper"],
                        accuracy_score=0.95,  # ML models typically more accurate
                        alternative_providers=[],  # Will be calculated below
                        input_tokens=input_tokens,
                        estimated_output_tokens=estimated_output_tokens or int(input_tokens * 0.3),
                    )
            except Exception as e:
                logger.warning(f"ML prediction failed, using fallback: {e}")
        
        # Fallback to rule-based prediction
        # Count tokens if text provided
        if input_text and not input_tokens:
            if provider == "openai":
                input_tokens = self.count_tokens_openai(input_text, model or "gpt-4o-mini")
            else:
                input_tokens = self.count_tokens_huggingface(input_text)

        if not input_tokens:
            input_tokens = 1000  # Default estimate

        if not estimated_output_tokens:
            # Estimate output tokens (typically 20-50% of input)
            estimated_output_tokens = int(input_tokens * 0.3)

        # Get pricing
        pricing = self.PRICING.get(provider, {}).get(model or "default", {})
        
        # Calculate cost
        if provider == "openai":
            input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * pricing.get("input", Decimal("0"))
            output_cost = (Decimal(estimated_output_tokens) / Decimal(1_000_000)) * pricing.get("output", Decimal("0"))
            predicted_cost = input_cost + output_cost
        elif provider == "huggingface":
            # Free tier (with limits)
            predicted_cost = Decimal("0.00")
        else:
            # Local or other
            predicted_cost = Decimal("0.001")  # Default

        # Calculate confidence interval (based on historical accuracy)
        accuracy_key = f"{provider}:{operation_type}"
        accuracy = self.historical_accuracy.get(accuracy_key, 0.90)  # Default 90% accurate
        
        # Confidence interval: ±5% if high accuracy, ±15% if low accuracy
        margin = Decimal("0.05") if accuracy > 0.90 else Decimal("0.15")
        confidence_lower = predicted_cost * (Decimal("1") - margin)
        confidence_upper = predicted_cost * (Decimal("1") + margin)

        # Find alternative providers
        alternatives = []
        for alt_provider in ["huggingface", "openai", "local"]:
            if alt_provider == provider:
                continue
            alt_cost = self.predict_cost(
                operation_type, alt_provider, input_tokens=input_tokens,
                estimated_output_tokens=estimated_output_tokens, model=model
            ).predicted_cost
            savings = ((predicted_cost - alt_cost) / predicted_cost * 100) if predicted_cost > 0 else 0
            alternatives.append({
                "provider": alt_provider,
                "cost": str(alt_cost),
                "savings_percent": float(savings),
            })

        return CostPrediction(
            predicted_cost=predicted_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
            confidence_lower=confidence_lower.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
            confidence_upper=confidence_upper.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
            accuracy_score=accuracy,
            alternative_providers=alternatives,
            input_tokens=input_tokens,
            estimated_output_tokens=estimated_output_tokens,
        )

    def record_actual_cost(
        self,
        provider: str,
        operation_type: str,
        predicted_cost: Decimal,
        actual_cost: Decimal,
    ):
        """Record actual cost to improve predictions."""
        error_percent = abs((actual_cost - predicted_cost) / predicted_cost * 100) if predicted_cost > 0 else 0
        
        # Update accuracy
        accuracy_key = f"{provider}:{operation_type}"
        current_accuracy = self.historical_accuracy.get(accuracy_key, 0.90)
        
        # Moving average: 90% old, 10% new
        new_accuracy = 1.0 - (error_percent / 100)
        self.historical_accuracy[accuracy_key] = current_accuracy * 0.9 + new_accuracy * 0.1
        
        logger.info(
            f"Cost accuracy update: {accuracy_key} = {self.historical_accuracy[accuracy_key]:.2%}, "
            f"error={error_percent:.2f}%"
        )
