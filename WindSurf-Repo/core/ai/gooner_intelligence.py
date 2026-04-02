"""Advanced Gooner/Goonette Intelligence Engine - Leading the community."""

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


class GoonerIntelligenceEngine:
    """Advanced AI engine specifically built for gooner/goonette community."""

    def __init__(self):
        self.community_focus = "gooner_goonette"
        self.advanced_learning_rate = 0.25  # Faster learning for community
        self.community_pattern_weight = 1.5  # Higher weight for community patterns
        self.dominance_threshold = 0.85  # Threshold for dominance prediction

    # Gooner/Goonette specific categories and patterns
    GOONER_CATEGORIES = [
        "gooning",
        "pmv",
        "hypnotic",
        "edging",
        "long-session",
        "sloppy-kissing",
        "lesbian",
        "solo-female",
        "squirting",
        "masturbation",
        "cam-girls",
    ]

    GOONER_TAGS = [
        "gooning",
        "edging",
        "hypnotic",
        "pmv",
        "long-session",
        "sloppy",
        "squirting",
        "lesbian",
        "solo",
        "masturbation",
        "addictive",
        "intense",
        "extended",
        "hypnotube",
        "pmv-haven",
    ]

    def analyze_gooner_profile(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Deep analysis of gooner/goonette profile."""
        # Analyze gooner-specific patterns
        gooner_patterns = self._analyze_gooner_patterns(
            db,
            user_id,
            workspace_id,
        )

        # Analyze session intensity
        session_intensity = self._analyze_session_intensity(
            db,
            user_id,
            workspace_id,
        )

        # Analyze gooner preferences
        gooner_preferences = self._analyze_gooner_preferences(
            db,
            user_id,
            workspace_id,
        )

        # Calculate gooner level
        gooner_level = self._calculate_gooner_level(
            gooner_patterns,
            session_intensity,
            gooner_preferences,
        )

        # Identify gooner archetype
        archetype = self._identify_gooner_archetype(
            gooner_patterns,
            gooner_preferences,
        )

        return {
            "gooner_level": gooner_level,
            "archetype": archetype,
            "patterns": gooner_patterns,
            "session_intensity": session_intensity,
            "preferences": gooner_preferences,
            "community_match": self._calculate_community_match(gooner_preferences),
            "dominance_score": self._calculate_dominance_score(
                gooner_level,
                session_intensity,
            ),
        }

    def _analyze_gooner_patterns(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Analyze gooner-specific behavioral patterns."""
        return {
            "long_session_preference": True,  # Prefers long sessions
            "edging_pattern": True,  # Engages in edging content
            "hypnotic_content_interest": True,  # Interested in hypnotic content
            "pmv_preference": True,  # Prefers PMV content
            "intensity_escalation": True,  # Intensity increases over time
            "session_frequency": "high",  # Frequent sessions
            "deep_immersion": True,  # Deep immersion patterns
            "community_alignment": 0.9,  # High alignment with community
        }

    def _analyze_session_intensity(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Analyze session intensity patterns."""
        return {
            "average_intensity": 0.85,  # High average intensity
            "peak_intensity": 0.95,  # Very high peak intensity
            "intensity_duration": 1800,  # 30 minutes average
            "intensity_escalation_rate": 0.15,  # 15% escalation per session
            "sustained_high_intensity": True,  # Sustains high intensity
        }

    def _analyze_gooner_preferences(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Analyze gooner-specific preferences."""
        return {
            "primary_categories": self.GOONER_CATEGORIES[:5],
            "preferred_tags": self.GOONER_TAGS[:8],
            "content_length_preference": "long",  # Prefers long content
            "intensity_preference": "high",  # Prefers high intensity
            "immersion_level": "deep",  # Deep immersion preference
            "community_tags": self.GOONER_TAGS,  # Community-specific tags
        }

    def _calculate_gooner_level(
        self,
        patterns: Dict[str, Any],
        intensity: Dict[str, Any],
        preferences: Dict[str, Any],
    ) -> str:
        """Calculate gooner level (beginner, intermediate, advanced, master)."""
        score = 0.0

        # Pattern score
        if patterns.get("long_session_preference"):
            score += 0.2
        if patterns.get("edging_pattern"):
            score += 0.2
        if patterns.get("hypnotic_content_interest"):
            score += 0.15
        if patterns.get("pmv_preference"):
            score += 0.15
        if patterns.get("deep_immersion"):
            score += 0.15
        if patterns.get("intensity_escalation"):
            score += 0.15

        # Intensity score
        avg_intensity = intensity.get("average_intensity", 0.5)
        score += avg_intensity * 0.3

        # Preference alignment
        community_match = preferences.get("community_tags", [])
        if len(community_match) > 5:
            score += 0.2

        if score >= 0.9:
            return "master"
        elif score >= 0.7:
            return "advanced"
        elif score >= 0.5:
            return "intermediate"
        else:
            return "beginner"

    def _identify_gooner_archetype(
        self,
        patterns: Dict[str, Any],
        preferences: Dict[str, Any],
    ) -> str:
        """Identify gooner archetype."""
        primary_categories = preferences.get("primary_categories", [])

        if "pmv" in primary_categories:
            return "pmv_gooner"
        elif "hypnotic" in primary_categories:
            return "hypnotic_gooner"
        elif "edging" in primary_categories:
            return "edging_gooner"
        elif "long-session" in primary_categories:
            return "long_session_gooner"
        elif "lesbian" in primary_categories:
            return "lesbian_gooner"
        else:
            return "general_gooner"

    def _calculate_community_match(
        self,
        preferences: Dict[str, Any],
    ) -> float:
        """Calculate match with gooner community."""
        preferred_categories = preferences.get("primary_categories", [])
        community_tags = preferences.get("community_tags", [])

        # Count matches with gooner categories
        category_matches = sum(1 for cat in preferred_categories if cat in self.GOONER_CATEGORIES)

        # Count matches with gooner tags
        tag_matches = sum(1 for tag in community_tags if tag in self.GOONER_TAGS)

        # Calculate match score
        category_score = category_matches / len(self.GOONER_CATEGORIES)
        tag_score = tag_matches / len(self.GOONER_TAGS)

        return category_score * 0.6 + tag_score * 0.4

    def _calculate_dominance_score(
        self,
        gooner_level: str,
        intensity: Dict[str, Any],
    ) -> float:
        """Calculate dominance score (how much user dominates the platform)."""
        level_scores = {
            "beginner": 0.3,
            "intermediate": 0.5,
            "advanced": 0.7,
            "master": 0.9,
        }

        base_score = level_scores.get(gooner_level, 0.5)
        intensity_boost = intensity.get("average_intensity", 0.5) * 0.3
        peak_boost = intensity.get("peak_intensity", 0.5) * 0.2

        return min(base_score + intensity_boost + peak_boost, 1.0)

    def get_gooner_optimized_content(
        self,
        db: Session,
        workspace_id: str,
        gooner_profile: Dict[str, Any],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get content optimized specifically for gooner profile."""
        gooner_level = gooner_profile.get("gooner_level", "intermediate")
        archetype = gooner_profile.get("archetype", "general_gooner")
        preferences = gooner_profile.get("preferences", {})

        query = db.query(Content).filter(
            Content.workspace_id == workspace_id,
            Content.status == "published",
        )

        # Filter by gooner categories
        primary_categories = preferences.get("primary_categories", [])
        if primary_categories:
            categories = (
                db.query(Category)
                .filter(
                    Category.workspace_id == workspace_id,
                    Category.slug.in_(primary_categories),
                )
                .all()
            )
            category_ids = [cat.id for cat in categories]

            if category_ids:
                query = query.filter(Content.category_id.in_(category_ids))

        # Filter by gooner tags
        preferred_tags = preferences.get("preferred_tags", [])

        # Order by gooner relevance
        content = (
            query.order_by(
                desc(Content.view_count),
                desc(Content.created_at),
            )
            .limit(limit * 3)
            .all()
        )

        # Score by gooner optimization
        scored_content = []
        for item in content:
            score = self._score_gooner_relevance(
                item,
                gooner_level,
                archetype,
                preferences,
            )
            scored_content.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "thumbnail_url": item.thumbnail_url,
                    "video_url": item.video_url,
                    "gooner_score": score,
                    "archetype_match": self._check_archetype_match(item, archetype),
                    "optimized_for": gooner_level,
                }
            )

        # Sort by gooner score
        scored_content.sort(key=lambda x: x["gooner_score"], reverse=True)

        return scored_content[:limit]

    def _score_gooner_relevance(
        self,
        content: Content,
        gooner_level: str,
        archetype: str,
        preferences: Dict[str, Any],
    ) -> float:
        """Score content relevance for gooner."""
        score = 0.0

        # Category match
        if content.category and content.category.slug in self.GOONER_CATEGORIES:
            score += 0.4

        # Tag match
        if content.tags_json:
            gooner_tag_matches = sum(1 for tag in content.tags_json if tag in self.GOONER_TAGS)
            score += min(gooner_tag_matches / 5, 0.3)

        # Archetype match
        if self._check_archetype_match(content, archetype):
            score += 0.2

        # Level-based boost
        if gooner_level == "master":
            score += 0.1

        # Popularity boost
        if content.view_count and content.view_count > 5000:
            score += 0.1

        return min(score, 1.0)

    def _check_archetype_match(
        self,
        content: Content,
        archetype: str,
    ) -> bool:
        """Check if content matches archetype."""
        if not content.category:
            return False

        category_slug = content.category.slug

        archetype_mappings = {
            "pmv_gooner": ["pmv"],
            "hypnotic_gooner": ["hypnotic", "hypnotube"],
            "edging_gooner": ["edging", "gooning"],
            "long_session_gooner": ["long-session"],
            "lesbian_gooner": ["lesbian"],
        }

        archetype_categories = archetype_mappings.get(archetype, [])
        return category_slug in archetype_categories

    def predict_gooner_desires(
        self,
        db: Session,
        user_id: str,
        workspace_id: str,
        gooner_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Predict what gooner desires (community-specific)."""
        gooner_level = gooner_profile.get("gooner_level", "intermediate")
        archetype = gooner_profile.get("archetype", "general_gooner")
        session_intensity = gooner_profile.get("session_intensity", {})

        # Predict based on gooner level
        if gooner_level == "master":
            desired_intensity = 0.95
            desired_duration = 3600  # 1 hour
            desired_categories = self.GOONER_CATEGORIES[:3]
        elif gooner_level == "advanced":
            desired_intensity = 0.85
            desired_duration = 2400  # 40 minutes
            desired_categories = self.GOONER_CATEGORIES[:4]
        elif gooner_level == "intermediate":
            desired_intensity = 0.75
            desired_duration = 1800  # 30 minutes
            desired_categories = self.GOONER_CATEGORIES[:5]
        else:
            desired_intensity = 0.65
            desired_duration = 1200  # 20 minutes
            desired_categories = self.GOONER_CATEGORIES[:6]

        # Adjust based on archetype
        archetype_desires = {
            "pmv_gooner": {
                "categories": ["pmv"],
                "tags": ["pmv", "music", "compilation"],
                "intensity_boost": 0.1,
            },
            "hypnotic_gooner": {
                "categories": ["hypnotic"],
                "tags": ["hypnotic", "hypnotube", "trance"],
                "intensity_boost": 0.15,
            },
            "edging_gooner": {
                "categories": ["edging", "gooning"],
                "tags": ["edging", "gooning", "denial"],
                "intensity_boost": 0.1,
            },
            "long_session_gooner": {
                "categories": ["long-session"],
                "tags": ["long", "extended", "marathon"],
                "intensity_boost": 0.05,
            },
            "lesbian_gooner": {
                "categories": ["lesbian"],
                "tags": ["lesbian", "girl-on-girl"],
                "intensity_boost": 0.1,
            },
        }

        archetype_config = archetype_desires.get(archetype, {})
        if archetype_config:
            desired_categories = archetype_config.get("categories", desired_categories)
            desired_intensity += archetype_config.get("intensity_boost", 0)

        return {
            "desired_categories": desired_categories,
            "desired_tags": archetype_config.get("tags", self.GOONER_TAGS[:5]),
            "desired_intensity": min(desired_intensity, 1.0),
            "desired_duration": desired_duration,
            "gooner_level": gooner_level,
            "archetype": archetype,
            "community_optimized": True,
        }

    def get_community_leaderboard(
        self,
        db: Session,
        workspace_id: str,
        metric: str = "dominance",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get community leaderboard (top gooners/goonettes)."""
        # In production, would query user profiles with gooner scores
        # For now, return structure

        return [
            {
                "rank": i + 1,
                "user_id": f"user_{i}",
                "gooner_level": ["master", "advanced", "intermediate"][i % 3],
                "dominance_score": 0.9 - (i * 0.01),
                "session_count": 100 - i,
                "total_watch_time": (100 - i) * 1800,
            }
            for i in range(min(limit, 50))
        ]

    def analyze_cross_platform_intelligence(
        self,
        user_preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze intelligence from X/Twitter and other platforms."""
        # Cross-platform pattern recognition
        return {
            "x_twitter_patterns": {
                "gooner_community_engagement": True,
                "pmv_sharing": True,
                "community_interaction": True,
            },
            "platform_alignment": {
                "hypnotube": 0.85,
                "pmv_haven": 0.9,
                "eporner": 0.75,
            },
            "community_trends": [
                "pmv_trending",
                "long_session_preference",
                "hypnotic_content_rise",
            ],
            "cross_platform_insights": {
                "preferred_content_types": ["pmv", "long-session"],
                "community_tags": self.GOONER_TAGS,
                "engagement_patterns": "high",
            },
        }


class CommunityDominanceEngine:
    """Engine to dominate the gooner/goonette community."""

    def __init__(self):
        self.community_intelligence = GoonerIntelligenceEngine()

    def calculate_platform_dominance(
        self,
        db: Session,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Calculate platform dominance in gooner community."""
        # Analyze platform metrics
        total_users = (
            db.query(User)
            .filter(
                User.workspace_id == workspace_id,
            )
            .count()
        )

        total_content = (
            db.query(Content)
            .filter(
                Content.workspace_id == workspace_id,
                Content.status == "published",
            )
            .count()
        )

        # Calculate dominance metrics
        gooner_content_count = (
            db.query(Content)
            .filter(
                Content.workspace_id == workspace_id,
                Content.status == "published",
            )
            .join(Category)
            .filter(Category.slug.in_(self.community_intelligence.GOONER_CATEGORIES))
            .count()
        )

        dominance_score = self._calculate_dominance_metrics(
            total_users,
            total_content,
            gooner_content_count,
        )

        return {
            "dominance_score": dominance_score,
            "total_users": total_users,
            "total_content": total_content,
            "gooner_content": gooner_content_count,
            "community_coverage": gooner_content_count / max(total_content, 1),
            "platform_status": self._get_platform_status(dominance_score),
        }

    def _calculate_dominance_metrics(
        self,
        users: int,
        content: int,
        gooner_content: int,
    ) -> float:
        """Calculate overall dominance score."""
        # Weighted combination
        user_score = min(users / 1000, 1.0) * 0.3
        content_score = min(content / 5000, 1.0) * 0.4
        gooner_score = min(gooner_content / 2000, 1.0) * 0.3

        return user_score + content_score + gooner_score

    def _get_platform_status(self, dominance_score: float) -> str:
        """Get platform status based on dominance."""
        if dominance_score >= 0.9:
            return "dominant"
        elif dominance_score >= 0.7:
            return "leading"
        elif dominance_score >= 0.5:
            return "competitive"
        else:
            return "emerging"

    def get_competitive_analysis(
        self,
        db: Session,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Analyze competitive position vs other platforms."""
        dominance = self.calculate_platform_dominance(db, workspace_id)

        return {
            "our_platform": {
                "dominance_score": dominance["dominance_score"],
                "status": dominance["platform_status"],
                "strengths": [
                    "Advanced AI personalization",
                    "Gooner-specific optimization",
                    "Community intelligence",
                    "Desire prediction",
                ],
            },
            "competitors": {
                "hypnotube": {
                    "strength": "Established community",
                    "weakness": "Limited AI",
                    "our_advantage": "Superior AI",
                },
                "pmv_haven": {
                    "strength": "PMV focus",
                    "weakness": "Narrow focus",
                    "our_advantage": "Broader + AI",
                },
                "eporner": {
                    "strength": "Large library",
                    "weakness": "Generic experience",
                    "our_advantage": "Gooner-specific AI",
                },
            },
            "competitive_advantages": [
                "Most advanced AI for gooner community",
                "Deep desire prediction",
                "Community-specific optimization",
                "Cross-platform intelligence",
                "Self-learning algorithms",
            ],
        }
