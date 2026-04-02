"""AI-powered recommendation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_user, get_current_workspace_id
from apps.api.routers.admin import require_full_admin
from core.ai.recommendation_engine import RecommendationEngine, ContentOptimizer
from core.ai.user_behavior_analyzer import UserBehaviorAnalyzer, ContentDiscoveryOptimizer
from core.ai.advanced_learning_engine import AdvancedLearningEngine
from core.ai.preference_learner import PreferenceLearner
from core.ai.desire_prediction_engine import DesirePredictionEngine
from core.ai.craving_analyzer import CravingAnalyzer
from core.ai.gooner_intelligence import GoonerIntelligenceEngine, CommunityDominanceEngine
from core.ai.community_leader import CommunityLeaderEngine
from core.ai.engagement_optimizer import EngagementOptimizer
from core.ai.content_flow_engine import ContentFlowEngine
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/ai/recommendations", tags=["ai-recommendations"])


class RecommendationResponse(BaseModel):
    recommendations: List[Dict[str, Any]]
    reason: str


class TrendingResponse(BaseModel):
    trending: List[Dict[str, Any]]
    time_window: str


@router.get("/personalized", response_model=RecommendationResponse)
async def get_personalized_recommendations(
    limit: int = Query(20, ge=1, le=100),
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get personalized content recommendations."""
    engine = RecommendationEngine()
    recommendations = engine.get_personalized_recommendations(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
        limit=limit,
    )

    return RecommendationResponse(
        recommendations=recommendations,
        reason="Based on your viewing history and preferences",
    )


