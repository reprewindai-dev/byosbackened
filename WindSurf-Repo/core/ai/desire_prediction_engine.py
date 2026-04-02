"""Advanced desire prediction engine - understands what users crave."""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from db.models.content import Content, Category, Tag
from db.models.user import User
import logging
import json
import math
from collections import defaultdict

logger = logging.getLogger(__name__)


class DesirePredictionEngine:
    """Advanced AI engine that predicts user desires and cravings."""

    def __init__(self):
        self.desire_decay_rate = 0.98  # Desires decay slightly over time
        self.craving_threshold = 0.7  # Threshold for strong craving
        self.pattern_window_days = 30  # Analyze patterns over 30 days
        self.deep_learning_rate = 0.2  # Deep learning adaptation rate

    def predict_user_desires(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Predict what user desires and craves right now.

        Uses deep behavioral analysis and pattern recognition.
        """
        # Analyze deep behavioral patterns
        behavioral_profile = self._analyze_behavioral_profile(
            db,
            user_id,
            workspace_id,
        )

        # Predict current desires
        current_desires = self._predict_current_desires(
            behavioral_profile,
            context,
        )

        # Identify cravings (strong desires)
        cravings = self._identify_cravings(current_desires)

        # Predict next desires (what they'll want next)
        next_desires = self._predict_next_desires(
            behavioral_profile,
            current_desires,
        )

        # Calculate desire intensity scores
        intensity_scores = self._calculate_desire_intensity(
            current_desires,
            behavioral_profile,
        )

        return {
            "current_desires": current_desires,
            "cravings": cravings,
            "next_desires": next_desires,
            "intensity_scores": intensity_scores,
            "behavioral_profile": behavioral_profile,
            "confidence": self._calculate_prediction_confidence(behavioral_profile),
            "prediction_timestamp": datetime.utcnow().isoformat(),
        }

    def _analyze_behavioral_profile(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Deep analysis of user behavioral patterns."""
        since = datetime.utcnow() - timedelta(days=self.pattern_window_days)

        # Analyze viewing patterns
        viewing_patterns = self._analyze_viewing_patterns(
            db,
            user_id,
            workspace_id,
            since,
        )

        # Analyze temporal patterns (time of day, day of week)
        temporal_patterns = self._analyze_temporal_patterns(
            db,
            user_id,
            workspace_id,
            since,
        )

        # Analyze category evolution (how preferences change)
        category_evolution = self._analyze_category_evolution(
            db,
            user_id,
            workspace_id,
            since,
        )

        # Analyze engagement depth (how deeply they engage)
        engagement_depth = self._analyze_engagement_depth(
            db,
            user_id,
            workspace_id,
            since,
        )

        # Analyze desire patterns (what triggers strong engagement)
        desire_patterns = self._analyze_desire_patterns(
            db,
            user_id,
            workspace_id,
            since,
        )

        return {
            "viewing_patterns": viewing_patterns,
            "temporal_patterns": temporal_patterns,
            "category_evolution": category_evolution,
            "engagement_depth": engagement_depth,
            "desire_patterns": desire_patterns,
            "profile_strength": self._calculate_profile_strength(
                viewing_patterns,
                temporal_patterns,
                category_evolution,
            ),
        }

    def _analyze_viewing_patterns(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        since: datetime,
    ) -> Dict[str, Any]:
        """Analyze deep viewing patterns."""
        # In production, would query actual interaction logs
        # For now, return pattern structure

        return {
            "average_session_length": 1800,  # Would be calculated
            "peak_engagement_duration": 300,  # Would be calculated
            "browsing_vs_watching_ratio": 0.3,  # 30% browsing, 70% watching
            "completion_rate": 0.75,  # 75% completion rate
            "replay_frequency": 0.2,  # 20% of content replayed
            "deep_dive_pattern": True,  # Tends to deep dive into topics
            "exploration_pattern": False,  # Less exploration, more focused
        }

    def _analyze_temporal_patterns(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        since: datetime,
    ) -> Dict[str, Any]:
        """Analyze temporal patterns (when user is most active)."""
        return {
            "peak_hours": [20, 21, 22, 23],  # 8pm-11pm peak
            "peak_days": [5, 6],  # Friday, Saturday
            "session_frequency": "daily",  # Daily sessions
            "time_between_sessions": 24,  # 24 hours average
            "weekend_intensity": 1.5,  # 50% more intense on weekends
        }

    def _analyze_category_evolution(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        since: datetime,
    ) -> Dict[str, Any]:
        """Analyze how category preferences evolve."""
        return {
            "primary_categories": ["lesbian", "solo-female", "squirting"],
            "emerging_categories": ["pmv", "long-session"],
            "declining_categories": [],
            "category_depth": 0.8,  # Deep engagement with categories
            "category_breadth": 0.4,  # Moderate exploration
            "preference_stability": 0.7,  # Relatively stable preferences
        }

    def _analyze_engagement_depth(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        since: datetime,
    ) -> Dict[str, Any]:
        """Analyze depth of engagement."""
        return {
            "average_watch_time": 240,  # 4 minutes average
            "full_completion_rate": 0.6,  # 60% watch full content
            "interaction_rate": 0.4,  # 40% interact (like/share)
            "return_rate": 0.3,  # 30% return to same content
            "deep_engagement_score": 0.75,  # High deep engagement
        }

    def _analyze_desire_patterns(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        since: datetime,
    ) -> Dict[str, Any]:
        """Analyze what triggers strong desire/engagement."""
        return {
            "high_engagement_triggers": [
                {"type": "category", "value": "lesbian", "weight": 0.9},
                {"type": "tag", "value": "squirting", "weight": 0.85},
                {"type": "duration", "value": "long", "weight": 0.8},
            ],
            "craving_indicators": [
                "high_completion_rate",
                "replay_frequency",
                "deep_category_exploration",
            ],
            "desire_intensity_factors": {
                "recency": 0.3,  # Recent views matter
                "frequency": 0.4,  # Frequency matters more
                "depth": 0.3,  # Depth matters
            },
        }

    def _predict_current_desires(
        self,
        behavioral_profile: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Predict what user desires right now."""
        current_hour = datetime.utcnow().hour
        current_day = datetime.utcnow().weekday()

        temporal_patterns = behavioral_profile.get("temporal_patterns", {})
        viewing_patterns = behavioral_profile.get("viewing_patterns", {})
        category_evolution = behavioral_profile.get("category_evolution", {})
        desire_patterns = behavioral_profile.get("desire_patterns", {})

        # Calculate time-based desire intensity
        time_intensity = 1.0
        if current_hour in temporal_patterns.get("peak_hours", []):
            time_intensity = 1.5  # 50% boost during peak hours

        if current_day in temporal_patterns.get("peak_days", []):
            time_intensity *= temporal_patterns.get("weekend_intensity", 1.0)

        # Predict desired categories
        desired_categories = []
        primary_categories = category_evolution.get("primary_categories", [])
        emerging_categories = category_evolution.get("emerging_categories", [])

        for category in primary_categories:
            desired_categories.append(
                {
                    "category": category,
                    "intensity": 0.9 * time_intensity,
                    "reason": "Primary preference",
                }
            )

        for category in emerging_categories:
            desired_categories.append(
                {
                    "category": category,
                    "intensity": 0.7 * time_intensity,
                    "reason": "Emerging interest",
                }
            )

        # Predict desired tags
        desired_tags = []
        high_engagement_triggers = desire_patterns.get("high_engagement_triggers", [])
        for trigger in high_engagement_triggers:
            if trigger["type"] == "tag":
                desired_tags.append(
                    {
                        "tag": trigger["value"],
                        "intensity": trigger["weight"] * time_intensity,
                        "reason": "High engagement trigger",
                    }
                )

        # Predict desired content characteristics
        desired_characteristics = {
            "duration_preference": viewing_patterns.get("peak_engagement_duration", 300),
            "completion_focus": viewing_patterns.get("completion_rate", 0.75) > 0.7,
            "depth_preference": viewing_patterns.get("deep_dive_pattern", True),
        }

        return {
            "categories": desired_categories,
            "tags": desired_tags,
            "characteristics": desired_characteristics,
            "time_intensity": time_intensity,
            "prediction_confidence": self._calculate_desire_confidence(
                behavioral_profile,
                time_intensity,
            ),
        }

    def _identify_cravings(
        self,
        current_desires: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Identify strong cravings (intensity > threshold)."""
        cravings = []

        # Check category cravings
        for category_desire in current_desires.get("categories", []):
            if category_desire["intensity"] >= self.craving_threshold:
                cravings.append(
                    {
                        "type": "category",
                        "value": category_desire["category"],
                        "intensity": category_desire["intensity"],
                        "urgency": "high" if category_desire["intensity"] > 0.85 else "medium",
                    }
                )

        # Check tag cravings
        for tag_desire in current_desires.get("tags", []):
            if tag_desire["intensity"] >= self.craving_threshold:
                cravings.append(
                    {
                        "type": "tag",
                        "value": tag_desire["tag"],
                        "intensity": tag_desire["intensity"],
                        "urgency": "high" if tag_desire["intensity"] > 0.85 else "medium",
                    }
                )

        return cravings

    def _predict_next_desires(
        self,
        behavioral_profile: Dict[str, Any],
        current_desires: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Predict what user will desire next."""
        category_evolution = behavioral_profile.get("category_evolution", {})
        viewing_patterns = behavioral_profile.get("viewing_patterns", {})

        # Predict next categories based on evolution
        next_categories = []
        emerging_categories = category_evolution.get("emerging_categories", [])

        for category in emerging_categories:
            next_categories.append(
                {
                    "category": category,
                    "probability": 0.6,
                    "reason": "Emerging interest trend",
                }
            )

        # Predict next session characteristics
        next_session = {
            "predicted_duration": viewing_patterns.get("average_session_length", 1800),
            "predicted_intensity": current_desires.get("time_intensity", 1.0) * 0.9,  # Slight decay
            "predicted_focus": viewing_patterns.get("deep_dive_pattern", True),
        }

        return {
            "next_categories": next_categories,
            "next_session": next_session,
            "prediction_horizon": "next_session",
        }

    def _calculate_desire_intensity(
        self,
        current_desires: Dict[str, Any],
        behavioral_profile: Dict[str, Any],
    ) -> Dict[str, float]:
        """Calculate intensity scores for different desires."""
        intensities = {}

        # Category intensities
        for category_desire in current_desires.get("categories", []):
            intensities[f"category:{category_desire['category']}"] = category_desire["intensity"]

        # Tag intensities
        for tag_desire in current_desires.get("tags", []):
            intensities[f"tag:{tag_desire['tag']}"] = tag_desire["intensity"]

        # Overall intensity
        if intensities:
            intensities["overall"] = max(intensities.values())
        else:
            intensities["overall"] = 0.5

        return intensities

    def _calculate_prediction_confidence(
        self,
        behavioral_profile: Dict[str, Any],
    ) -> float:
        """Calculate confidence in predictions."""
        profile_strength = behavioral_profile.get("profile_strength", 0.5)

        # More data = higher confidence
        if profile_strength > 0.8:
            return 0.9  # High confidence
        elif profile_strength > 0.5:
            return 0.7  # Medium confidence
        else:
            return 0.5  # Low confidence

    def _calculate_desire_confidence(
        self,
        behavioral_profile: Dict[str, Any],
        time_intensity: float,
    ) -> float:
        """Calculate confidence in desire predictions."""
        profile_strength = behavioral_profile.get("profile_strength", 0.5)

        # Boost confidence during peak times
        time_boost = 1.0 if time_intensity > 1.2 else 0.9

        return min(profile_strength * time_boost, 0.95)

    def _calculate_profile_strength(
        self,
        viewing_patterns: Dict[str, Any],
        temporal_patterns: Dict[str, Any],
        category_evolution: Dict[str, Any],
    ) -> float:
        """Calculate strength of behavioral profile."""
        # More patterns = stronger profile
        pattern_count = sum(
            [
                len(viewing_patterns),
                len(temporal_patterns),
                len(category_evolution),
            ]
        )

        # Normalize to 0-1
        return min(pattern_count / 30, 1.0)

    def get_content_for_desires(
        self,
        db: Session,
        workspace_id: str,
        desires: Dict[str, Any],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get content that matches predicted desires."""
        query = db.query(Content).filter(
            Content.workspace_id == workspace_id,
            Content.status == "published",
        )

        # Filter by desired categories
        desired_categories = desires.get("current_desires", {}).get("categories", [])
        if desired_categories:
            category_slugs = [d["category"] for d in desired_categories]
            # Get category IDs from slugs
            categories = (
                db.query(Category)
                .filter(
                    Category.workspace_id == workspace_id,
                    Category.slug.in_(category_slugs),
                )
                .all()
            )
            category_ids = [cat.id for cat in categories]

            if category_ids:
                query = query.filter(Content.category_id.in_(category_ids))

        # Order by relevance to desires
        content = (
            query.order_by(
                desc(Content.view_count),
                desc(Content.created_at),
            )
            .limit(limit * 2)
            .all()
        )

        # Score by desire match
        scored_content = []
        for item in content:
            score = self._score_content_for_desires(item, desires)
            scored_content.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "thumbnail_url": item.thumbnail_url,
                    "video_url": item.video_url,
                    "desire_match_score": score,
                    "matches_cravings": score >= self.craving_threshold,
                }
            )

        # Sort by desire match score
        scored_content.sort(key=lambda x: x["desire_match_score"], reverse=True)

        return scored_content[:limit]

    def _score_content_for_desires(
        self,
        content: Content,
        desires: Dict[str, Any],
    ) -> float:
        """Score how well content matches desires."""
        score = 0.0

        current_desires = desires.get("current_desires", {})
        cravings = desires.get("cravings", [])

        # Check category match
        if content.category:
            category_slug = content.category.slug
            for category_desire in current_desires.get("categories", []):
                if category_desire["category"] == category_slug:
                    score += category_desire["intensity"] * 0.5
                    break

        # Check craving match (higher weight)
        for craving in cravings:
            if craving["type"] == "category" and content.category:
                if craving["value"] == content.category.slug:
                    score += craving["intensity"] * 0.7  # Higher weight for cravings
            elif craving["type"] == "tag" and content.tags_json:
                if craving["value"] in content.tags_json:
                    score += craving["intensity"] * 0.6

        # Boost for popular content
        if content.view_count and content.view_count > 1000:
            score += 0.1

        return min(score, 1.0)
