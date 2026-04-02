"""Game API schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class GameProfileResponse(BaseModel):
    """Game profile response."""

    id: str
    user_id: str
    current_level: int
    total_xp: int
    player_level: int
    coins: int
    total_games_played: int
    total_wins: int
    total_losses: int
    best_streak: int
    current_streak: int
    unlocked_particles: List[str]
    unlocked_themes: List[str]
    unlocked_powerups: List[str]
    sound_enabled: bool
    music_enabled: bool
    vibration_enabled: bool
    created_at: datetime
    updated_at: datetime


class GameProfileUpdate(BaseModel):
    """Update game profile settings."""

    sound_enabled: Optional[bool] = None
    music_enabled: Optional[bool] = None
    vibration_enabled: Optional[bool] = None


class LevelData(BaseModel):
    """Level configuration data."""

    level_number: int
    particle_count: int
    target_connections: int
    time_limit: Optional[float] = None  # Seconds, None = no limit
    particles: List[Dict[str, Any]]  # Particle positions and properties
    connections: List[List[int]]  # Required connections (indices)
    difficulty_multiplier: float
    rewards: Dict[str, int]  # coins, xp


class LevelProgressResponse(BaseModel):
    """Level progress response."""

    id: str
    level_number: int
    is_completed: bool
    is_perfect: bool
    best_score: int
    best_time: Optional[float]
    attempts: int
    hints_used: int
    coins_earned: int
    xp_earned: int
    first_completed_at: Optional[datetime]
    last_played_at: Optional[datetime]


class LevelCompleteRequest(BaseModel):
    """Level completion submission."""

    level_number: int
    score: int
    time_taken: float
    moves: int
    hints_used: int
    is_perfect: bool
    connection_times: Optional[List[float]] = []  # Time between each connection
    connection_order: Optional[List[List[int]]] = []  # Order of connections made


class LevelCompleteResponse(BaseModel):
    """Level completion response."""

    success: bool
    coins_earned: int
    xp_earned: int
    level_up: bool
    new_player_level: Optional[int] = None
    achievements_unlocked: List[str] = []
    next_level_unlocked: bool


class PurchaseRequest(BaseModel):
    """In-app purchase request."""

    product_id: str
    platform: str  # "ios", "android", "web", "pc"
    transaction_id: str
    receipt_data: Optional[str] = None
    amount_paid: float
    currency: str = "USD"


class PurchaseResponse(BaseModel):
    """Purchase response."""

    success: bool
    purchase_id: str
    coins_granted: int
    items_granted: Dict[str, Any]
    new_coin_balance: int


class AchievementResponse(BaseModel):
    """Achievement response."""

    id: str
    achievement_id: str
    achievement_type: str
    title: str
    description: Optional[str]
    icon: Optional[str]
    progress: int
    target: int
    is_unlocked: bool
    coins_reward: int
    xp_reward: int
    items_reward: Dict[str, Any]
    unlocked_at: Optional[datetime]


class LeaderboardEntry(BaseModel):
    """Leaderboard entry."""

    rank: int
    profile_id: str
    user_name: Optional[str]
    score: int
    level_reached: int
    total_xp: int


class LeaderboardResponse(BaseModel):
    """Leaderboard response."""

    leaderboard_type: str
    entries: List[LeaderboardEntry]
    user_rank: Optional[int]
    total_players: int
