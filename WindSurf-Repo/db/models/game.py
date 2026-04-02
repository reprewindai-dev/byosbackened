"""Game models for Neon Grid - particle connection puzzle game."""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class GameProfile(Base):
    """User game profile with progression data."""

    __tablename__ = "game_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    # Progression
    current_level = Column(Integer, default=0, nullable=False)
    total_xp = Column(Integer, default=0, nullable=False)
    player_level = Column(Integer, default=1, nullable=False)
    coins = Column(Integer, default=100, nullable=False)  # Starting coins

    # Stats
    total_games_played = Column(Integer, default=0, nullable=False)
    total_wins = Column(Integer, default=0, nullable=False)
    total_losses = Column(Integer, default=0, nullable=False)
    best_streak = Column(Integer, default=0, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)

    # Unlocks
    unlocked_particles = Column(JSON, default=list)  # List of particle skin IDs
    unlocked_themes = Column(JSON, default=list)  # List of theme IDs
    unlocked_powerups = Column(JSON, default=list)  # List of powerup IDs

    # Settings
    sound_enabled = Column(Boolean, default=True, nullable=False)
    music_enabled = Column(Boolean, default=True, nullable=False)
    vibration_enabled = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="game_profile")
    level_progress = relationship(
        "GameLevelProgress", back_populates="profile", cascade="all, delete-orphan"
    )
    purchases = relationship("GamePurchase", back_populates="profile", cascade="all, delete-orphan")
    achievements = relationship(
        "GameAchievement", back_populates="profile", cascade="all, delete-orphan"
    )


class GameLevelProgress(Base):
    """Individual level progress and completion data."""

    __tablename__ = "game_level_progress"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("game_profiles.id"), nullable=False, index=True)
    level_number = Column(Integer, nullable=False, index=True)

    # Completion
    is_completed = Column(Boolean, default=False, nullable=False)
    is_perfect = Column(Boolean, default=False, nullable=False)  # Perfect score
    best_score = Column(Integer, default=0, nullable=False)
    best_time = Column(Float, default=None)  # Best completion time in seconds

    # Attempts
    attempts = Column(Integer, default=0, nullable=False)
    hints_used = Column(Integer, default=0, nullable=False)

    # Rewards collected
    coins_earned = Column(Integer, default=0, nullable=False)
    xp_earned = Column(Integer, default=0, nullable=False)

    # Timestamps
    first_completed_at = Column(DateTime, default=None)
    last_played_at = Column(DateTime, default=None)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    profile = relationship("GameProfile", back_populates="level_progress")

    __table_args__ = ({"extend_existing": True},)


class GamePurchase(Base):
    """In-app purchase records."""

    __tablename__ = "game_purchases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("game_profiles.id"), nullable=False, index=True)

    # Purchase details
    product_id = Column(
        String, nullable=False, index=True
    )  # e.g., "coins_1000", "remove_ads", "premium_pack"
    product_type = Column(
        String, nullable=False
    )  # "coins", "powerup", "theme", "remove_ads", "premium"
    amount_paid = Column(Float, nullable=False)  # USD
    currency = Column(String, default="USD", nullable=False)

    # Platform
    platform = Column(String, nullable=False)  # "ios", "android", "web", "pc"
    transaction_id = Column(String, unique=True, nullable=False, index=True)
    receipt_data = Column(Text)  # Platform-specific receipt/verification data

    # Status
    is_verified = Column(Boolean, default=False, nullable=False)
    is_consumed = Column(Boolean, default=False, nullable=False)

    # Rewards granted
    coins_granted = Column(Integer, default=0, nullable=False)
    items_granted = Column(JSON, default=dict)  # Additional items granted

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    profile = relationship("GameProfile", back_populates="purchases")


class GameAchievement(Base):
    """User achievements/unlockables."""

    __tablename__ = "game_achievements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("game_profiles.id"), nullable=False, index=True)

    # Achievement details
    achievement_id = Column(
        String, nullable=False, index=True
    )  # e.g., "first_win", "level_100", "perfect_10"
    achievement_type = Column(
        String, nullable=False
    )  # "milestone", "skill", "collection", "special"
    title = Column(String, nullable=False)
    description = Column(Text)
    icon = Column(String)  # Icon identifier

    # Progress
    progress = Column(Integer, default=0, nullable=False)
    target = Column(Integer, nullable=False)
    is_unlocked = Column(Boolean, default=False, nullable=False)

    # Rewards
    coins_reward = Column(Integer, default=0, nullable=False)
    xp_reward = Column(Integer, default=0, nullable=False)
    items_reward = Column(JSON, default=dict)

    unlocked_at = Column(DateTime, default=None)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    profile = relationship("GameProfile", back_populates="achievements")

    __table_args__ = ({"extend_existing": True},)


class GameLeaderboard(Base):
    """Global leaderboard entries."""

    __tablename__ = "game_leaderboards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("game_profiles.id"), nullable=False, index=True)

    # Leaderboard type
    leaderboard_type = Column(
        String, nullable=False, index=True
    )  # "global", "weekly", "monthly", "level_100", etc.

    # Score
    score = Column(Integer, nullable=False, index=True)
    level_reached = Column(Integer, nullable=False)
    total_xp = Column(Integer, nullable=False)

    # Metadata
    game_metadata = Column(
        JSON, default=dict
    )  # Additional scoring data (renamed from 'metadata' to avoid SQLAlchemy conflict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    profile = relationship("GameProfile", backref="leaderboard_entries")

    __table_args__ = ({"extend_existing": True},)
