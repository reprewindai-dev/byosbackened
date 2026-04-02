"""Seked Foundation - Perfect proportion principles for structural integrity."""
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import math
from core.signal_coherence.signal_field import signal_field, InteractionLog


class SekedProportion(BaseModel):
    """Represents a Seked proportion (slope ratio) for perfect proportionality."""
    name: str = Field(..., description="Proportion identifier")
    intent_slope: float = Field(..., description="Slope of intent (rise/run)")
    action_slope: float = Field(..., description="Slope of action (rise/run)")
    proportion_ratio: float = Field(..., description="Seked ratio (intent:action)")
    is_optimal: bool = Field(True, description="Whether proportion is optimal")
    deviation_score: float = Field(0.0, description="How much it deviates from perfect proportion")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_calculated: datetime = Field(default_factory=datetime.utcnow)


class SekedFoundation:
    """Seked Foundation providing perfect proportion principles for structural integrity."""

    # Ancient Egyptian Seked ratios for reference
    CLASSIC_SEKED_RATIOS = {
        "perfect_pyramid": 5.25,  # Great Pyramid slope
        "golden_ratio": (1 + math.sqrt(5)) / 2,  # ~1.618
        "silver_ratio": 1 + math.sqrt(2),  # ~2.414
        "bronze_ratio": (3 + math.sqrt(13)) / 2,  # ~3.303
    }

    def __init__(self):
        self.proportions: Dict[str, SekedProportion] = {}
        self.ideal_proportions = {
            "intent_action": 1.0,  # Perfect 1:1 proportionality
            "planning_execution": 1.618,  # Golden ratio for planning
            "learning_adaptation": 2.414,  # Silver ratio for learning
            "stability_change": 0.618,  # Inverse golden ratio for stability
        }

    def calculate_seked_proportion(
        self,
        intent_magnitude: float,
        action_magnitude: float,
        context: str = "general"
    ) -> SekedProportion:
        """Calculate Seked proportion between intent and action."""

        # Avoid division by zero
        if action_magnitude == 0:
            proportion_ratio = float('inf') if intent_magnitude > 0 else 1.0
        else:
            proportion_ratio = intent_magnitude / action_magnitude

        # Calculate deviation from ideal proportion
        ideal_ratio = self.ideal_proportions.get(context, 1.0)
        deviation_score = abs(proportion_ratio - ideal_ratio) / ideal_ratio

        # Determine if optimal (within 10% of ideal)
        is_optimal = deviation_score <= 0.1

        proportion = SekedProportion(
            name=f"seked_{context}_{datetime.utcnow().isoformat()}",
            intent_slope=intent_magnitude,
            action_slope=action_magnitude,
            proportion_ratio=proportion_ratio,
            is_optimal=is_optimal,
            deviation_score=deviation_score
        )

        # Store proportion
        self.proportions[proportion.name] = proportion
        signal_field.seked_proportions[proportion.name] = proportion_ratio

        return proportion

    def validate_structural_integrity(self) -> Dict[str, Any]:
        """Validate structural integrity using Seked principles."""

        integrity_metrics = {
            "overall_integrity": signal_field.get_structural_integrity(),
            "proportion_balance": self._calculate_proportion_balance(),
            "slope_stability": self._calculate_slope_stability(),
            "temporal_alignment": self._calculate_temporal_alignment(),
            "weak_points": self._identify_weak_points(),
            "recommendations": self._generate_recommendations()
        }

        return integrity_metrics

    def _calculate_proportion_balance(self) -> float:
        """Calculate how well proportions are balanced across the system."""

        if not self.proportions:
            return 1.0  # Perfect balance if no proportions measured

        ratios = [p.proportion_ratio for p in self.proportions.values()]
        avg_ratio = sum(ratios) / len(ratios)

        # Calculate variance from average (lower is better balance)
        variance = sum((r - avg_ratio) ** 2 for r in ratios) / len(ratios)
        balance_score = 1.0 / (1.0 + variance)  # Convert to 0-1 score

        return balance_score

    def _calculate_slope_stability(self) -> float:
        """Calculate slope stability over time."""

        if len(signal_field.interaction_history) < 2:
            return 1.0

        # Analyze proportion trends over recent interactions
        recent_interactions = signal_field.interaction_history[-20:]
        slopes = [i.seked_proportion for i in recent_interactions if i.seked_proportion > 0]

        if len(slopes) < 2:
            return 1.0

        # Calculate slope changes (stability = low variance in changes)
        changes = []
        for i in range(1, len(slopes)):
            change = abs(slopes[i] - slopes[i-1]) / slopes[i-1] if slopes[i-1] != 0 else 0
            changes.append(change)

        avg_change = sum(changes) / len(changes)
        stability_score = 1.0 / (1.0 + avg_change)  # Lower change = higher stability

        return stability_score

    def _calculate_temporal_alignment(self) -> float:
        """Calculate temporal alignment of intent and action."""

        if not signal_field.intent_vectors:
            return 1.0

        # Check alignment between intent vectors and recent actions
        recent_actions = signal_field.interaction_history[-10:]
        active_intents = [v for v in signal_field.intent_vectors.values()
                         if (datetime.utcnow() - v.created_at).days < 7]

        if not active_intents or not recent_actions:
            return 1.0

        alignment_scores = []
        for intent in active_intents:
            intent_direction = intent.direction.lower()
            matching_actions = [a for a in recent_actions
                              if intent_direction in a.action_taken.lower()]
            alignment_score = len(matching_actions) / len(recent_actions) if recent_actions else 0
            alignment_scores.append(alignment_score)

        return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 1.0

    def _identify_weak_points(self) -> List[Dict[str, Any]]:
        """Identify weak points in structural integrity."""

        weak_points = []

        # Check for disproportionate proportions
        for name, proportion in self.proportions.items():
            if not proportion.is_optimal and proportion.deviation_score > 0.3:
                weak_points.append({
                    "type": "disproportionate_seked",
                    "component": name,
                    "severity": proportion.deviation_score,
                    "description": f"Seked proportion deviates by {proportion.deviation_score:.1%}"
                })

        # Check for fracture points affecting proportions
        for fracture_id, fracture in signal_field.fracture_map.items():
            if fracture.fracture_score > 0.5:
                weak_points.append({
                    "type": "high_fracture_impact",
                    "component": fracture_id,
                    "severity": fracture.fracture_score,
                    "description": f"Fracture point affecting structural integrity"
                })

        # Check for trust degradation
        for source_id, trust in signal_field.trust_weights.items():
            if trust.reliability_score < 0.3:
                weak_points.append({
                    "type": "trust_degradation",
                    "component": source_id,
                    "severity": 1.0 - trust.reliability_score,
                    "description": f"Low trust source affecting proportion calculations"
                })

        return weak_points

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for maintaining Seked integrity."""

        recommendations = []

        # Proportion balance recommendations
        balance_score = self._calculate_proportion_balance()
        if balance_score < 0.7:
            recommendations.append("Rebalance intent-to-action proportions to improve system harmony")

        # Slope stability recommendations
        stability_score = self._calculate_slope_stability()
        if stability_score < 0.8:
            recommendations.append("Stabilize operational slopes to reduce temporal variance")

        # Temporal alignment recommendations
        alignment_score = self._calculate_temporal_alignment()
        if alignment_score < 0.6:
            recommendations.append("Improve alignment between intent vectors and actual actions")

        # Reference star recommendations
        star_count = len(signal_field.reference_stars)
        if star_count < 3:
            recommendations.append("Establish more reference stars for better navigational stability")

        # Trust network recommendations
        low_trust_sources = [s for s in signal_field.trust_weights.values() if s.reliability_score < 0.5]
        if len(low_trust_sources) > len(signal_field.trust_weights) * 0.3:
            recommendations.append("Rebuild trust network - too many low-reliability sources")

        return recommendations

    def optimize_proportions(self) -> Dict[str, Any]:
        """Optimize system proportions for perfect Seked alignment."""

        optimization_results = {
            "current_state": self.validate_structural_integrity(),
            "optimizations_applied": [],
            "expected_improvements": []
        }

        # Apply golden ratio optimization to intent vectors
        for vector_id, vector in signal_field.intent_vectors.items():
            current_ratio = vector.magnitude
            optimal_ratio = self.ideal_proportions.get("intent_action", 1.0)

            if abs(current_ratio - optimal_ratio) > 0.1:
                # Gradually adjust toward optimal
                adjustment = (optimal_ratio - current_ratio) * 0.1
                vector.magnitude += adjustment

                optimization_results["optimizations_applied"].append(
                    f"Adjusted intent vector {vector_id} magnitude by {adjustment:.3f}"
                )

        # Clean up old proportions
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        old_proportions = [
            name for name, prop in self.proportions.items()
            if prop.created_at < cutoff_date
        ]

        for old_prop in old_proportions:
            del self.proportions[old_prop]
            if old_prop in signal_field.seked_proportions:
                del signal_field.seked_proportions[old_prop]

        if old_proportions:
            optimization_results["optimizations_applied"].append(
                f"Cleaned up {len(old_proportions)} old proportions"
            )

        optimization_results["expected_improvements"] = [
            "Improved structural integrity",
            "Better intent-to-action proportionality",
            "Enhanced temporal stability"
        ]

        return optimization_results

    def get_classic_seked_ratio(self, name: str) -> float:
        """Get a classic Seked ratio by name."""
        return self.CLASSIC_SEKED_RATIOS.get(name, 1.0)


# Global Seked foundation instance
seked_foundation = SekedFoundation()
