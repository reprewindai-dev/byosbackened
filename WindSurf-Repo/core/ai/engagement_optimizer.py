"""Advanced engagement optimization for continuous content discovery."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models.content import Content, Category
import logging
import math

logger = logging.getLogger(__name__)


class EngagementOptimizer:
    """Optimizes content flow for continuous engagement."""

    def __init__(self):
        self.continuous_flow_enabled = True
        self.seamless_transition = True
        self.content_chain_optimization = True

    def create_continuous_content_flow(
        self,
        db: Session,
        workspace_id: str,
        user_preferences: Dict[str, Any],
        current_content_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Create seamless content flow for continuous discovery.

        Optimizes content order for smooth transitions and continuous engagement.
        """
        # Get initial content set
        if current_content_id:
            # Start from current content
            current_content = (
                db.query(Content)
                .filter(
                    Content.id == current_content_id,
                )
                .first()
            )

            if current_content:
                # Build chain starting from current
                content_chain = self._build_content_chain(
                    db,
                    workspace_id,
                    current_content,
                    user_preferences,
                    limit,
                )
                return content_chain

        # Build optimized feed
        optimized_feed = self._build_optimized_feed(
            db,
            workspace_id,
            user_preferences,
            limit,
        )

        return optimized_feed

    def _build_content_chain(
        self,
        db: Session,
        workspace_id: str,
        start_content: Content,
        user_preferences: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Build seamless content chain from starting point."""
        chain = []

        # Add starting content
        chain.append(
            {
                "id": start_content.id,
                "title": start_content.title,
                "thumbnail_url": start_content.thumbnail_url,
                "video_url": start_content.video_url,
                "chain_position": 0,
                "transition_score": 1.0,  # Perfect transition from start
            }
        )

        # Find similar content for seamless transitions
        similar_content = self._find_similar_content(
            db,
            workspace_id,
            start_content,
            user_preferences,
            limit - 1,
        )

        # Build chain with smooth transitions
        for i, content in enumerate(similar_content):
            transition_score = self._calculate_transition_score(
                chain[-1] if chain else None,
                content,
                user_preferences,
            )

            chain.append(
                {
                    "id": content.id,
                    "title": content.title,
                    "thumbnail_url": content.thumbnail_url,
                    "video_url": content.video_url,
                    "chain_position": i + 1,
                    "transition_score": transition_score,
                    "seamless_flow": transition_score > 0.7,
                }
            )

        return chain

    def _find_similar_content(
        self,
        db: Session,
        workspace_id: str,
        reference_content: Content,
        user_preferences: Dict[str, Any],
        limit: int,
    ) -> List[Content]:
        """Find content similar to reference for smooth transitions."""
        query = db.query(Content).filter(
            Content.workspace_id == workspace_id,
            Content.status == "published",
            Content.id != reference_content.id,
        )

        # Match by category first
        if reference_content.category_id:
            query = query.filter(Content.category_id == reference_content.category_id)

        # Get similar content
        similar = (
            query.order_by(
                desc(Content.view_count),
                desc(Content.created_at),
            )
            .limit(limit * 2)
            .all()
        )

        # Score and sort by similarity
        scored = []
        for item in similar:
            similarity = self._calculate_similarity(reference_content, item)
            scored.append((item, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)

        return [item for item, _ in scored[:limit]]

    def _calculate_similarity(
        self,
        content1: Content,
        content2: Content,
    ) -> float:
        """Calculate similarity between two content items."""
        score = 0.0

        # Category match
        if content1.category_id == content2.category_id:
            score += 0.5

        # Tag overlap
        if content1.tags_json and content2.tags_json:
            tags1 = set(content1.tags_json)
            tags2 = set(content2.tags_json)
            overlap = len(tags1 & tags2)
            total = len(tags1 | tags2)
            if total > 0:
                score += (overlap / total) * 0.3

        # Duration similarity
        if content1.duration_seconds and content2.duration_seconds:
            duration_diff = abs(content1.duration_seconds - content2.duration_seconds)
            max_duration = max(content1.duration_seconds, content2.duration_seconds)
            if max_duration > 0:
                duration_similarity = 1.0 - (duration_diff / max_duration)
                score += duration_similarity * 0.2

        return score

    def _calculate_transition_score(
        self,
        previous_content: Optional[Dict[str, Any]],
        current_content: Content,
        user_preferences: Dict[str, Any],
    ) -> float:
        """Calculate how smooth the transition is."""
        if not previous_content:
            return 1.0

        score = 0.0

        # Category continuity
        # Would check if categories match

        # Preference match
        preferred_categories = user_preferences.get("preferred_categories", [])
        if current_content.category:
            if current_content.category.slug in preferred_categories:
                score += 0.5

        # Popularity boost
        if current_content.view_count and current_content.view_count > 1000:
            score += 0.3

        # Recency boost
        days_old = (datetime.utcnow() - current_content.created_at).days
        if days_old < 7:
            score += 0.2

        return min(score, 1.0)

    def _build_optimized_feed(
        self,
        db: Session,
        workspace_id: str,
        user_preferences: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Build optimized feed for continuous discovery."""
        # Mix of personalized, trending, and new content
        personalized_limit = int(limit * 0.5)
        trending_limit = int(limit * 0.3)
        new_limit = limit - personalized_limit - trending_limit

        feed = []

        # Personalized content
        preferred_categories = user_preferences.get("preferred_categories", [])
        if preferred_categories:
            categories = (
                db.query(Category)
                .filter(
                    Category.workspace_id == workspace_id,
                    Category.slug.in_(preferred_categories[:5]),
                )
                .all()
            )
            category_ids = [cat.id for cat in categories]

            if category_ids:
                personalized = (
                    db.query(Content)
                    .filter(
                        Content.workspace_id == workspace_id,
                        Content.status == "published",
                        Content.category_id.in_(category_ids),
                    )
                    .order_by(
                        desc(Content.view_count),
                        desc(Content.rating),
                    )
                    .limit(personalized_limit)
                    .all()
                )

                for item in personalized:
                    feed.append(
                        {
                            "id": item.id,
                            "title": item.title,
                            "thumbnail_url": item.thumbnail_url,
                            "video_url": item.video_url,
                            "feed_type": "personalized",
                            "relevance_score": 0.9,
                        }
                    )

        # Trending content
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
            .limit(trending_limit)
            .all()
        )

        for item in trending:
            feed.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "thumbnail_url": item.thumbnail_url,
                    "video_url": item.video_url,
                    "feed_type": "trending",
                    "relevance_score": 0.7,
                }
            )

        # New content
        new_content = (
            db.query(Content)
            .filter(
                Content.workspace_id == workspace_id,
                Content.status == "published",
            )
            .order_by(
                desc(Content.created_at),
            )
            .limit(new_limit)
            .all()
        )

        for item in new_content:
            feed.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "thumbnail_url": item.thumbnail_url,
                    "video_url": item.video_url,
                    "feed_type": "new",
                    "relevance_score": 0.6,
                }
            )

        # Shuffle for variety
        import random

        random.shuffle(feed)

        return feed[:limit]

    def optimize_for_continuous_discovery(
        self,
        content_list: List[Dict[str, Any]],
        user_preferences: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Optimize content order for continuous discovery."""
        # Sort by relevance and variety
        optimized = sorted(
            content_list,
            key=lambda x: (
                x.get("relevance_score", 0),
                x.get("view_count", 0),
                -x.get("days_old", 365),
            ),
            reverse=True,
        )

        return optimized
