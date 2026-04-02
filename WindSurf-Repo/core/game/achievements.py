"""Achievement system for the game."""

from sqlalchemy.orm import Session
from db.models.game import GameProfile, GameAchievement
from datetime import datetime
from typing import List


class AchievementManager:
    """Manages achievement unlocking and tracking."""

    # Achievement definitions
    ACHIEVEMENTS = {
        "first_win": {
            "type": "milestone",
            "title": "First Victory",
            "description": "Complete your first level",
            "icon": "trophy",
            "target": 1,
            "coins": 50,
            "xp": 100,
        },
        "level_10": {
            "type": "milestone",
            "title": "Rising Star",
            "description": "Reach level 10",
            "icon": "star",
            "target": 10,
            "coins": 100,
            "xp": 200,
        },
        "level_50": {
            "type": "milestone",
            "title": "Halfway Hero",
            "description": "Reach level 50",
            "icon": "medal",
            "target": 50,
            "coins": 500,
            "xp": 1000,
        },
        "level_100": {
            "type": "milestone",
            "title": "Centurion",
            "description": "Reach level 100",
            "icon": "crown",
            "target": 100,
            "coins": 1000,
            "xp": 2000,
        },
        "level_500": {
            "type": "milestone",
            "title": "Master Builder",
            "description": "Reach level 500",
            "icon": "diamond",
            "target": 500,
            "coins": 5000,
            "xp": 10000,
        },
        "level_1000": {
            "type": "milestone",
            "title": "Legend",
            "description": "Complete all 1000 levels",
            "icon": "legend",
            "target": 1000,
            "coins": 10000,
            "xp": 50000,
        },
        "complete_all_1000_human": {
            "type": "special",
            "title": "True Legend",
            "description": "Complete all 1000 levels without AI assistance",
            "icon": "legend_gold",
            "target": 1000,
            "coins": 50000,
            "xp": 100000,
        },
        "human_master": {
            "type": "skill",
            "title": "Human Master",
            "description": "Complete 100 levels with verified human play",
            "icon": "human",
            "target": 100,
            "coins": 5000,
            "xp": 10000,
        },
        "perfect_10": {
            "type": "skill",
            "title": "Perfectionist",
            "description": "Get perfect score on 10 levels",
            "icon": "perfect",
            "target": 10,
            "coins": 500,
            "xp": 1000,
        },
        "perfect_50": {
            "type": "skill",
            "title": "Flawless",
            "description": "Get perfect score on 50 levels",
            "icon": "perfect_gold",
            "target": 50,
            "coins": 2500,
            "xp": 5000,
        },
        "streak_10": {
            "type": "skill",
            "title": "On Fire",
            "description": "Win 10 levels in a row",
            "icon": "flame",
            "target": 10,
            "coins": 300,
            "xp": 600,
        },
        "streak_50": {
            "type": "skill",
            "title": "Unstoppable",
            "description": "Win 50 levels in a row",
            "icon": "flame_gold",
            "target": 50,
            "coins": 2000,
            "xp": 4000,
        },
        "no_hints": {
            "type": "skill",
            "title": "Independent",
            "description": "Complete 20 levels without hints",
            "icon": "brain",
            "target": 20,
            "coins": 400,
            "xp": 800,
        },
        "speed_demon": {
            "type": "skill",
            "title": "Speed Demon",
            "description": "Complete 10 levels in under 30 seconds",
            "icon": "lightning",
            "target": 10,
            "coins": 600,
            "xp": 1200,
        },
    }

    def __init__(self, db: Session, profile: GameProfile):
        self.db = db
        self.profile = profile

    def check_and_unlock_achievements(
        self, level_number: int, score: int, is_perfect: bool
    ) -> List[str]:
        """Check and unlock achievements based on current progress."""
        unlocked = []

        # Check level-based achievements
        if level_number >= 10:
            self._check_achievement("level_10", level_number)
        if level_number >= 50:
            self._check_achievement("level_50", level_number)
        if level_number >= 100:
            self._check_achievement("level_100", level_number)
        if level_number >= 500:
            self._check_achievement("level_500", level_number)
        if level_number >= 1000:
            self._check_achievement("level_1000", level_number)

        # Check first win
        if level_number == 1:
            achievement = self._check_achievement("first_win", 1)
            if achievement:
                unlocked.append("first_win")

        # Check perfect scores
        if is_perfect:
            perfect_count = (
                self.db.query(GameAchievement)
                .filter(
                    GameAchievement.profile_id == self.profile.id,
                    GameAchievement.achievement_id == "perfect_10",
                )
                .first()
            )

            if perfect_count:
                # Update progress
                perfect_count.progress += 1
                if perfect_count.progress >= perfect_count.target and not perfect_count.is_unlocked:
                    self._unlock_achievement(perfect_count)
                    unlocked.append("perfect_10")
            else:
                # Create new achievement
                achievement = self._create_achievement("perfect_10", 1)
                if achievement and achievement.is_unlocked:
                    unlocked.append("perfect_10")

        # Check streaks
        if self.profile.current_streak >= 10:
            achievement = self._check_achievement("streak_10", self.profile.current_streak)
            if achievement and achievement.is_unlocked:
                unlocked.append("streak_10")

        if self.profile.current_streak >= 50:
            achievement = self._check_achievement("streak_50", self.profile.current_streak)
            if achievement and achievement.is_unlocked:
                unlocked.append("streak_50")

        self.db.commit()
        return unlocked

    def _check_achievement(self, achievement_id: str, progress_value: int) -> GameAchievement:
        """Check if achievement should be unlocked."""
        achievement_def = self.ACHIEVEMENTS.get(achievement_id)
        if not achievement_def:
            return None

        # Get or create achievement
        achievement = (
            self.db.query(GameAchievement)
            .filter(
                GameAchievement.profile_id == self.profile.id,
                GameAchievement.achievement_id == achievement_id,
            )
            .first()
        )

        if not achievement:
            achievement = self._create_achievement(achievement_id, progress_value)
        else:
            # Update progress
            achievement.progress = max(achievement.progress, progress_value)
            if achievement.progress >= achievement.target and not achievement.is_unlocked:
                self._unlock_achievement(achievement)

        return achievement

    def _create_achievement(self, achievement_id: str, initial_progress: int) -> GameAchievement:
        """Create a new achievement entry."""
        achievement_def = self.ACHIEVEMENTS[achievement_id]

        achievement = GameAchievement(
            profile_id=self.profile.id,
            achievement_id=achievement_id,
            achievement_type=achievement_def["type"],
            title=achievement_def["title"],
            description=achievement_def["description"],
            icon=achievement_def["icon"],
            progress=initial_progress,
            target=achievement_def["target"],
            coins_reward=achievement_def["coins"],
            xp_reward=achievement_def["xp"],
            is_unlocked=initial_progress >= achievement_def["target"],
        )

        if achievement.is_unlocked:
            achievement.unlocked_at = datetime.utcnow()
            self.profile.coins += achievement.coins_reward
            self.profile.total_xp += achievement.xp_reward

        self.db.add(achievement)
        return achievement

    def _unlock_achievement(self, achievement: GameAchievement):
        """Unlock an achievement and grant rewards."""
        if achievement.is_unlocked:
            return

        achievement.is_unlocked = True
        achievement.unlocked_at = datetime.utcnow()

        # Grant rewards
        self.profile.coins += achievement.coins_reward
        self.profile.total_xp += achievement.xp_reward
