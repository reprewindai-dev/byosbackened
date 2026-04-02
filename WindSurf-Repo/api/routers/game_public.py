"""Public game endpoints (no auth required)."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from db.session import get_db
from db.models.game import GameLeaderboard, GameProfile
from db.models.user import User
from apps.api.schemas.game import LeaderboardEntry, LeaderboardResponse

router = APIRouter(prefix="/game/public", tags=["game-public"])


@router.get("/leaderboard/{leaderboard_type}", response_model=LeaderboardResponse)
async def get_public_leaderboard(
    leaderboard_type: str, limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)
):
    """Get public leaderboard - no authentication required."""
    # Get top entries
    entries_query = (
        db.query(GameLeaderboard, User.full_name)
        .join(GameProfile, GameLeaderboard.profile_id == GameProfile.id)
        .join(User, GameProfile.user_id == User.id)
        .filter(GameLeaderboard.leaderboard_type == leaderboard_type)
        .order_by(desc(GameLeaderboard.score))
        .limit(limit)
    )

    entries_data = entries_query.all()

    # Build response
    entries = []
    for rank, (entry, user_name) in enumerate(entries_data, 1):
        entries.append(
            LeaderboardEntry(
                rank=rank,
                profile_id=entry.profile_id,
                user_name=user_name or "Anonymous",
                score=entry.score,
                level_reached=entry.level_reached,
                total_xp=entry.total_xp,
            )
        )

    # Get total players
    total_players = (
        db.query(func.count(GameLeaderboard.id))
        .filter(GameLeaderboard.leaderboard_type == leaderboard_type)
        .scalar()
    )

    return LeaderboardResponse(
        leaderboard_type=leaderboard_type,
        entries=entries,
        user_rank=None,  # Not available without auth
        total_players=total_players or 0,
    )
