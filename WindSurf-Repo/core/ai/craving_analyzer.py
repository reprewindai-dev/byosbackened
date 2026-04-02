"""Advanced craving analysis - understands deep user cravings."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging
import math

logger = logging.getLogger(__name__)


class CravingAnalyzer:
    """Analyzes and predicts user cravings."""

    def __init__(self):
        self.craving_intensity_threshold = 0.7
        self.deep_craving_threshold = 0.85
        self.craving_decay_rate = 0.95

    def analyze_cravings(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        recent_interactions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Deep analysis of user cravings."""
        # Analyze craving patterns
        craving_patterns = self._identify_craving_patterns(recent_interactions)

        # Calculate craving intensity
        craving_intensity = self._calculate_craving_intensity(
            recent_interactions,
            craving_patterns,
        )

        # Identify specific cravings
        specific_cravings = self._identify_specific_cravings(
            recent_interactions,
            craving_patterns,
        )

        # Predict craving triggers
        craving_triggers = self._identify_craving_triggers(
            recent_interactions,
            craving_patterns,
        )

        # Calculate craving urgency
        craving_urgency = self._calculate_craving_urgency(
            craving_intensity,
            specific_cravings,
        )

        return {
            "craving_intensity": craving_intensity,
            "specific_cravings": specific_cravings,
            "craving_triggers": craving_triggers,
            "craving_urgency": craving_urgency,
            "craving_patterns": craving_patterns,
            "prediction_confidence": self._calculate_craving_confidence(
                recent_interactions,
            ),
        }

    def _identify_craving_patterns(
        self,
        recent_interactions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Identify patterns that indicate cravings."""
        patterns = {
            "rapid_viewing": False,
            "deep_engagement": False,
            "repetitive_content": False,
            "increasing_intensity": False,
            "session_length": 0,
        }

        if not recent_interactions:
            return patterns

        # Check for rapid viewing
        if len(recent_interactions) > 10:
            patterns["rapid_viewing"] = True

        # Check for deep engagement
        completion_rates = [i.get("completion_rate", 0) for i in recent_interactions]
        avg_completion = sum(completion_rates) / len(completion_rates) if completion_rates else 0
        if avg_completion > 0.7:
            patterns["deep_engagement"] = True

        # Check for repetitive content (same category/tags)
        categories = [i.get("category") for i in recent_interactions if i.get("category")]
        if len(set(categories)) < len(categories) * 0.5:  # Less than 50% diversity
            patterns["repetitive_content"] = True

        # Check for increasing intensity
        durations = [i.get("duration", 0) for i in recent_interactions if i.get("duration")]
        if len(durations) > 3:
            recent_durations = durations[-3:]
            earlier_durations = durations[:-3]
            if sum(recent_durations) > sum(earlier_durations):
                patterns["increasing_intensity"] = True

        # Calculate session length
        total_duration = sum(i.get("duration", 0) for i in recent_interactions)
        patterns["session_length"] = total_duration

        return patterns

    def _calculate_craving_intensity(
        self,
        recent_interactions: List[Dict[str, Any]],
        craving_patterns: Dict[str, Any],
    ) -> float:
        """Calculate overall craving intensity."""
        intensity = 0.0

        # Base intensity from interaction count
        interaction_count = len(recent_interactions)
        intensity += min(interaction_count / 20, 0.3)  # Max 30% from count

        # Intensity from patterns
        if craving_patterns.get("rapid_viewing"):
            intensity += 0.2
        if craving_patterns.get("deep_engagement"):
            intensity += 0.2
        if craving_patterns.get("repetitive_content"):
            intensity += 0.15
        if craving_patterns.get("increasing_intensity"):
            intensity += 0.15

        # Intensity from session length
        session_length = craving_patterns.get("session_length", 0)
        if session_length > 1800:  # > 30 minutes
            intensity += 0.2
        elif session_length > 900:  # > 15 minutes
            intensity += 0.1

        return min(intensity, 1.0)

    def _identify_specific_cravings(
        self,
        recent_interactions: List[Dict[str, Any]],
        craving_patterns: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Identify specific things user is craving."""
        cravings = []

        # Analyze category cravings
        category_counts = {}
        for interaction in recent_interactions:
            category = interaction.get("category")
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1

        # Categories with high frequency indicate craving
        total_interactions = len(recent_interactions)
        for category, count in category_counts.items():
            frequency = count / total_interactions if total_interactions > 0 else 0
            if frequency > 0.3:  # More than 30% of interactions
                intensity = min(frequency * 2, 1.0)  # Scale to 0-1
                cravings.append(
                    {
                        "type": "category",
                        "value": category,
                        "intensity": intensity,
                        "frequency": frequency,
                    }
                )

        # Analyze tag cravings
        tag_counts = {}
        for interaction in recent_interactions:
            tags = interaction.get("tags", [])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        for tag, count in tag_counts.items():
            frequency = count / total_interactions if total_interactions > 0 else 0
            if frequency > 0.2:  # More than 20% of interactions
                intensity = min(frequency * 2.5, 1.0)
                cravings.append(
                    {
                        "type": "tag",
                        "value": tag,
                        "intensity": intensity,
                        "frequency": frequency,
                    }
                )

        return cravings

    def _identify_craving_triggers(
        self,
        recent_interactions: List[Dict[str, Any]],
        craving_patterns: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Identify what triggers cravings."""
        triggers = []

        # Time-based triggers
        current_hour = datetime.utcnow().hour
        if current_hour >= 20:  # Evening
            triggers.append(
                {
                    "type": "temporal",
                    "value": "evening",
                    "strength": 0.7,
                }
            )

        # Content-based triggers
        if craving_patterns.get("repetitive_content"):
            triggers.append(
                {
                    "type": "content_pattern",
                    "value": "repetitive_viewing",
                    "strength": 0.8,
                }
            )

        # Engagement-based triggers
        if craving_patterns.get("deep_engagement"):
            triggers.append(
                {
                    "type": "engagement",
                    "value": "high_completion",
                    "strength": 0.75,
                }
            )

        return triggers

    def _calculate_craving_urgency(
        self,
        craving_intensity: float,
        specific_cravings: List[Dict[str, Any]],
    ) -> str:
        """Calculate urgency level of cravings."""
        if craving_intensity >= self.deep_craving_threshold:
            return "critical"
        elif craving_intensity >= self.craving_intensity_threshold:
            return "high"
        elif specific_cravings:
            return "medium"
        else:
            return "low"

    def _calculate_craving_confidence(
        self,
        recent_interactions: List[Dict[str, Any]],
    ) -> float:
        """Calculate confidence in craving predictions."""
        interaction_count = len(recent_interactions)

        if interaction_count > 20:
            return 0.9  # High confidence
        elif interaction_count > 10:
            return 0.7  # Medium confidence
        elif interaction_count > 5:
            return 0.5  # Low confidence
        else:
            return 0.3  # Very low confidence

    def predict_next_craving(
        self,
        current_cravings: Dict[str, Any],
        behavioral_trends: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Predict what user will crave next."""
        specific_cravings = current_cravings.get("specific_cravings", [])
        craving_intensity = current_cravings.get("craving_intensity", 0.5)

        # Predict next craving based on current trends
        next_cravings = []

        # If intensity is high, predict continuation
        if craving_intensity > self.craving_intensity_threshold:
            for craving in specific_cravings:
                # Slight decay but continuation
                next_intensity = craving["intensity"] * self.craving_decay_rate
                next_cravings.append(
                    {
                        "type": craving["type"],
                        "value": craving["value"],
                        "predicted_intensity": next_intensity,
                        "probability": 0.8,
                    }
                )

        # Predict emerging cravings from trends
        if behavioral_trends.get("emerging_categories"):
            for category in behavioral_trends["emerging_categories"]:
                next_cravings.append(
                    {
                        "type": "category",
                        "value": category,
                        "predicted_intensity": 0.6,
                        "probability": 0.5,
                    }
                )

        return {
            "next_cravings": next_cravings,
            "predicted_intensity": craving_intensity * self.craving_decay_rate,
            "prediction_horizon": "next_session",
        }
