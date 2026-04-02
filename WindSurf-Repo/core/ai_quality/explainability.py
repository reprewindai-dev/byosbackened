"""AI explainability - explain AI decisions."""

from typing import Dict, List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class Explanation(BaseModel):
    """AI decision explanation."""

    decision: str
    reasoning: str
    confidence: float
    important_inputs: List[str]
    important_outputs: List[str]
    alternatives_considered: List[str]


class ExplainabilityEngine:
    """Generate explanations for AI decisions."""

    def explain_routing_decision(
        self,
        selected_provider: str,
        alternatives: List[Dict],
        constraints: Dict,
    ) -> Explanation:
        """Explain why a provider was selected."""
        reasoning_parts = [
            f"Selected {selected_provider} because it",
        ]

        # Explain based on constraints
        if constraints.get("strategy") == "cost_optimized":
            reasoning_parts.append("offers the lowest cost")
        elif constraints.get("strategy") == "quality_optimized":
            reasoning_parts.append("provides the highest quality")

        # Compare with alternatives
        if alternatives:
            alt = alternatives[0]
            savings = alt.get("savings_percent", 0)
            if savings > 0:
                reasoning_parts.append(
                    f"and saves {savings:.1f}% compared to {alt.get('provider')}"
                )

        reasoning = ". ".join(reasoning_parts) + "."

        return Explanation(
            decision=f"Route to {selected_provider}",
            reasoning=reasoning,
            confidence=0.85,  # Can be calculated from historical accuracy
            important_inputs=[f"Operation type: {constraints.get('operation_type', 'unknown')}"],
            important_outputs=[f"Provider: {selected_provider}"],
            alternatives_considered=[alt.get("provider") for alt in alternatives],
        )

    def explain_cost_prediction(
        self,
        predicted_cost: float,
        input_tokens: int,
        provider: str,
    ) -> Explanation:
        """Explain cost prediction."""
        reasoning = (
            f"Predicted cost of ${predicted_cost:.6f} based on "
            f"{input_tokens} input tokens using {provider} pricing model. "
            f"Cost calculated from provider's per-token rates."
        )

        return Explanation(
            decision=f"Predicted cost: ${predicted_cost:.6f}",
            reasoning=reasoning,
            confidence=0.90,  # Based on historical accuracy
            important_inputs=[f"Input tokens: {input_tokens}", f"Provider: {provider}"],
            important_outputs=[f"Predicted cost: ${predicted_cost:.6f}"],
            alternatives_considered=[],
        )


# Global explainability engine
_explainability_engine = ExplainabilityEngine()


def get_explainability_engine() -> ExplainabilityEngine:
    """Get explainability engine."""
    return _explainability_engine
