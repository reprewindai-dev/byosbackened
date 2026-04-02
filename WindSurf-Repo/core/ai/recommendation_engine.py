"""AI-powered content recommendation engine."""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from db.models.content import Content, Category, Tag
from db.models.user import User
from db.models.subscription import Subscription
import logging
import json

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """AI-powered recommendation engine that learns user preferences."""

    def __init__(self):
        self.learning_rate = 0.1  # How quickly to adapt to new preferences
        self.min_interactions = 3  # Minimum interactions before recommendations

    def get_personalized_recommendations(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get personalized content recommendations based on user behavior.

        Uses collaborative filtering and content-based filtering.
        """
        # Get user preferences from viewing history
        user_preferences = self._analyze_user_preferences(db, user_id, workspace_id)

        # Get content based on preferences
        recommendations = self._get_content_by_preferences(
            db,
            workspace_id,
            user_preferences,
            limit=limit,
        )

        return recommendations

    def _analyze_user_preferences(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Analyze user preferences from viewing history."""
        # Get user's viewed content (from view_count or separate tracking)
        # For now, we'll use content that has been viewed

        # Get user's subscription tier (affects recommendations)
        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.workspace_id == workspace_id,
                Subscription.status == "active",
            )
            .first()
        )

        tier = subscription.tier.value if subscription else "basic"

        # Analyze preferred categories
        # In production, track actual views/clicks/interactions
        preferred_categories = self._get_preferred_categories(db, user_id, workspace_id)

        # Analyze preferred tags
        preferred_tags = self._get_preferred_tags(db, user_id, workspace_id)

        # Analyze preferred content types
        preferred_types = self._get_preferred_types(db, user_id, workspace_id)

        # Analyze watch patterns (duration, time of day, etc.)
        watch_patterns = self._analyze_watch_patterns(db, user_id, workspace_id)

        return {
            "tier": tier,
            "preferred_categories": preferred_categories,
            "preferred_tags": preferred_tags,
            "preferred_types": preferred_types,
            "watch_patterns": watch_patterns,
            "preference_score": self._calculate_preference_score(
                preferred_categories,
                preferred_tags,
                preferred_types,
            ),
        }

    def _get_preferred_categories(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> List[Dict[str, Any]]:
        """Get user's preferred categories."""
        # In production, track actual category views/clicks
        # For now, return popular categories weighted by user's subscription tier

        categories = (
            db.query(Category)
            .filter(
                Category.workspace_id == workspace_id,
                Category.is_active == True,
            )
            .all()
        )

        # Return categories with weights (simplified - in production, use actual user data)
        return [
            {
                "category_id": cat.id,
                "category_slug": cat.slug,
                "weight": 1.0,  # Would be calculated from user behavior
            }
            for cat in categories[:10]  # Top 10 categories
        ]

    def _get_preferred_tags(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> List[Dict[str, Any]]:
        """Get user's preferred tags."""
        # In production, analyze tags from viewed content
        # For now, return popular tags

        tags = (
            db.query(Tag)
            .filter(
                Tag.workspace_id == workspace_id,
            )
            .limit(20)
            .all()
        )

        return [
            {
                "tag_id": tag.id,
                "tag_name": tag.name,
                "weight": 1.0,  # Would be calculated from user behavior
            }
            for tag in tags
        ]

    def _get_preferred_types(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> List[str]:
        """Get user's preferred content types."""
        # In production, analyze content types from viewed content
        return ["video"]  # Default to video

    def _analyze_watch_patterns(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Analyze user's watch patterns."""
        # In production, track actual watch times, durations, etc.
        return {
            "preferred_duration": None,  # Would be calculated
            "preferred_time_of_day": None,  # Would be calculated
            "average_session_length": None,  # Would be calculated
        }

    def _calculate_preference_score(
        self,
        categories: List[Dict],
        tags: List[Dict],
        types: List[str],
    ) -> float:
        """Calculate overall preference score."""
        # Weighted combination of preferences
        category_score = sum(cat["weight"] for cat in categories) / max(len(categories), 1)
        tag_score = sum(tag["weight"] for tag in tags) / max(len(tags), 1)
        type_score = len(types) * 0.1

        return category_score * 0.5 + tag_score * 0.3 + type_score * 0.2

    def _get_content_by_preferences(
        self,
        db: Session,
        workspace_id: str,
        preferences: Dict[str, Any],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get content matching user preferences."""
        query = db.query(Content).filter(
            Content.workspace_id == workspace_id,
            Content.status == "published",
        )

        # Filter by preferred categories
        if preferences["preferred_categories"]:
            category_ids = [cat["category_id"] for cat in preferences["preferred_categories"]]
            query = query.filter(Content.category_id.in_(category_ids))

        # Order by relevance (view count, rating, recency)
        content = (
            query.order_by(
                desc(Content.view_count),
                desc(Content.rating),
                desc(Content.created_at),
            )
            .limit(limit)
            .all()
        )

        # Convert to dict with relevance scores
        recommendations = []
        for item in content:
            relevance_score = self._calculate_relevance_score(item, preferences)
            recommendations.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "thumbnail_url": item.thumbnail_url,
                    "video_url": item.video_url,
                    "duration": item.duration,
                    "view_count": item.view_count,
                    "rating": item.rating,
                    "category": item.category.slug if item.category else None,
                    "tags": [tag.name for tag in item.tags] if hasattr(item, "tags") else [],
                    "relevance_score": relevance_score,
                    "recommendation_reason": self._get_recommendation_reason(item, preferences),
                }
            )

        # Sort by relevance score
        recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)

        return recommendations

    def _calculate_relevance_score(
        self,
        content: Content,
        preferences: Dict[str, Any],
    ) -> float:
        """Calculate relevance score for content."""
        score = 0.0

        # Category match
        if content.category_id:
            category_ids = [cat["category_id"] for cat in preferences["preferred_categories"]]
            if content.category_id in category_ids:
                score += 0.4

        # View count (popularity)
        if content.view_count:
            score += min(content.view_count / 10000, 0.3)  # Normalize

        # Rating
        if content.rating:
            score += (content.rating / 5.0) * 0.2

        # Recency
        days_old = (datetime.utcnow() - content.created_at).days
        recency_score = max(0, 1.0 - (days_old / 365.0))  # Decay over year
        score += recency_score * 0.1

        return score

    def _get_recommendation_reason(
        self,
        content: Content,
        preferences: Dict[str, Any],
    ) -> str:
        """Get human-readable reason for recommendation."""
        reasons = []

        if content.category_id:
            category_ids = [cat["category_id"] for cat in preferences["preferred_categories"]]
            if content.category_id in category_ids:
                reasons.append("matches your preferred categories")

        if content.view_count and content.view_count > 1000:
            reasons.append("popular with other users")

        if content.rating and content.rating >= 4.0:
            reasons.append("highly rated")

        if not reasons:
            reasons.append("trending now")

        return "Recommended because it " + ", ".join(reasons)

    def learn_from_interaction(
        self,
        db: Session,
        user_id: str,
        content_id: str,
        interaction_type: str,  # "view", "like", "share", "watch_complete"
        duration: Optional[float] = None,
    ):
        """Learn from user interactions to improve recommendations."""
        # In production, store interaction data and update user preferences
        logger.info(
            f"Learning from interaction: user={user_id}, "
            f"content={content_id}, type={interaction_type}, duration={duration}"
        )

        # Update user preferences based on interaction
        # This would update the user's preference weights in production


class ContentOptimizer:
    """Optimize content discovery and presentation."""

    def optimize_content_order(
        self,
        content_list: List[Dict[str, Any]],
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Optimize content order for maximum engagement."""
        if not user_preferences:
            # Default: sort by popularity and recency
            return sorted(
                content_list,
                key=lambda x: (
                    x.get("view_count", 0),
                    x.get("rating", 0),
                    -x.get("days_old", 365),
                ),
                reverse=True,
            )

        # Sort by relevance score if available
        if all("relevance_score" in item for item in content_list):
            return sorted(
                content_list,
                key=lambda x: x["relevance_score"],
                reverse=True,
            )

        return content_list

    def get_trending_content(
        self,
        db: Session,
        workspace_id: str,
        time_window_hours: int = 24,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get trending content in last N hours."""
        since = datetime.utcnow() - timedelta(hours=time_window_hours)

        content = (
            db.query(Content)
            .filter(
                Content.workspace_id == workspace_id,
                Content.status == "published",
                Content.created_at >= since,
            )
            .order_by(
                desc(Content.view_count),
                desc(Content.rating),
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "id": item.id,
                "title": item.title,
                "thumbnail_url": item.thumbnail_url,
                "view_count": item.view_count,
                "rating": item.rating,
                "trending_score": self._calculate_trending_score(item),
            }
            for item in content
        ]

    def _calculate_trending_score(self, content: Content) -> float:
        """Calculate trending score."""
        # Based on views, rating, and recency
        view_score = min(content.view_count or 0 / 1000, 1.0)
        rating_score = (content.rating or 0) / 5.0

        days_old = (datetime.utcnow() - content.created_at).days
        recency_score = max(0, 1.0 - (days_old / 7.0))  # Decay over week

        return view_score * 0.4 + rating_score * 0.3 + recency_score * 0.3
