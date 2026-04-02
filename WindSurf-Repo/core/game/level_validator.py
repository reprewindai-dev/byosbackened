"""Level validator - ensures all levels are solvable and properly classified."""

from typing import List, Dict, Tuple, Any
import math


class LevelValidator:
    """Validates that levels are solvable and properly classified."""

    def __init__(self):
        self.difficulty_classes = {
            "tutorial": (0, 10),
            "easy": (11, 50),
            "medium": (51, 200),
            "hard": (201, 500),
            "expert": (501, 800),
            "master": (801, 950),
            "legendary": (951, 1000),
        }

    def validate_level(self, level_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate a single level is solvable."""
        particles = level_data.get("particles", [])
        connections = level_data.get("connections", [])

        if not particles:
            return False, "No particles"

        if not connections:
            return False, "No connections required"

        # Check all connection indices are valid
        max_particle_index = len(particles) - 1
        for conn in connections:
            if len(conn) != 2:
                return False, f"Invalid connection format: {conn}"
            if conn[0] < 0 or conn[0] > max_particle_index:
                return False, f"Invalid particle index: {conn[0]}"
            if conn[1] < 0 or conn[1] > max_particle_index:
                return False, f"Invalid particle index: {conn[1]}"
            if conn[0] == conn[1]:
                return False, f"Connection to self: {conn}"

        # Check if level is solvable (all particles reachable)
        if not self._is_solvable(particles, connections):
            return False, "Level is not solvable - particles not connected"

        return True, "Valid"

    def _is_solvable(self, particles: List[Dict], connections: List[List[int]]) -> bool:
        """Check if all particles are reachable through connections."""
        if not particles:
            return False

        # Build adjacency graph
        graph = {i: [] for i in range(len(particles))}
        for conn in connections:
            graph[conn[0]].append(conn[1])
            graph[conn[1]].append(conn[0])

        # BFS to check connectivity
        visited = set()
        queue = [0]
        visited.add(0)

        while queue:
            node = queue.pop(0)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # All particles must be reachable
        return len(visited) == len(particles)

    def classify_difficulty(self, level_number: int) -> str:
        """Classify level difficulty."""
        for class_name, (min_level, max_level) in self.difficulty_classes.items():
            if min_level <= level_number <= max_level:
                return class_name
        return "medium"

    def get_difficulty_multiplier(self, level_number: int) -> float:
        """Get difficulty multiplier based on level."""
        base = 1.0

        if level_number <= 10:
            return base  # Tutorial
        elif level_number <= 50:
            return base * (1 + (level_number - 10) * 0.02)  # Easy
        elif level_number <= 200:
            return base * (1.8 + (level_number - 50) * 0.015)  # Medium
        elif level_number <= 500:
            return base * (4.05 + (level_number - 200) * 0.01)  # Hard
        elif level_number <= 800:
            return base * (7.05 + (level_number - 500) * 0.008)  # Expert
        elif level_number <= 950:
            return base * (9.45 + (level_number - 800) * 0.005)  # Master
        else:
            return base * (10.2 + (level_number - 950) * 0.01)  # Legendary

    def calculate_required_parameters(self, level_number: int) -> Dict[str, int]:
        """Calculate required parameters for a level based on difficulty."""
        difficulty = self.classify_difficulty(level_number)

        if difficulty == "tutorial":
            return {
                "particle_count": 4 + level_number,
                "connections": 2 + level_number,
                "min_distance": 80,
                "max_distance": 200,
            }
        elif difficulty == "easy":
            return {
                "particle_count": 6 + int(level_number / 5),
                "connections": 4 + int(level_number / 3),
                "min_distance": 70,
                "max_distance": 250,
            }
        elif difficulty == "medium":
            return {
                "particle_count": 10 + int(level_number / 10),
                "connections": 6 + int(level_number / 8),
                "min_distance": 60,
                "max_distance": 300,
            }
        elif difficulty == "hard":
            return {
                "particle_count": 15 + int(level_number / 15),
                "connections": 10 + int(level_number / 12),
                "min_distance": 50,
                "max_distance": 350,
            }
        elif difficulty == "expert":
            return {
                "particle_count": 20 + int(level_number / 20),
                "connections": 15 + int(level_number / 15),
                "min_distance": 40,
                "max_distance": 400,
            }
        elif difficulty == "master":
            return {
                "particle_count": 25 + int(level_number / 25),
                "connections": 20 + int(level_number / 20),
                "min_distance": 35,
                "max_distance": 450,
            }
        else:  # legendary
            return {
                "particle_count": 30 + int(level_number / 30),
                "connections": 25 + int(level_number / 25),
                "min_distance": 30,
                "max_distance": 500,
            }
