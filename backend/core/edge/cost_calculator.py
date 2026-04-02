"""Edge cost calculator - calculate costs per region (data transfer, compute)."""
from typing import Dict, Optional
from decimal import Decimal
from core.edge.region_manager import RegionManager
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
region_manager = RegionManager()


class EdgeCostCalculator:
    """
    Calculate costs per region.
    
    Considers:
    - Compute costs (varies by region)
    - Data transfer costs (edge -> central -> edge)
    - Storage costs (if applicable)
    """

    # Regional compute costs (per hour, normalized)
    REGIONAL_COMPUTE_COSTS = {
        "us-east": Decimal("0.10"),  # Base cost
        "eu-west": Decimal("0.12"),   # Slightly higher
        "asia-pacific": Decimal("0.11"),
    }

    # Data transfer costs (per GB)
    DATA_TRANSFER_COSTS = {
        "us-east": Decimal("0.01"),   # Within region
        "eu-west": Decimal("0.01"),
        "asia-pacific": Decimal("0.01"),
        "cross-region": Decimal("0.05"),  # Between regions
    }

    def calculate_region_cost(
        self,
        region: str,
        operation_type: str,
        input_size_bytes: int,
        compute_time_seconds: float = 1.0,
        data_transfer_bytes: Optional[int] = None,
    ) -> Dict[str, Decimal]:
        """
        Calculate total cost for operation in region.
        
        Returns breakdown of costs.
        """
        if region not in region_manager.REGIONS:
            logger.warning(f"Unknown region: {region}")
            region = "us-east"  # Default
        
        # Compute cost (based on compute time)
        compute_cost_per_hour = self.REGIONAL_COMPUTE_COSTS.get(region, Decimal("0.10"))
        compute_cost = (Decimal(str(compute_time_seconds)) / Decimal("3600")) * compute_cost_per_hour
        
        # Data transfer cost
        if data_transfer_bytes is None:
            # Estimate: input + output (assume 2x input for output)
            data_transfer_bytes = input_size_bytes * 2
        
        # Check if cross-region transfer
        # For now, assume within-region (can be enhanced)
        transfer_cost_per_gb = self.DATA_TRANSFER_COSTS.get(region, Decimal("0.01"))
        transfer_cost = (Decimal(str(data_transfer_bytes)) / Decimal(1024**3)) * transfer_cost_per_gb
        
        total_cost = compute_cost + transfer_cost
        
        return {
            "compute_cost": compute_cost,
            "transfer_cost": transfer_cost,
            "total_cost": total_cost,
            "region": region,
        }

    def compare_region_costs(
        self,
        operation_type: str,
        input_size_bytes: int,
        compute_time_seconds: float = 1.0,
        source_region: Optional[str] = None,
    ) -> Dict[str, Dict[str, Decimal]]:
        """
        Compare costs across all regions.
        
        Useful for finding cheapest region for operation.
        """
        costs = {}
        
        for region in region_manager.get_regions():
            # Calculate transfer cost if source region specified
            data_transfer_bytes = None
            if source_region and source_region != region:
                # Cross-region transfer
                data_transfer_bytes = input_size_bytes * 2  # Input + output
                transfer_cost_per_gb = self.DATA_TRANSFER_COSTS["cross-region"]
            else:
                # Within region
                data_transfer_bytes = input_size_bytes * 2
                transfer_cost_per_gb = self.DATA_TRANSFER_COSTS.get(region, Decimal("0.01"))
            
            region_cost = self.calculate_region_cost(
                region=region,
                operation_type=operation_type,
                input_size_bytes=input_size_bytes,
                compute_time_seconds=compute_time_seconds,
                data_transfer_bytes=data_transfer_bytes,
            )
            
            costs[region] = region_cost
        
        return costs

    def get_cheapest_region(
        self,
        operation_type: str,
        input_size_bytes: int,
        compute_time_seconds: float = 1.0,
        source_region: Optional[str] = None,
    ) -> str:
        """
        Get cheapest region for operation.
        
        Considers compute + transfer costs.
        """
        costs = self.compare_region_costs(
            operation_type=operation_type,
            input_size_bytes=input_size_bytes,
            compute_time_seconds=compute_time_seconds,
            source_region=source_region,
        )
        
        if not costs:
            return "us-east"  # Default
        
        cheapest_region = min(
            costs.keys(),
            key=lambda r: costs[r]["total_cost"]
        )
        
        return cheapest_region

    def estimate_data_transfer_cost(
        self,
        from_region: str,
        to_region: str,
        data_size_bytes: int,
    ) -> Decimal:
        """
        Estimate data transfer cost between regions.
        
        Returns cost in dollars.
        """
        if from_region == to_region:
            # Within region
            cost_per_gb = self.DATA_TRANSFER_COSTS.get(from_region, Decimal("0.01"))
        else:
            # Cross-region
            cost_per_gb = self.DATA_TRANSFER_COSTS["cross-region"]
        
        cost = (Decimal(str(data_size_bytes)) / Decimal(1024**3)) * cost_per_gb
        return cost


# Global edge cost calculator
_edge_cost_calculator = EdgeCostCalculator()


def get_edge_cost_calculator() -> EdgeCostCalculator:
    """Get global edge cost calculator instance."""
    return _edge_cost_calculator