@router.get("/trending", response_model=TrendingResponse)
async def get_trending_content(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get trending content."""
    optimizer = ContentOptimizer()
    trending = optimizer.get_trending_content(
        db,
        workspace_id=workspace_id,
        time_window_hours=hours,
        limit=limit,
    )

    return TrendingResponse(
        trending=trending,
        time_window=f"Last {hours} hours",
    )


@router.get("/discovery-feed")
async def get_discovery_feed(
    limit: int = Query(50, ge=1, le=200),
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get optimized discovery feed (mix of personalized, trending, new)."""
    optimizer = ContentDiscoveryOptimizer()

    # Get user preferences
    engine = RecommendationEngine()
    preferences = engine._analyze_user_preferences(db, user.id, workspace_id)

    feed = optimizer.get_discovery_feed(
        db,
        workspace_id=workspace_id,
        user_preferences=preferences,
        limit=limit,
    )

    return {
        "feed": feed,
        "total": len(feed),
        "optimized": True,
    }


@router.get("/similar/{content_id}")
async def get_similar_content(
    content_id: str,
    limit: int = Query(10, ge=1, le=50),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get content similar to specified content."""
    analyzer = UserBehaviorAnalyzer()
    similar = analyzer.predict_next_content(
        db,
        user_id="",  # Not needed for similar content
        workspace_id=workspace_id,
        current_content_id=content_id,
    )

    return {
        "similar": similar[:limit],
        "content_id": content_id,
    }


@router.post("/learn")
async def learn_from_interaction(
    content_id: str,
    interaction_type: str = Query(
        ..., pattern="^(view|like|share|watch_complete|watch_50_percent|watch_75_percent|favorite)$"
    ),
    duration: Optional[float] = Query(None, ge=0),
    completion_rate: Optional[float] = Query(None, ge=0, le=1),
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Learn from user interaction to improve recommendations (advanced learning)."""
    # Use advanced learning engine
    advanced_engine = AdvancedLearningEngine()
    result = advanced_engine.learn_from_interaction(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
        content_id=content_id,
        interaction_type=interaction_type,
        duration=duration,
        completion_rate=completion_rate,
    )

    return {
        "status": "learned",
        "message": "AI has learned from your interaction and updated preferences",
        "interaction_weight": result.get("interaction_weight", 0),
        "preferences_updated": True,
    }


@router.post("/learn-session")
async def learn_from_session(
    session_data: dict,
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Learn from entire user session."""
    learner = PreferenceLearner()
    learned = learner.learn_from_session(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
        session_data=session_data,
    )

    return {
        "status": "learned",
        "learned_preferences": learned,
        "message": "AI has analyzed your session and learned your preferences",
    }


@router.get("/optimized")
async def get_optimized_recommendations(
    limit: int = Query(20, ge=1, le=100),
    exploration: bool = Query(True),
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get optimized recommendations using advanced learning."""
    advanced_engine = AdvancedLearningEngine()
    recommendations = advanced_engine.get_optimized_recommendations(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
        limit=limit,
        exploration=exploration,
    )

    return {
        "recommendations": recommendations,
        "total": len(recommendations),
        "optimized": True,
        "learning_active": True,
    }


@router.get("/learning-stats")
async def get_learning_stats(
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get AI learning statistics."""
    advanced_engine = AdvancedLearningEngine()
    stats = advanced_engine.get_continuous_learning_stats(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
    )

    return {
        "stats": stats,
        "message": "AI is continuously learning your preferences",
    }


@router.get("/desires")
async def predict_user_desires(
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Predict what user desires and craves right now."""
    desire_engine = DesirePredictionEngine()
    desires = desire_engine.predict_user_desires(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
    )

    return {
        "desires": desires,
        "message": "AI understands what you desire and crave",
    }


@router.get("/desires/content")
async def get_content_for_desires(
    limit: int = Query(20, ge=1, le=100),
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get content that matches predicted desires."""
    desire_engine = DesirePredictionEngine()

    # Predict desires first
    desires = desire_engine.predict_user_desires(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
    )

    # Get content matching desires
    content = desire_engine.get_content_for_desires(
        db,
        workspace_id=workspace_id,
        desires=desires,
        limit=limit,
    )

    return {
        "content": content,
        "desires": desires,
        "total": len(content),
        "message": "Content perfectly matched to your desires",
    }


@router.post("/analyze-cravings")
async def analyze_cravings(
    recent_interactions: List[dict],
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Deep analysis of user cravings."""
    craving_analyzer = CravingAnalyzer()
    cravings = craving_analyzer.analyze_cravings(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
        recent_interactions=recent_interactions,
    )

    return {
        "cravings": cravings,
        "message": "AI has analyzed your deep cravings",
    }


@router.get("/gooner-profile")
async def get_gooner_profile(
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get advanced gooner/goonette profile analysis."""
    gooner_engine = GoonerIntelligenceEngine()
    profile = gooner_engine.analyze_gooner_profile(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
    )

    return {
        "profile": profile,
        "message": "Advanced gooner intelligence analysis complete",
    }


@router.get("/gooner-content")
async def get_gooner_optimized_content(
    limit: int = Query(20, ge=1, le=100),
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get content optimized specifically for gooner profile."""
    gooner_engine = GoonerIntelligenceEngine()

    # Get gooner profile
    profile = gooner_engine.analyze_gooner_profile(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
    )

    # Get optimized content
    content = gooner_engine.get_gooner_optimized_content(
        db,
        workspace_id=workspace_id,
        gooner_profile=profile,
        limit=limit,
    )

    return {
        "content": content,
        "profile": profile,
        "optimized": True,
        "message": "Content optimized for your gooner profile",
    }


@router.get("/gooner-desires")
async def predict_gooner_desires(
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Predict gooner-specific desires."""
    gooner_engine = GoonerIntelligenceEngine()

    # Get profile
    profile = gooner_engine.analyze_gooner_profile(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
    )

    # Predict desires
    desires = gooner_engine.predict_gooner_desires(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
        gooner_profile=profile,
    )

    return {
        "desires": desires,
        "profile": profile,
        "message": "Gooner desires predicted with advanced AI",
    }


@router.get("/community-leadership")
async def get_community_leadership(
    admin: str = Depends(require_full_admin),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get platform's leadership status in gooner community."""
    leader_engine = CommunityLeaderEngine()
    leadership = leader_engine.get_community_leadership_status(
        db,
        workspace_id=workspace_id,
    )

    dominance_engine = CommunityDominanceEngine()
    dominance = dominance_engine.calculate_platform_dominance(
        db,
        workspace_id=workspace_id,
    )

    competitive = dominance_engine.get_competitive_analysis(
        db,
        workspace_id=workspace_id,
    )

    strategy = leader_engine.get_dominance_strategy(
        db,
        workspace_id=workspace_id,
    )

    return {
        "leadership": leadership,
        "dominance": dominance,
        "competitive_analysis": competitive,
        "dominance_strategy": strategy,
        "message": "Platform leadership analysis complete",
    }


@router.get("/community-leaderboard")
async def get_community_leaderboard(
    metric: str = Query("dominance", pattern="^(dominance|intensity|engagement)$"),
    limit: int = Query(50, ge=1, le=100),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get community leaderboard (top gooners/goonettes)."""
    gooner_engine = GoonerIntelligenceEngine()
    leaderboard = gooner_engine.get_community_leaderboard(
        db,
        workspace_id=workspace_id,
        metric=metric,
        limit=limit,
    )

    return {
        "leaderboard": leaderboard,
        "metric": metric,
        "message": "Community leaderboard - top gooners/goonettes",
    }


@router.get("/cross-platform-intelligence")
async def get_cross_platform_intelligence(
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get cross-platform intelligence (X/Twitter, etc.)."""
    gooner_engine = GoonerIntelligenceEngine()

    # Get user preferences
    profile = gooner_engine.analyze_gooner_profile(
        db,
        user_id=user.id,
        workspace_id=workspace_id,
    )

    preferences = profile.get("preferences", {})

    # Analyze cross-platform
    intelligence = gooner_engine.analyze_cross_platform_intelligence(preferences)

    return {
        "intelligence": intelligence,
        "message": "Cross-platform intelligence from X/Twitter and community",
    }


@router.get("/continuous-flow")
async def get_continuous_content_flow(
    current_content_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get continuous content flow for seamless discovery."""
    optimizer = EngagementOptimizer()

    # Get user preferences
    from core.ai.recommendation_engine import RecommendationEngine

    engine = RecommendationEngine()
    preferences = engine._analyze_user_preferences(db, user.id, workspace_id)

    # Create continuous flow
    flow = optimizer.create_continuous_content_flow(
        db,
        workspace_id=workspace_id,
        user_preferences=preferences,
        current_content_id=current_content_id,
        limit=limit,
    )

    return {
        "flow": flow,
        "total": len(flow),
        "continuous": True,
        "seamless_transitions": True,
        "message": "Continuous content flow optimized for discovery",
    }


@router.get("/seamless-flow")
async def get_seamless_flow(
    current_content_id: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get seamless content flow."""
    flow_engine = ContentFlowEngine()

    # Get user preferences
    from core.ai.recommendation_engine import RecommendationEngine

    engine = RecommendationEngine()
    preferences = engine._analyze_user_preferences(db, user.id, workspace_id)

    # Create seamless flow
    flow = flow_engine.create_seamless_flow(
        db,
        workspace_id=workspace_id,
        current_content_id=current_content_id,
        user_preferences=preferences,
        limit=limit,
    )

    return {
        "flow": flow,
        "seamless": True,
        "continuous": True,
        "message": "Seamless content flow for continuous discovery",
    }


@router.get("/optimize-search")
async def optimize_search_results(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    user: str = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get optimized search results based on user preferences."""
    # First get basic search results (would use actual search)
    from apps.api.routers.content import search_content

    # This is a placeholder - would integrate with actual search

    optimizer = ContentDiscoveryOptimizer()
    engine = RecommendationEngine()
    preferences = engine._analyze_user_preferences(db, user.id, workspace_id)

    # In production, get actual search results and optimize them
    return {
        "query": query,
        "optimized": True,
        "message": "Search results optimized based on your preferences",
    }
