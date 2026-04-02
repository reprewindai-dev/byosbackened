"""Level generator for Neon Grid game."""

import random
import math
from typing import List, Dict, Any
from apps.api.schemas.game import LevelData
from core.game.level_validator import LevelValidator


class LevelGenerator:
    """Generates game levels with progressive difficulty."""

    def __init__(self):
        self.validator = LevelValidator()
        self.base_particle_count = 5
        self.max_particle_count = 50
        self.base_connections = 3
        self.max_connections = 25

    def generate_level(self, level_number: int) -> LevelData:
        """Generate a level configuration."""
        # Use validator to get proper parameters based on difficulty
        params = self.validator.calculate_required_parameters(level_number)
        difficulty_class = self.validator.classify_difficulty(level_number)
        difficulty_multiplier = self.validator.get_difficulty_multiplier(level_number)

        # Particle count based on difficulty
        particle_count = min(params["particle_count"], self.max_particle_count)

        # Connection count based on difficulty
        target_connections = min(params["connections"], self.max_connections)

        # Time limit (optional, becomes stricter at higher levels)
        time_limit = None
        if level_number > 100:
            # Start introducing time limits
            base_time = 300  # 5 minutes
            time_limit = max(60, base_time - (level_number - 100) * 2)

        # Generate particle positions (with params for proper spacing)
        particles = self._generate_particles(particle_count, level_number, params)

        # Generate required connections (ensure solvable)
        max_attempts = 10
        connections = None
        for attempt in range(max_attempts):
            test_connections = self._generate_connections(
                particle_count, target_connections, level_number
            )

            # Validate level is solvable
            test_level = {"particles": particles, "connections": test_connections}
            is_valid, error = self.validator.validate_level(test_level)

            if is_valid:
                connections = test_connections
                break

        if connections is None:
            # Fallback: create simple valid level
            connections = self._create_fallback_connections(particle_count, target_connections)

        # Calculate rewards
        rewards = self._calculate_rewards(level_number, target_connections, difficulty_class)

        return LevelData(
            level_number=level_number,
            particle_count=particle_count,
            target_connections=target_connections,
            time_limit=time_limit,
            particles=particles,
            connections=connections,
            difficulty_multiplier=difficulty_multiplier,
            rewards=rewards,
        )

    def _calculate_difficulty(self, level_number: int) -> float:
        """Calculate difficulty multiplier."""
        # Exponential difficulty curve
        base = 1.0
        growth = 1.05  # 5% increase per level
        return base * (growth**level_number)

    def _generate_particles(
        self, count: int, level_number: int, params: Dict[str, int] = None
    ) -> List[Dict[str, Any]]:
        """Generate particle positions and properties."""
        particles = []
        canvas_width = 800
        canvas_height = 600

        # Create a grid-based layout for easier connections
        grid_cols = int(math.ceil(math.sqrt(count)))
        grid_rows = int(math.ceil(count / grid_cols))
        cell_width = canvas_width / (grid_cols + 1)
        cell_height = canvas_height / (grid_rows + 1)

        # Add some randomization
        random.seed(level_number)  # Deterministic per level

        for i in range(count):
            col = i % grid_cols
            row = i // grid_cols

            # Base position on grid
            base_x = cell_width * (col + 1)
            base_y = cell_height * (row + 1)

            # Add random offset (respecting min_distance if params provided)
            if params:
                max_offset = min(cell_width * 0.3, params.get("min_distance", 50) / 2)
            else:
                max_offset = cell_width * 0.3
            offset_x = random.uniform(-max_offset, max_offset)
            offset_y = random.uniform(-max_offset, max_offset)

            x = max(50, min(canvas_width - 50, base_x + offset_x))
            y = max(50, min(canvas_height - 50, base_y + offset_y))

            # Particle properties
            particle = {
                "id": i,
                "x": x,
                "y": y,
                "radius": random.uniform(8, 15),
                "color": self._get_particle_color(i, level_number),
                "type": self._get_particle_type(i, level_number),
            }

            particles.append(particle)

        return particles

    def _get_particle_color(self, index: int, level_number: int) -> str:
        """Get particle color based on level."""
        colors = ["#ccff00", "#00ffcc", "#ff00cc", "#ffcc00", "#cc00ff"]

        # Higher levels get more color variety
        if level_number > 200:
            colors.extend(["#00ff00", "#ff0000", "#0000ff", "#ffffff"])

        return colors[index % len(colors)]

    def _get_particle_type(self, index: int, level_number: int) -> str:
        """Get particle type (affects gameplay)."""
        types = ["normal"]

        # Introduce special particles at higher levels
        if level_number > 50:
            types.append("anchor")  # Must connect first
        if level_number > 150:
            types.append("multiplier")  # Doubles score
        if level_number > 300:
            types.append("time_bonus")  # Adds time

        return random.choice(types)

    def _generate_connections(
        self, particle_count: int, target_connections: int, level_number: int
    ) -> List[List[int]]:
        """Generate required connections between particles."""
        random.seed(level_number * 1000)  # Different seed for connections

        # Ensure target_connections is at least enough for a spanning tree
        min_connections = particle_count - 1
        if target_connections < min_connections:
            target_connections = min_connections

        spanning_tree = []
        used_particles = set()
        available_particles = set(range(particle_count))

        # Start with first particle
        current = 0
        used_particles.add(current)
        available_particles.remove(current)

        # Build spanning tree (ensures all particles are connected)
        while available_particles:
            # Connect to a random unused particle
            target = random.choice(list(available_particles))
            conn = sorted([current, target])
            spanning_tree.append(conn)
            used_particles.add(target)
            available_particles.remove(target)
            # Next particle can be any used particle
            current = random.choice(list(used_particles))

        # Start with spanning tree
        connections = spanning_tree.copy()

        # Add additional connections to reach target
        attempts = 0
        max_attempts = 2000
        while len(connections) < target_connections and attempts < max_attempts:
            p1 = random.randint(0, particle_count - 1)
            p2 = random.randint(0, particle_count - 1)

            if p1 != p2:
                connection = sorted([p1, p2])
                if connection not in connections:
                    connections.append(connection)
            attempts += 1

        # Shuffle for variety, but ensure spanning tree connections remain
        # We'll shuffle only the extra connections
        if len(connections) > len(spanning_tree):
            extra = connections[len(spanning_tree) :]
            random.shuffle(extra)
            connections = spanning_tree + extra

        return connections[:target_connections]

    def _calculate_rewards(
        self, level_number: int, connections: int, difficulty_class: str
    ) -> Dict[str, int]:
        """Calculate rewards for completing level."""
        base_coins = 10
        base_xp = 50

        # Rewards scale with level and complexity
        coins = base_coins + (level_number * 2) + (connections * 5)
        xp = base_xp + (level_number * 3) + (connections * 10)

        # Difficulty multipliers
        multipliers = {
            "tutorial": 1.0,
            "easy": 1.2,
            "medium": 1.5,
            "hard": 2.0,
            "expert": 2.5,
            "master": 3.0,
            "legendary": 4.0,
        }

        multiplier = multipliers.get(difficulty_class, 1.5)
        coins = int(coins * multiplier)
        xp = int(xp * multiplier)

        # Special bonuses
        if level_number == 100:
            coins += 1000
            xp += 5000
        elif level_number == 500:
            coins += 5000
            xp += 25000
        elif level_number == 1000:
            coins += 10000
            xp += 50000

        return {"coins": coins, "xp": xp}

    def _create_fallback_connections(
        self, particle_count: int, target_connections: int
    ) -> List[List[int]]:
        """Create a simple valid connection pattern as fallback."""
        connections = []

        # Create spanning tree first (ensures all particles are connected)
        for i in range(particle_count - 1):
            connections.append([i, i + 1])

        # Add additional connections
        added = 0
        attempts = 0
        while len(connections) < target_connections and attempts < 1000:
            p1 = random.randint(0, particle_count - 1)
            p2 = random.randint(0, particle_count - 1)
            if p1 != p2:
                conn = sorted([p1, p2])
                if conn not in connections:
                    connections.append(conn)
                    added += 1
            attempts += 1

        return connections[:target_connections]
