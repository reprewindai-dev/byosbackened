"""Automatic edge routing - decides where code runs."""
from typing import Optional, Dict
from decimal import Decimal
from core.edge.region_manager import RegionManager
from core.edge.placement_learner import PlacementLearner
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
region_manager = RegionManager()
placement_learner = PlacementLearner()


class EdgeRouter:
    """
    Automatic edge routing - decides where code runs.
    
    Edge-aware by default - no user configuration needed.
    Learns optimal placement over time.
    """

    def select_region(
        self,
        workspace_id: str,
        operation_type: str,
        user_region: Optional[str] = None,  # From geo-IP
        data_residency: Optional[str] = None,  # From workspace settings
    ) -> str:
        """
        Select optimal region automatically.
        
        Considers:
        - User geography (route to nearest)
        - Data residency requirements (GDPR, etc.)
        - Learned patterns (which operations benefit from edge)
        - Cost (data transfer costs)
        """
        # Data residency takes priority
        if data_residency:
            # Map data residency to region
            region_map = {
                "eu": "eu-west",
                "us": "us-east",
                "asia": "asia-pacific",
            }
            if data_residency.lower() in region_map:
                selected = region_map[data_residency.lower()]
                logger.debug(f"Selected {selected} for data residency: {data_residency}")
                return selected
        
        # Try learned placement
        learned_region = placement_learner.get_optimal_region(
            workspace_id=workspace_id,
            operation_type=operation_type,
        )
        
        if learned_region:
            logger.debug(f"Selected {learned_region} from learned patterns")
            return learned_region
        
        # Fallback: route to nearest region based on user geography
        if user_region:
            # Simple mapping (can be enhanced with geo-IP)
            if user_region.lower() in ["eu", "europe"]:
                return "eu-west"
            elif user_region.lower() in ["asia", "apac"]:
                return "asia-pacific"
            else:
                return "us-east"  # Default
        
        # Default: US East
        return "us-east"

    def should_use_edge(
        self,
        workspace_id: str,
        operation_type: str,
        input_size_bytes: int,
    ) -> bool:
        """
        Decide if operation should run at edge.
        
        Learns over time which operations benefit from edge.
        """
        # Media/real-time operations benefit from edge
        if operation_type in ["transcribe", "extract"]:
            # Large files benefit from edge (lower latency)
            if input_size_bytes > 10_000_000:  # > 10MB
                return True
        
        # Check learned patterns
        return placement_learner.should_use_edge(
            workspace_id=workspace_id,
            operation_type=operation_type,
        )

    def update_placement_outcome(
        self,
        workspace_id: str,
        operation_type: str,
        region: str,
        latency_ms: int,
        cost: Decimal,
        success: bool,
    ):
        """
        Update placement learner with outcome.
        
        This is the learning loop - improves placement decisions over time.
        """
        placement_learner.update_outcome(
            workspace_id=workspace_id,
            operation_type=operation_type,
            region=region,
            latency_ms=latency_ms,
            cost=cost,
            success=success,
        )


# Global edge router
_edge_router = EdgeRouter()


def get_edge_router() -> EdgeRouter:
    """Get global edge router instance."""
    return _edge_router
