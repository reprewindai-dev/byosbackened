"""Advanced content flow engine for seamless content discovery."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from db.models.content import Content
import logging

logger = logging.getLogger(__name__)


class ContentFlowEngine:
    """Creates seamless content flow for continuous discovery."""

    def __init__(self):
        self.flow_optimization = True
        self.seamless_transitions = True

    def create_seamless_flow(
        self,
        db: Session,
        workspace_id: str,
        current_content_id: Optional[str],
        user_preferences: Dict[str, Any],
        limit: int = 30,
    ) -> Dict[str, Any]:
        """Create seamless content flow."""
        if current_content_id:
            # Build chain from current content
            current_content = (
                db.query(Content)
                .filter(
                    Content.id == current_content_id,
                )
                .first()
            )

            if current_content:
                next_content = self._get_next_in_flow(
                    db,
                    workspace_id,
                    current_content,
                    user_preferences,
                    limit,
                )

                return {
                    "current": {
                        "id": current_content.id,
                        "title": current_content.title,
                    },
                    "next_content": next_content,
                    "flow_type": "seamless_chain",
                    "continuous": True,
                }

        # Build discovery feed
        discovery_feed = self._build_discovery_feed(
            db,
            workspace_id,
            user_preferences,
            limit,
        )

        return {
            "feed": discovery_feed,
            "flow_type": "discovery_feed",
            "continuous": True,
        }

    def _get_next_in_flow(
        self,
        db: Session,
        workspace_id: str,
        current_content: Content,
        user_preferences: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Get next content in seamless flow."""
        # Find similar content for smooth transition
        query = db.query(Content).filter(
            Content.workspace_id == workspace_id,
            Content.status == "published",
            Content.id != current_content.id,
        )

        # Match category for continuity
        if current_content.category_id:
            query = query.filter(Content.category_id == current_content.category_id)

        # Get content
        content = (
            query.order_by(
                desc(Content.view_count),
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
                "video_url": item.video_url,
                "flow_position": i,
                "seamless_transition": True,
            }
            for i, item in enumerate(content)
        ]

    def _build_discovery_feed(
        self,
        db: Session,
        workspace_id: str,
        user_preferences: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Build discovery feed for continuous exploration."""
        # Mix of content types for variety
        feed = []

        # Get diverse content
        content = (
            db.query(Content)
            .filter(
                Content.workspace_id == workspace_id,
                Content.status == "published",
            )
            .order_by(
                desc(Content.view_count),
                desc(Content.created_at),
            )
            .limit(limit * 2)
            .all()
        )

        # Add variety
        for item in content[:limit]:
            feed.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "thumbnail_url": item.thumbnail_url,
                    "video_url": item.video_url,
                    "discovery_score": 0.8,
                }
            )

        return feed
