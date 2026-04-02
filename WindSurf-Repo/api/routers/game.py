"""Game API router for Neon Grid."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta

from db.session import get_db
from db.models.game import (
    GameProfile,
    GameLevelProgress,
    GamePurchase,
    GameAchievement,
    GameLeaderboard,
)
from db.models.user import User
from apps.api.schemas.game import (
    GameProfileResponse,
    GameProfileUpdate,
    LevelData,
    LevelProgressResponse,
    LevelCompleteRequest,
    LevelCompleteResponse,
    PurchaseRequest,
    PurchaseResponse,
    AchievementResponse,
    LeaderboardEntry,
    LeaderboardResponse,
)
from apps.api.deps import get_current_user
from core.game.level_generator import LevelGenerator
from core.game.progression import ProgressionCalculator
from core.game.achievements import AchievementManager
from core.game.anti_cheat import AntiCheatDetector
from core.game.level_validator import LevelValidator
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["game"])


@router.get("/profile", response_model=GameProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user's game profile."""
    profile = db.query(GameProfile).filter(GameProfile.user_id == current_user.id).first()

    if not profile:
        # Create new profile
        profile = GameProfile(
            user_id=current_user.id,
            workspace_id=current_user.workspace_id,
            unlocked_particles=["default"],
            unlocked_themes=["neon"],
            unlocked_powerups=[],
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile


@router.patch("/profile", response_model=GameProfileResponse)
async def update_profile(
    update: GameProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update game profile settings."""
    profile = db.query(GameProfile).filter(GameProfile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game profile not found")

    if update.sound_enabled is not None:
        profile.sound_enabled = update.sound_enabled
    if update.music_enabled is not None:
        profile.music_enabled = update.music_enabled
    if update.vibration_enabled is not None:
        profile.vibration_enabled = update.vibration_enabled

    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)

    return profile


@router.get("/level/{level_number}", response_model=LevelData)
async def get_level(
    level_number: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get level data for a specific level."""
    if level_number < 0 or level_number > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Level must be between 0 and 1000"
        )

    profile = db.query(GameProfile).filter(GameProfile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game profile not found")

    # Check if level is unlocked
    if level_number > profile.current_level + 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Level {level_number} is locked. Complete level {profile.current_level} first.",
        )

    # Generate level data
    generator = LevelGenerator()
    level_data = generator.generate_level(level_number)

    return level_data


@router.get("/level/{level_number}/progress", response_model=LevelProgressResponse)
async def get_level_progress(
    level_number: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get progress for a specific level."""
    profile = db.query(GameProfile).filter(GameProfile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game profile not found")

    progress = (
        db.query(GameLevelProgress)
        .filter(
            GameLevelProgress.profile_id == profile.id,
            GameLevelProgress.level_number == level_number,
        )
        .first()
    )

    if not progress:
        # Create new progress entry
        progress = GameLevelProgress(profile_id=profile.id, level_number=level_number)
        db.add(progress)
        db.commit()
        db.refresh(progress)

    return progress


@router.post("/level/complete", response_model=LevelCompleteResponse)
async def complete_level(
    request: LevelCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit level completion."""
    profile = db.query(GameProfile).filter(GameProfile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game profile not found")

    # Get or create level progress
    progress = (
        db.query(GameLevelProgress)
        .filter(
            GameLevelProgress.profile_id == profile.id,
            GameLevelProgress.level_number == request.level_number,
        )
        .first()
    )

    if not progress:
        progress = GameLevelProgress(profile_id=profile.id, level_number=request.level_number)
        db.add(progress)

    # Update progress
    progress.attempts += 1
    progress.last_played_at = datetime.utcnow()

    if request.score > progress.best_score:
        progress.best_score = request.score
        if request.best_time:
            progress.best_time = request.time_taken

    if request.is_perfect and not progress.is_perfect:
        progress.is_perfect = True

    if not progress.is_completed:
        progress.is_completed = True
        progress.first_completed_at = datetime.utcnow()

    progress.hints_used += request.hints_used

    # Anti-cheat detection
    anti_cheat = AntiCheatDetector()
    cheat_analysis = anti_cheat.analyze_completion(
        level_number=request.level_number,
        time_taken=request.time_taken,
        moves=request.moves,
        hints_used=request.hints_used,
        connection_times=request.connection_times or [],
        connection_order=[tuple(c) for c in (request.connection_order or [])],
    )

    # Calculate base rewards
    calculator = ProgressionCalculator()
    rewards = calculator.calculate_level_rewards(
        level_number=request.level_number,
        score=request.score,
        time_taken=request.time_taken,
        is_perfect=request.is_perfect,
        hints_used=request.hints_used,
    )

    # Apply human completion bonus if verified
    if anti_cheat.verify_human_completion(cheat_analysis):
        human_bonus = anti_cheat.get_completion_bonus(cheat_analysis, request.level_number)
        rewards["coins"] = human_bonus["coins"]
        rewards["xp"] = human_bonus["xp"]

    # Special reward for completing all 1000 levels (human verified)
    if request.level_number == 1000 and anti_cheat.verify_human_completion(cheat_analysis):
        rewards["coins"] += 50000  # Massive bonus
        rewards["xp"] += 100000
        # Unlock legendary achievement
        achievement_manager = AchievementManager(db, profile)
        achievement_manager._check_achievement("complete_all_1000_human", 1000)

    # Grant rewards
    progress.coins_earned += rewards["coins"]
    progress.xp_earned += rewards["xp"]
    profile.coins += rewards["coins"]
    profile.total_xp += rewards["xp"]
    profile.total_games_played += 1
    profile.total_wins += 1

    # Update leaderboard
    leaderboard_entry = (
        db.query(GameLeaderboard)
        .filter(
            GameLeaderboard.profile_id == profile.id, GameLeaderboard.leaderboard_type == "global"
        )
        .first()
    )

    if not leaderboard_entry:
        leaderboard_entry = GameLeaderboard(
            profile_id=profile.id,
            leaderboard_type="global",
            score=profile.total_xp,
            level_reached=profile.current_level,
            total_xp=profile.total_xp,
        )
        db.add(leaderboard_entry)
    else:
        leaderboard_entry.score = profile.total_xp
        leaderboard_entry.level_reached = profile.current_level
        leaderboard_entry.total_xp = profile.total_xp
        leaderboard_entry.updated_at = datetime.utcnow()

    # Update streaks and level progression
    if request.level_number >= profile.current_level:
        # Completed current or higher level
        profile.current_streak += 1
        if profile.current_streak > profile.best_streak:
            profile.best_streak = profile.current_streak
        # Unlock next level
        if request.level_number >= profile.current_level:
            profile.current_level = min(1000, request.level_number + 1)
    else:
        # Replaying an old level - reset streak
        profile.current_streak = 0

    # Check for level up
    level_up = False
    new_player_level = None
    old_player_level = profile.player_level
    profile.player_level = calculator.calculate_player_level(profile.total_xp)

    if profile.player_level > old_player_level:
        level_up = True
        new_player_level = profile.player_level

    # Check achievements
    achievement_manager = AchievementManager(db, profile)
    achievements_unlocked = achievement_manager.check_and_unlock_achievements(
        level_number=request.level_number, score=request.score, is_perfect=request.is_perfect
    )

    db.commit()
    db.refresh(profile)
    db.refresh(progress)

    return LevelCompleteResponse(
        success=True,
        coins_earned=rewards["coins"],
        xp_earned=rewards["xp"],
        level_up=level_up,
        new_player_level=new_player_level,
        achievements_unlocked=achievements_unlocked,
        next_level_unlocked=True,
    )


@router.post("/purchase", response_model=PurchaseResponse)
async def process_purchase(
    request: PurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Process in-app purchase."""
    profile = db.query(GameProfile).filter(GameProfile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game profile not found")

    # Check if transaction already exists
    existing = (
        db.query(GamePurchase).filter(GamePurchase.transaction_id == request.transaction_id).first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction already processed"
        )

    # Process purchase based on product_id
    coins_granted = 0
    items_granted = {}

    # Product definitions
    products = {
        "coins_100": {"coins": 100, "price": 0.99},
        "coins_500": {"coins": 500, "price": 4.99},
        "coins_1000": {"coins": 1000, "price": 8.99},
        "coins_5000": {"coins": 5000, "price": 39.99},
        "coins_10000": {"coins": 10000, "price": 69.99},
        "remove_ads": {"coins": 0, "remove_ads": True, "price": 2.99},
        "premium_pack": {
            "coins": 2000,
            "themes": ["premium"],
            "particles": ["gold"],
            "price": 9.99,
        },
        "starter_pack": {"coins": 500, "hints": 10, "price": 4.99},
    }

    product = products.get(request.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown product: {request.product_id}"
        )

    coins_granted = product.get("coins", 0)
    items_granted = {k: v for k, v in product.items() if k not in ["coins", "price"]}

    # Create purchase record
    purchase = GamePurchase(
        profile_id=profile.id,
        product_id=request.product_id,
        product_type="coins" if coins_granted > 0 else "other",
        amount_paid=request.amount_paid,
        currency=request.currency,
        platform=request.platform,
        transaction_id=request.transaction_id,
        receipt_data=request.receipt_data,
        is_verified=True,  # In production, verify with platform
        coins_granted=coins_granted,
        items_granted=items_granted,
    )

    # Grant rewards
    profile.coins += coins_granted
    if "themes" in items_granted:
        profile.unlocked_themes.extend(items_granted["themes"])
    if "particles" in items_granted:
        profile.unlocked_particles.extend(items_granted["particles"])

    db.add(purchase)
    db.commit()
    db.refresh(profile)
    db.refresh(purchase)

    return PurchaseResponse(
        success=True,
        purchase_id=purchase.id,
        coins_granted=coins_granted,
        items_granted=items_granted,
        new_coin_balance=profile.coins,
    )


@router.get("/achievements", response_model=List[AchievementResponse])
async def get_achievements(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user's achievements."""
    profile = db.query(GameProfile).filter(GameProfile.user_id == current_user.id).first()

    if not profile:
        return []

    achievements = (
        db.query(GameAchievement)
        .filter(GameAchievement.profile_id == profile.id)
        .order_by(GameAchievement.created_at)
        .all()
    )

    return achievements


@router.get("/leaderboard/{leaderboard_type}", response_model=LeaderboardResponse)
async def get_leaderboard(
    leaderboard_type: str,
    limit: int = 100,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get leaderboard - public endpoint."""
    profile = None
    if current_user:
        profile = db.query(GameProfile).filter(GameProfile.user_id == current_user.id).first()

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
    user_rank = None

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

        if profile and entry.profile_id == profile.id:
            user_rank = rank

    # Get total players
    total_players = (
        db.query(func.count(GameLeaderboard.id))
        .filter(GameLeaderboard.leaderboard_type == leaderboard_type)
        .scalar()
    )

    return LeaderboardResponse(
        leaderboard_type=leaderboard_type,
        entries=entries,
        user_rank=user_rank,
        total_players=total_players or 0,
    )
