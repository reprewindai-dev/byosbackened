"""Progression calculator for game rewards and leveling."""

from typing import Dict


class ProgressionCalculator:
    """Calculates XP, level ups, and rewards."""

    def __init__(self):
        self.base_xp_per_level = 100
        self.xp_multiplier = 1.15  # 15% increase per level

    def calculate_level_rewards(
        self, level_number: int, score: int, time_taken: float, is_perfect: bool, hints_used: int
    ) -> Dict[str, int]:
        """Calculate rewards for completing a level."""
        base_coins = 10
        base_xp = 50

        # Base rewards scale with level
        coins = base_coins + (level_number * 2)
        xp = base_xp + (level_number * 3)

        # Score multiplier (0.5x to 2.0x)
        score_multiplier = 0.5 + (score / 10000) * 1.5
        coins = int(coins * score_multiplier)
        xp = int(xp * score_multiplier)

        # Time bonus (faster = more rewards)
        if time_taken > 0:
            time_bonus = max(0.5, 2.0 - (time_taken / 300))  # Up to 2x for very fast
            coins = int(coins * time_bonus)
            xp = int(xp * time_bonus)

        # Perfect bonus
        if is_perfect:
            coins = int(coins * 1.5)
            xp = int(xp * 2.0)

        # Hint penalty
        hint_penalty = max(0.5, 1.0 - (hints_used * 0.1))
        coins = int(coins * hint_penalty)
        xp = int(xp * hint_penalty)

        return {"coins": max(1, coins), "xp": max(1, xp)}

    def calculate_player_level(self, total_xp: int) -> int:
        """Calculate player level from total XP."""
        level = 1
        xp_required = 0

        while xp_required <= total_xp:
            level_xp = int(self.base_xp_per_level * (self.xp_multiplier ** (level - 1)))
            xp_required += level_xp

            if xp_required <= total_xp:
                level += 1
            else:
                break

        return level

    def get_xp_for_next_level(self, current_level: int) -> int:
        """Get XP required for next level."""
        return int(self.base_xp_per_level * (self.xp_multiplier ** (current_level - 1)))
