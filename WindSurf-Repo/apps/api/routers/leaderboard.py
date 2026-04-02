"""Monthly leaderboard endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.live_stream import MonthlyLeaderboard
from db.models.user import User
from db.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier
from apps.api.deps import get_current_user, get_current_workspace_id
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class LeaderboardEntry(BaseModel):
    """Leaderboard entry."""

    rank: int
    user_id: str
    user_email: str
    user_name: Optional[str]
    total_score: int
    live_sessions: int
    total_minutes: int
    total_viewers: int
    gems_earned: int
    reward: Optional[str] = None  # "free_month", etc.


class LeaderboardResponse(BaseModel):
    """Leaderboard response."""

    period: str  # "2024-02"
    entries: List[LeaderboardEntry]
    my_rank: Optional[int] = None
    my_score: Optional[int] = None


@router.get("/monthly", response_model=LeaderboardResponse)
async def get_monthly_leaderboard(
    year: Optional[int] = None,
    month: Optional[int] = None,
    user: Optional[User] = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    """Get monthly leaderboard for live streaming."""

    # Default to current month
    now = datetime.utcnow()
    year = year or now.year
    month = month or now.month

    # Get leaderboard entries for this month
    entries_query = (
        db.query(
            MonthlyLeaderboard.user_id,
            func.sum(MonthlyLeaderboard.total_score).label("total_score"),
            func.sum(MonthlyLeaderboard.live_sessions_count).label("live_sessions"),
            func.sum(MonthlyLeaderboard.total_live_minutes).label("total_minutes"),
            func.sum(MonthlyLeaderboard.total_viewers).label("total_viewers"),
            func.sum(MonthlyLeaderboard.total_gems_earned).label("gems_earned"),
        )
        .filter(
            MonthlyLeaderboard.workspace_id == workspace_id,
            MonthlyLeaderboard.year == year,
            MonthlyLeaderboard.month == month,
        )
        .group_by(MonthlyLeaderboard.user_id)
        .order_by(desc("total_score"))
        .limit(limit)
    )

    entries_data = entries_query.all()

    # Build leaderboard entries
    leaderboard_entries = []
    my_rank = None
    my_score = None

    for idx, entry_data in enumerate(entries_data, start=1):
        user_obj = db.query(User).filter(User.id == entry_data.user_id).first()

        # Determine reward
        reward = None
        if idx == 1:
            reward = "free_month"  # 1st place
        elif idx == 2:
            reward = "free_month"  # 2nd place
        elif idx == 3:
            reward = "free_month"  # 3rd place

        leaderboard_entry = LeaderboardEntry(
            rank=idx,
            user_id=entry_data.user_id,
            user_email=user_obj.email if user_obj else "Unknown",
            user_name=user_obj.full_name if user_obj else None,
            total_score=entry_data.total_score or 0,
            live_sessions=entry_data.live_sessions or 0,
            total_minutes=entry_data.total_minutes or 0,
            total_viewers=entry_data.total_viewers or 0,
            gems_earned=entry_data.gems_earned or 0,
            reward=reward,
        )
        leaderboard_entries.append(leaderboard_entry)

        # Check if this is current user
        if user and entry_data.user_id == user.id:
            my_rank = idx
            my_score = entry_data.total_score or 0

    return LeaderboardResponse(
        period=f"{year}-{month:02d}",
        entries=leaderboard_entries,
        my_rank=my_rank,
        my_score=my_score,
    )


@router.post("/claim-reward")
async def claim_monthly_reward(
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Claim monthly leaderboard reward (free month for top 3)."""

    now = datetime.utcnow()
    year = now.year
    month = now.month

    # Get user's rank for this month
    entries_query = (
        db.query(
            MonthlyLeaderboard.user_id,
            func.sum(MonthlyLeaderboard.total_score).label("total_score"),
        )
        .filter(
            MonthlyLeaderboard.workspace_id == workspace_id,
            MonthlyLeaderboard.year == year,
            MonthlyLeaderboard.month == month,
        )
        .group_by(MonthlyLeaderboard.user_id)
        .order_by(desc("total_score"))
        .limit(3)
    )

    top_3_users = [entry.user_id for entry in entries_query.all()]

    if user.id not in top_3_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not in the top 3 for this month",
        )

    # Check if already claimed
    leaderboard_entry = (
        db.query(MonthlyLeaderboard)
        .filter(
            MonthlyLeaderboard.user_id == user.id,
            MonthlyLeaderboard.year == year,
            MonthlyLeaderboard.month == month,
        )
        .first()
    )

    if leaderboard_entry and leaderboard_entry.reward_claimed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reward already claimed",
        )

    # Create or update subscription with free month
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
            Subscription.workspace_id == workspace_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .first()
    )

    if subscription:
        # Extend subscription by 30 days
        if subscription.expires_at:
            subscription.expires_at += timedelta(days=30)
        else:
            subscription.expires_at = datetime.utcnow() + timedelta(days=30)
    else:
        # Create new subscription
        subscription = Subscription(
            user_id=user.id,
            workspace_id=workspace_id,
            tier=SubscriptionTier.PREMIUM,
            status=SubscriptionStatus.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(days=30),
            price_period=0.0,  # Free!
            billing_period_days=30,
            auto_renew=False,
        )
        db.add(subscription)

    # Mark reward as claimed
    if not leaderboard_entry:
        leaderboard_entry = MonthlyLeaderboard(
            user_id=user.id,
            workspace_id=workspace_id,
            year=year,
            month=month,
            rank=top_3_users.index(user.id) + 1,
            reward_claimed=True,
        )
        db.add(leaderboard_entry)
    else:
        leaderboard_entry.reward_claimed = True

    user.free_month_earned = True
    user.last_month_rank = top_3_users.index(user.id) + 1

    db.commit()

    logger.info(f"User {user.id} claimed free month reward for rank {user.last_month_rank}")

    return {
        "message": "Free month reward claimed!",
        "rank": user.last_month_rank,
        "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
    }


@router.get("/my-stats")
async def get_my_leaderboard_stats(
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get current user's leaderboard stats."""

    now = datetime.utcnow()

    # Get current month stats
    current_month_entry = (
        db.query(MonthlyLeaderboard)
        .filter(
            MonthlyLeaderboard.user_id == user.id,
            MonthlyLeaderboard.year == now.year,
            MonthlyLeaderboard.month == now.month,
        )
        .first()
    )

    # Calculate rank
    entries_query = (
        db.query(
            MonthlyLeaderboard.user_id,
            func.sum(MonthlyLeaderboard.total_score).label("total_score"),
        )
        .filter(
            MonthlyLeaderboard.workspace_id == workspace_id,
            MonthlyLeaderboard.year == now.year,
            MonthlyLeaderboard.month == now.month,
        )
        .group_by(MonthlyLeaderboard.user_id)
        .order_by(desc("total_score"))
    )

    all_entries = entries_query.all()
    my_rank = None
    for idx, entry in enumerate(all_entries, start=1):
        if entry.user_id == user.id:
            my_rank = idx
            break

    return {
        "gems": user.gems,
        "monthly_score": user.monthly_live_score,
        "current_rank": my_rank,
        "total_live_sessions": user.total_live_sessions,
        "total_live_minutes": user.total_live_minutes,
        "total_live_viewers": user.total_live_viewers,
        "last_month_rank": user.last_month_rank,
        "free_month_earned": user.free_month_earned,
        "can_claim_reward": my_rank is not None
        and my_rank <= 3
        and (not current_month_entry or not current_month_entry.reward_claimed),
    }
