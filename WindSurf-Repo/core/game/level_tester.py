"""Test all levels to ensure they're solvable."""

from core.game.level_generator import LevelGenerator
from core.game.level_validator import LevelValidator
from typing import List, Dict, Tuple
import json


class LevelTester:
    """Tests all levels for validity and solvability."""

    def __init__(self):
        self.generator = LevelGenerator()
        self.validator = LevelValidator()

    def test_all_levels(self, start: int = 0, end: int = 1000) -> Dict[str, Any]:
        """Test all levels from start to end."""
        results = {
            "total": end - start + 1,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "difficulty_distribution": {},
        }

        print(f"Testing levels {start} to {end}...")

        for level_num in range(start, end + 1):
            try:
                # Generate level
                level_data = self.generator.generate_level(level_num)

                # Validate
                is_valid, error = self.validator.validate_level(
                    {"particles": level_data.particles, "connections": level_data.connections}
                )

                if is_valid:
                    results["passed"] += 1
                    difficulty = self.validator.classify_difficulty(level_num)
                    results["difficulty_distribution"][difficulty] = (
                        results["difficulty_distribution"].get(difficulty, 0) + 1
                    )
                else:
                    results["failed"] += 1
                    results["errors"].append({"level": level_num, "error": error})
                    print(f"[FAIL] Level {level_num}: {error}")

                # Progress indicator
                if level_num % 100 == 0:
                    print(
                        f"Progress: {level_num}/{end} ({results['passed']} passed, {results['failed']} failed)"
                    )

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"level": level_num, "error": str(e)})
                print(f"[ERROR] Level {level_num}: Exception - {e}")

        print(f"\n[COMPLETE] Testing complete!")
        print(f"Passed: {results['passed']}/{results['total']}")
        print(f"Failed: {results['failed']}/{results['total']}")

        return results

    def test_level_range(self, start: int, end: int) -> List[Dict]:
        """Test a specific range of levels."""
        results = []
        for level_num in range(start, end + 1):
            try:
                level_data = self.generator.generate_level(level_num)
                is_valid, error = self.validator.validate_level(
                    {"particles": level_data.particles, "connections": level_data.connections}
                )
                results.append(
                    {
                        "level": level_num,
                        "valid": is_valid,
                        "error": error if not is_valid else None,
                        "particle_count": len(level_data.particles),
                        "connection_count": len(level_data.connections),
                        "difficulty": self.validator.classify_difficulty(level_num),
                    }
                )
            except Exception as e:
                results.append({"level": level_num, "valid": False, "error": str(e)})
        return results
