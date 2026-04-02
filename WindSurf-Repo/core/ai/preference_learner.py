"""Advanced preference learning system."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models.content import Content
from db.models.user import User
import logging
import json

logger = logging.getLogger(__name__)


class PreferenceLearner:
    """Learns and adapts user preferences continuously."""

    def __init__(self):
        self.learning_rate = 0.15
        self.decay_rate = 0.95  # Preferences decay over time
        self.min_interactions = 3

    def learn_from_session(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        session_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Learn from entire user session."""
        interactions = session_data.get("interactions", [])
        session_duration = session_data.get("duration", 0)

        learned_preferences = {
            "categories": {},
            "tags": {},
            "content_types": {},
            "viewing_patterns": {},
            "session_insights": {},
        }

        # Learn from each interaction
        for interaction in interactions:
            content_id = interaction.get("content_id")
            interaction_type = interaction.get("type")
            duration = interaction.get("duration")

            if content_id:
                content = (
                    db.query(Content)
                    .filter(
                        Content.id == content_id,
                    )
                    .first()
                )

                if content:
                    # Learn category preference
                    if content.category_id:
                        weight = self._calculate_weight(interaction_type, duration)
                        learned_preferences["categories"][content.category_id] = (
                            learned_preferences["categories"].get(content.category_id, 0) + weight
                        )

                    # Learn tag preferences
                    if content.tags_json:
                        for tag in content.tags_json:
                            weight = self._calculate_weight(interaction_type, duration)
                            learned_preferences["tags"][tag] = (
                                learned_preferences["tags"].get(tag, 0) + weight
                            )

                    # Learn content type preference
                    weight = self._calculate_weight(interaction_type, duration)
                    learned_preferences["content_types"][content.content_type.value] = (
                        learned_preferences["content_types"].get(content.content_type.value, 0)
                        + weight
                    )

        # Analyze session patterns
        learned_preferences["session_insights"] = {
            "average_watch_time": self._calculate_avg_watch_time(interactions),
            "preferred_duration": self._calculate_preferred_duration(interactions),
            "engagement_level": self._calculate_engagement_level(
                session_duration, len(interactions)
            ),
            "category_diversity": len(learned_preferences["categories"]),
            "tag_diversity": len(learned_preferences["tags"]),
        }

        return learned_preferences

    def _calculate_weight(
        self,
        interaction_type: str,
        duration: Optional[float],
    ) -> float:
        """Calculate learning weight for interaction."""
        weights = {
            "view": 0.1,
            "like": 0.2,
            "share": 0.25,
            "favorite": 0.3,
            "watch_complete": 0.4,
            "watch_50": 0.25,
            "watch_75": 0.35,
        }

        base_weight = weights.get(interaction_type, 0.1)

        # Boost for longer duration
        if duration:
            duration_boost = min(duration / 300, 0.2)  # Max 20% boost
            base_weight += duration_boost

        return min(base_weight, 1.0)

    def _calculate_avg_watch_time(self, interactions: List[Dict]) -> float:
        """Calculate average watch time."""
        durations = [i.get("duration", 0) for i in interactions if i.get("duration")]
        return sum(durations) / len(durations) if durations else 0

    def _calculate_preferred_duration(self, interactions: List[Dict]) -> Optional[int]:
        """Calculate preferred content duration."""
        durations = [i.get("duration", 0) for i in interactions if i.get("duration")]
        if not durations:
            return None

        # Return median duration
        sorted_durations = sorted(durations)
        mid = len(sorted_durations) // 2
        return int(sorted_durations[mid])

    def _calculate_engagement_level(
        self,
        session_duration: float,
        interaction_count: int,
    ) -> str:
        """Calculate engagement level."""
        if session_duration > 3600 and interaction_count > 10:
            return "high"
        elif session_duration > 1800 or interaction_count > 5:
            return "medium"
        else:
            return "low"

    def update_preferences(
        self,
        current_preferences: Dict[str, Any],
        new_learned: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update preferences with new learning."""
        updated = current_preferences.copy()

        # Update category preferences
        current_categories = updated.get("categories", {})
        new_categories = new_learned.get("categories", {})

        for category_id, weight in new_categories.items():
            current_weight = current_categories.get(category_id, 0.5)
            # Exponential moving average
            new_weight = current_weight * (1 - self.learning_rate) + weight * self.learning_rate
            current_categories[category_id] = min(new_weight, 1.0)

        updated["categories"] = current_categories

        # Update tag preferences similarly
        current_tags = updated.get("tags", {})
        new_tags = new_learned.get("tags", {})

        for tag, weight in new_tags.items():
            current_weight = current_tags.get(tag, 0.5)
            new_weight = current_weight * (1 - self.learning_rate) + weight * self.learning_rate
            current_tags[tag] = min(new_weight, 1.0)

        updated["tags"] = current_tags

        # Update content type preferences
        current_types = updated.get("content_types", {})
        new_types = new_learned.get("content_types", {})

        for content_type, weight in new_types.items():
            current_weight = current_types.get(content_type, 0.5)
            new_weight = current_weight * (1 - self.learning_rate) + weight * self.learning_rate
            current_types[content_type] = min(new_weight, 1.0)

        updated["content_types"] = current_types

        # Update session insights
        updated["session_insights"] = new_learned.get("session_insights", {})

        return updated

    def apply_preference_decay(
        self,
        preferences: Dict[str, Any],
        days_since_update: int,
    ) -> Dict[str, Any]:
        """Apply decay to preferences over time."""
        decay_factor = self.decay_rate**days_since_update

        # Decay category weights
        categories = preferences.get("categories", {})
        for category_id in categories:
            categories[category_id] *= decay_factor

        # Decay tag weights
        tags = preferences.get("tags", {})
        for tag in tags:
            tags[tag] *= decay_factor

        return preferences
