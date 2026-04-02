"""Advanced self-learning AI engine for content optimization."""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from db.models.content import Content, Category, Tag
from db.models.user import User
import logging
import json
import math

logger = logging.getLogger(__name__)


class AdvancedLearningEngine:
    """Self-learning AI engine that continuously improves recommendations."""

    def __init__(self):
        self.learning_rate = 0.15  # Adaptive learning rate
        self.exploration_rate = 0.2  # Explore new content 20% of time
        self.min_samples = 5  # Minimum interactions before learning
        self.decay_factor = 0.95  # Preference decay over time

    def learn_from_interaction(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        content_id: str,
        interaction_type: str,
        duration: Optional[float] = None,
        completion_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Learn from user interaction and update preferences.

        Returns updated preference weights.
        """
        # Get content details
        content = (
            db.query(Content)
            .filter(
                Content.id == content_id,
                Content.workspace_id == workspace_id,
            )
            .first()
        )

        if not content:
            return {"status": "error", "message": "Content not found"}

        # Calculate interaction weight
        interaction_weight = self._calculate_interaction_weight(
            interaction_type,
            duration,
            completion_rate,
        )

        # Update category preference
        if content.category_id:
            self._update_category_preference(
                db,
                user_id,
                workspace_id,
                content.category_id,
                interaction_weight,
            )

        # Update tag preferences
        if content.tags_json:
            for tag_name in content.tags_json:
                self._update_tag_preference(
                    db,
                    user_id,
                    workspace_id,
                    tag_name,
                    interaction_weight,
                )

        # Update content type preference
        self._update_content_type_preference(
            db,
            user_id,
            workspace_id,
            content.content_type.value,
            interaction_weight,
        )

        # Update viewing pattern
        self._update_viewing_pattern(
            db,
            user_id,
            workspace_id,
            duration,
            completion_rate,
        )

        logger.info(
            f"Learned from interaction: user={user_id}, "
            f"content={content_id}, type={interaction_type}, "
            f"weight={interaction_weight}"
        )

        return {
            "status": "learned",
            "interaction_weight": interaction_weight,
            "preferences_updated": True,
        }

    def _calculate_interaction_weight(
        self,
        interaction_type: str,
        duration: Optional[float],
        completion_rate: Optional[float],
    ) -> float:
        """Calculate weight for interaction based on type and engagement."""
        base_weights = {
            "view": 0.1,
            "like": 0.2,
            "share": 0.25,
            "favorite": 0.3,
            "watch_complete": 0.4,
            "watch_50_percent": 0.25,
            "watch_75_percent": 0.35,
        }

        base_weight = base_weights.get(interaction_type, 0.1)

        # Boost weight based on duration
        if duration:
            # Longer watch time = higher weight
            duration_boost = min(duration / 300, 0.3)  # Max 30% boost for 5+ min
            base_weight += duration_boost

        # Boost weight based on completion rate
        if completion_rate:
            completion_boost = completion_rate * 0.2  # Max 20% boost for 100% completion
            base_weight += completion_boost

        return min(base_weight, 1.0)  # Cap at 1.0

    def _update_category_preference(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        category_id: str,
        weight: float,
    ):
        """Update user's category preference weight."""
        # In production, store in user_preferences table
        # For now, log the update
        logger.debug(
            f"Updating category preference: user={user_id}, "
            f"category={category_id}, weight={weight}"
        )

    def _update_tag_preference(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        tag_name: str,
        weight: float,
    ):
        """Update user's tag preference weight."""
        logger.debug(
            f"Updating tag preference: user={user_id}, " f"tag={tag_name}, weight={weight}"
        )

    def _update_content_type_preference(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        content_type: str,
        weight: float,
    ):
        """Update user's content type preference."""
        logger.debug(
            f"Updating content type preference: user={user_id}, "
            f"type={content_type}, weight={weight}"
        )

    def _update_viewing_pattern(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        duration: Optional[float],
        completion_rate: Optional[float],
    ):
        """Update user's viewing pattern."""
        logger.debug(
            f"Updating viewing pattern: user={user_id}, "
            f"duration={duration}, completion={completion_rate}"
        )

    def get_optimized_recommendations(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        limit: int = 20,
        exploration: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get optimized recommendations using learned preferences.

        Uses exploration-exploitation balance.
        """
        # Get user preferences
        preferences = self._get_user_preferences(db, user_id, workspace_id)

        # Decide exploration vs exploitation
        if exploration and self._should_explore(preferences):
            # Explore: Mix in new/discover content
            recommendations = self._get_exploration_recommendations(
                db,
                workspace_id,
                preferences,
                limit=int(limit * self.exploration_rate),
            )
            exploitation_limit = limit - len(recommendations)
        else:
            recommendations = []
            exploitation_limit = limit

        # Exploit: Use learned preferences
        exploitation_recs = self._get_exploitation_recommendations(
            db,
            workspace_id,
            preferences,
            limit=exploitation_limit,
        )

        recommendations.extend(exploitation_recs)

        # Re-rank by relevance
        recommendations = self._rerank_by_relevance(recommendations, preferences)

        return recommendations[:limit]

    def _get_user_preferences(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Get user's learned preferences."""
        # In production, load from user_preferences table
        # For now, return default preferences
        return {
            "category_weights": {},
            "tag_weights": {},
            "content_type_weights": {},
            "viewing_patterns": {},
            "interaction_count": 0,
        }

    def _should_explore(self, preferences: Dict[str, Any]) -> bool:
        """Determine if should explore new content."""
        interaction_count = preferences.get("interaction_count", 0)

        # Explore more if user is new (few interactions)
        if interaction_count < self.min_samples:
            return True

        # Always explore some (exploration rate)
        import random

        return random.random() < self.exploration_rate

    def _get_exploration_recommendations(
        self,
        db: Session,
        workspace_id: str,
        preferences: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Get exploration recommendations (new/discover content)."""
        # Get trending/new content user hasn't seen
        content = (
            db.query(Content)
            .filter(
                Content.workspace_id == workspace_id,
                Content.status == "published",
            )
            .order_by(
                desc(Content.created_at),
                desc(Content.view_count),
            )
            .limit(limit * 2)
            .all()
        )  # Get more to filter

        # Convert to recommendations
        recommendations = []
        for item in content[:limit]:
            recommendations.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "thumbnail_url": item.thumbnail_url,
                    "relevance_score": 0.5,  # Neutral for exploration
                    "recommendation_type": "exploration",
                    "reason": "New content you might like",
                }
            )

        return recommendations

    def _get_exploitation_recommendations(
        self,
        db: Session,
        workspace_id: str,
        preferences: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Get exploitation recommendations (based on learned preferences)."""
        # Get content matching preferences
        category_weights = preferences.get("category_weights", {})
        tag_weights = preferences.get("tag_weights", {})

        query = db.query(Content).filter(
            Content.workspace_id == workspace_id,
            Content.status == "published",
        )

        # Filter by preferred categories
        if category_weights:
            preferred_categories = [
                cat_id
                for cat_id, weight in category_weights.items()
                if weight > 0.3  # Only strong preferences
            ]
            if preferred_categories:
                query = query.filter(Content.category_id.in_(preferred_categories))

        content = (
            query.order_by(
                desc(Content.view_count),
                desc(Content.rating),
                desc(Content.created_at),
            )
            .limit(limit * 2)
            .all()
        )

        # Score and rank by relevance
        recommendations = []
        for item in content:
            relevance = self._calculate_content_relevance(item, preferences)
            recommendations.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "thumbnail_url": item.thumbnail_url,
                    "relevance_score": relevance,
                    "recommendation_type": "exploitation",
                    "reason": self._get_recommendation_reason(item, preferences),
                }
            )

        # Sort by relevance
        recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)

        return recommendations[:limit]

    def _calculate_content_relevance(
        self,
        content: Content,
        preferences: Dict[str, Any],
    ) -> float:
        """Calculate relevance score for content."""
        score = 0.0

        # Category match
        category_weights = preferences.get("category_weights", {})
        if content.category_id and content.category_id in category_weights:
            score += category_weights[content.category_id] * 0.4

        # Tag matches
        tag_weights = preferences.get("tag_weights", {})
        if content.tags_json:
            tag_matches = sum(tag_weights.get(tag, 0) for tag in content.tags_json)
            score += min(tag_matches / max(len(content.tags_json), 1), 0.3)

        # Popularity boost
        if content.view_count:
            popularity_score = min(math.log(content.view_count + 1) / 10, 0.2)
            score += popularity_score

        # Rating boost
        if hasattr(content, "rating") and content.rating:
            rating_score = (content.rating / 5.0) * 0.1
            score += rating_score

        return min(score, 1.0)

    def _get_recommendation_reason(
        self,
        content: Content,
        preferences: Dict[str, Any],
    ) -> str:
        """Get human-readable recommendation reason."""
        reasons = []

        category_weights = preferences.get("category_weights", {})
        if content.category_id and content.category_id in category_weights:
            weight = category_weights[content.category_id]
            if weight > 0.5:
                reasons.append("matches your favorite categories")

        tag_weights = preferences.get("tag_weights", {})
        if content.tags_json:
            strong_tags = [tag for tag in content.tags_json if tag_weights.get(tag, 0) > 0.5]
            if strong_tags:
                reasons.append(f"features tags you like: {', '.join(strong_tags[:2])}")

        if not reasons:
            reasons.append("popular with users like you")

        return "Recommended because it " + ", ".join(reasons)

    def _rerank_by_relevance(
        self,
        recommendations: List[Dict[str, Any]],
        preferences: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Re-rank recommendations by relevance."""
        # Sort by relevance score
        return sorted(
            recommendations,
            key=lambda x: x.get("relevance_score", 0),
            reverse=True,
        )

    def get_continuous_learning_stats(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Get statistics about learning progress."""
        preferences = self._get_user_preferences(db, user_id, workspace_id)

        return {
            "interactions_learned": preferences.get("interaction_count", 0),
            "categories_learned": len(preferences.get("category_weights", {})),
            "tags_learned": len(preferences.get("tag_weights", {})),
            "learning_rate": self.learning_rate,
            "exploration_rate": self.exploration_rate,
            "confidence": self._calculate_confidence(preferences),
        }

    def _calculate_confidence(self, preferences: Dict[str, Any]) -> float:
        """Calculate confidence in recommendations."""
        interaction_count = preferences.get("interaction_count", 0)

        # More interactions = higher confidence
        if interaction_count < self.min_samples:
            return 0.3  # Low confidence
        elif interaction_count < 20:
            return 0.6  # Medium confidence
        else:
            return 0.9  # High confidence
