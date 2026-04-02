"""Anti-cheat detection system."""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import statistics


class AntiCheatDetector:
    """Detects AI assistance and cheating patterns."""

    def __init__(self):
        self.suspicious_patterns = []

    def analyze_completion(
        self,
        level_number: int,
        time_taken: float,
        moves: int,
        hints_used: int,
        connection_times: List[float],
        connection_order: List[Tuple[int, int]],
    ) -> Dict[str, Any]:
        """Analyze completion for suspicious patterns."""
        analysis = {"suspicious": False, "confidence": 0.0, "flags": [], "human_score": 100.0}

        # Flag 1: Too fast (AI-like speed)
        expected_min_time = self._calculate_min_time(level_number, moves)
        if time_taken < expected_min_time * 0.3:
            analysis["flags"].append("suspiciously_fast")
            analysis["confidence"] += 30
            analysis["human_score"] -= 20

        # Flag 2: Perfect moves (no mistakes)
        optimal_moves = self._calculate_optimal_moves(level_number)
        if moves == optimal_moves and level_number > 50:
            analysis["flags"].append("perfect_moves")
            analysis["confidence"] += 20
            analysis["human_score"] -= 15

        # Flag 3: Consistent timing (AI-like precision)
        if len(connection_times) > 5:
            timing_variance = statistics.stdev(connection_times) if len(connection_times) > 1 else 0
            if timing_variance < 0.1:  # Too consistent
                analysis["flags"].append("consistent_timing")
                analysis["confidence"] += 15
                analysis["human_score"] -= 10

        # Flag 4: No hesitation (immediate connections)
        if connection_times and all(t < 0.5 for t in connection_times):
            analysis["flags"].append("no_hesitation")
            analysis["confidence"] += 25
            analysis["human_score"] -= 25

        # Flag 5: Optimal path (always shortest)
        if self._is_optimal_path(connection_order, level_number):
            analysis["flags"].append("optimal_path")
            analysis["confidence"] += 20
            analysis["human_score"] -= 15

        # Flag 6: No exploration (direct to solution)
        if len(set(connection_order)) == len(connection_order) and level_number > 100:
            # No retries, no exploration
            analysis["flags"].append("no_exploration")
            analysis["confidence"] += 15
            analysis["human_score"] -= 10

        # Human indicators (increase human_score)
        if hints_used > 0:
            analysis["human_score"] += 5  # Humans use hints

        if moves > optimal_moves * 1.5:
            analysis["human_score"] += 10  # Humans make mistakes

        if time_taken > expected_min_time * 2:
            analysis["human_score"] += 5  # Humans take time to think

        # Calculate final scores
        analysis["confidence"] = min(100, analysis["confidence"])
        analysis["human_score"] = max(0, min(100, analysis["human_score"]))

        if analysis["confidence"] > 50:
            analysis["suspicious"] = True

        return analysis

    def _calculate_min_time(self, level_number: int, moves: int) -> float:
        """Calculate minimum expected time for human completion."""
        base_time = 5.0  # Base thinking time
        move_time = moves * 1.5  # Time per move
        difficulty_time = level_number * 0.1  # Difficulty multiplier
        return base_time + move_time + difficulty_time

    def _calculate_optimal_moves(self, level_number: int) -> int:
        """Calculate optimal number of moves."""
        # Optimal is exactly the number of required connections
        return max(3, int(level_number / 20) + 3)

    def _is_optimal_path(self, connection_order: List[Tuple[int, int]], level_number: int) -> bool:
        """Check if path is too optimal (AI-like)."""
        if level_number < 50:
            return False  # Early levels can be optimal

        # Check if connections follow a logical pattern
        # Humans tend to explore, AI goes direct
        if len(connection_order) < 3:
            return False

        # Check for exploration patterns (humans try different things)
        unique_starts = len(set(c[0] for c in connection_order))
        if unique_starts == len(connection_order):
            return True  # Always starting from new particle (suspicious)

        return False

    def verify_human_completion(self, analysis: Dict[str, Any]) -> bool:
        """Verify if completion appears human."""
        return analysis["human_score"] >= 50 and not analysis["suspicious"]

    def get_completion_bonus(self, analysis: Dict[str, Any], level_number: int) -> Dict[str, int]:
        """Calculate bonus rewards for verified human completion."""
        base_coins = 10 + (level_number * 2)
        base_xp = 50 + (level_number * 3)

        bonus_multiplier = 1.0

        # Human completion bonus
        if analysis["human_score"] >= 70:
            bonus_multiplier = 1.5  # 50% bonus for human play
        elif analysis["human_score"] >= 50:
            bonus_multiplier = 1.2  # 20% bonus

        # Perfect completion bonus (but verified human)
        if not analysis["suspicious"] and analysis["human_score"] >= 60:
            bonus_multiplier *= 1.3  # Additional 30% for perfect human play

        return {
            "coins": int(base_coins * bonus_multiplier),
            "xp": int(base_xp * bonus_multiplier),
            "human_bonus": bonus_multiplier > 1.0,
        }
