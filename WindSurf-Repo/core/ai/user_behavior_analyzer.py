"""Analyze user behavior patterns for personalization."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from db.models.content import Content
from db.models.user import User
import logging

logger = logging.getLogger(__name__)


class UserBehaviorAnalyzer:
    """Analyze user behavior to improve recommendations."""

    def analyze_user_session(
        self,
        db: Session,
        user_id: str,
        session_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze user session data."""
        insights = {
            "session_duration": session_data.get("duration", 0),
            "content_viewed": session_data.get("content_count", 0),
            "categories_explored": session_data.get("categories", []),
            "search_queries": session_data.get("searches", []),
            "interaction_pattern": self._analyze_interaction_pattern(session_data),
            "engagement_level": self._calculate_engagement_level(session_data),
        }

        return insights

    def _analyze_interaction_pattern(
        self,
        session_data: Dict[str, Any],
    ) -> str:
        """Analyze user interaction pattern."""
        content_count = session_data.get("content_count", 0)
        duration = session_data.get("duration", 0)

        if content_count == 0:
            return "explorer"  # Browsing, not viewing

        avg_time_per_content = duration / content_count if content_count > 0 else 0

        if avg_time_per_content > 300:  # > 5 minutes per content
            return "deep_viewer"  # Watches full content
        elif avg_time_per_content > 60:  # > 1 minute per content
            return "moderate_viewer"
        else:
            return "quick_browser"  # Quick browsing

    def _calculate_engagement_level(
        self,
        session_data: Dict[str, Any],
    ) -> str:
        """Calculate user engagement level."""
        duration = session_data.get("duration", 0)
        content_count = session_data.get("content_count", 0)

        if duration > 3600 and content_count > 10:  # > 1 hour, > 10 items
            return "high"
        elif duration > 1800 or content_count > 5:  # > 30 min or > 5 items
            return "medium"
        else:
            return "low"

    def get_user_preferences_update(
        self,
        current_preferences: Dict[str, Any],
        new_interactions: List[Dict[str, Any]],
        learning_rate: float = 0.1,
    ) -> Dict[str, Any]:
        """Update user preferences based on new interactions."""
        updated_preferences = current_preferences.copy()

        # Update category preferences
        category_weights = updated_preferences.get("preferred_categories", {})
        for interaction in new_interactions:
            category_id = interaction.get("category_id")
            if category_id:
                current_weight = category_weights.get(category_id, 0.5)
                # Increase weight based on interaction
                interaction_weight = {
                    "view": 0.1,
                    "like": 0.2,
                    "watch_complete": 0.3,
                    "share": 0.15,
                }.get(interaction.get("type", "view"), 0.1)

                new_weight = current_weight + (interaction_weight * learning_rate)
                category_weights[category_id] = min(new_weight, 1.0)

        updated_preferences["preferred_categories"] = category_weights

        # Update tag preferences similarly
        tag_weights = updated_preferences.get("preferred_tags", {})
        for interaction in new_interactions:
            tags = interaction.get("tags", [])
            for tag in tags:
                current_weight = tag_weights.get(tag, 0.5)
                new_weight = current_weight + (0.1 * learning_rate)
                tag_weights[tag] = min(new_weight, 1.0)

        updated_preferences["preferred_tags"] = tag_weights

        return updated_preferences

    def predict_next_content(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        current_content_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Predict what content user might want next."""
        # Get similar content to what user is currently viewing
        if current_content_id:
            current_content = (
                db.query(Content)
                .filter(
                    Content.id == current_content_id,
                )
                .first()
            )

            if current_content:
                # Find similar content (same category, similar tags)
                similar = (
                    db.query(Content)
                    .filter(
                        Content.workspace_id == workspace_id,
                        Content.status == "published",
                        Content.id != current_content_id,
                        Content.category_id == current_content.category_id,
                    )
                    .order_by(
                        desc(Content.view_count),
                        desc(Content.rating),
                    )
                    .limit(10)
                    .all()
                )

                return [
                    {
                        "id": item.id,
                        "title": item.title,
                        "thumbnail_url": item.thumbnail_url,
                        "similarity_reason": f"Similar to '{current_content.title}'",
                    }
                    for item in similar
                ]

        # Default: return trending content
        trending = (
            db.query(Content)
            .filter(
                Content.workspace_id == workspace_id,
                Content.status == "published",
            )
            .order_by(
                desc(Content.view_count),
                desc(Content.created_at),
            )
            .limit(10)
            .all()
        )

        return [
            {
                "id": item.id,
                "title": item.title,
                "thumbnail_url": item.thumbnail_url,
                "similarity_reason": "Trending now",
            }
            for item in trending
        ]


class ContentDiscoveryOptimizer:
    """Optimize content discovery for better user experience."""

    def optimize_search_results(
        self,
        search_results: List[Dict[str, Any]],
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Optimize search results order."""
        if not user_preferences:
            return search_results

        # Re-rank based on user preferences
        for result in search_results:
            relevance = self._calculate_search_relevance(result, user_preferences)
            result["search_relevance"] = relevance

        # Sort by relevance
        return sorted(search_results, key=lambda x: x.get("search_relevance", 0), reverse=True)

    def _calculate_search_relevance(
        self,
        result: Dict[str, Any],
        user_preferences: Dict[str, Any],
    ) -> float:
        """Calculate relevance score for search result."""
        score = 0.0

        # Category match
        category_id = result.get("category_id")
        if category_id:
            preferred_categories = user_preferences.get("preferred_categories", {})
            if category_id in preferred_categories:
                score += preferred_categories[category_id] * 0.5

        # Tag matches
        tags = result.get("tags", [])
        preferred_tags = user_preferences.get("preferred_tags", {})
        tag_matches = sum(preferred_tags.get(tag, 0) for tag in tags)
        score += min(tag_matches / max(len(tags), 1), 0.3)

        # Popularity
        view_count = result.get("view_count", 0)
        score += min(view_count / 10000, 0.2)

        return score

    def get_discovery_feed(
        self,
        db: Session,
        workspace_id: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get optimized discovery feed."""
        # Mix of personalized, trending, and new content
        personalized_limit = int(limit * 0.5)
        trending_limit = int(limit * 0.3)
        new_limit = limit - personalized_limit - trending_limit

        feed = []

        # Personalized content
        if user_preferences:
            personalized = self._get_personalized_content(
                db,
                workspace_id,
                user_preferences,
                limit=personalized_limit,
            )
            feed.extend(personalized)

        # Trending content
        trending = self._get_trending_content(db, workspace_id, limit=trending_limit)
        feed.extend(trending)

        # New content
        new_content = self._get_new_content(db, workspace_id, limit=new_limit)
        feed.extend(new_content)

        # Shuffle and return
        import random

        random.shuffle(feed)
        return feed[:limit]

    def _get_personalized_content(
        self,
        db: Session,
        workspace_id: str,
        user_preferences: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Get personalized content."""
        # Similar to recommendation engine
        from core.ai.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        return engine.get_personalized_recommendations(
            db,
            user_id="",  # Would use actual user_id
            workspace_id=workspace_id,
            limit=limit,
        )

    def _get_trending_content(
        self,
        db: Session,
        workspace_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Get trending content."""
        content = (
            db.query(Content)
            .filter(
                Content.workspace_id == workspace_id,
                Content.status == "published",
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
                "feed_type": "trending",
            }
            for item in content
        ]

    def _get_new_content(
        self,
        db: Session,
        workspace_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Get new content."""
        content = (
            db.query(Content)
            .filter(
                Content.workspace_id == workspace_id,
                Content.status == "published",
            )
            .order_by(
                desc(Content.created_at),
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "id": item.id,
                "title": item.title,
                "thumbnail_url": item.thumbnail_url,
                "feed_type": "new",
            }
            for item in content
        ]
