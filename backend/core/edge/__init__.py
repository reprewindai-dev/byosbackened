"""Edge-aware architecture - automatic placement decisions."""
from core.edge.region_manager import RegionManager
from core.edge.routing import EdgeRouter
from core.edge.placement_learner import PlacementLearner

__all__ = [
    "RegionManager",
    "EdgeRouter",
    "PlacementLearner",
]
