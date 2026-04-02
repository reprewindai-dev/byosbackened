"""Environmental decision-making service for carbon-aware routing."""
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio
from enum import Enum


class Region(str, Enum):
    """Geographic regions for carbon intensity."""
    US_WEST = "us-west"
    US_EAST = "us-east"
    EU_WEST = "eu-west"
    EU_EAST = "eu-east"
    ASIA_PACIFIC = "asia-pacific"
    SOUTH_AMERICA = "south-america"
    AFRICA = "africa"


class Zone(str, Enum):
    """Availability zones within regions."""
    A = "a"
    B = "b"
    C = "c"
    D = "d"


class RoutingDecision(BaseModel):
    """A routing decision with environmental impact."""
    id: Optional[str] = Field(None, description="Decision ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Decision timestamp")

    workspace_id: Optional[str] = Field(None, description="Workspace identifier")
    operation: Optional[str] = Field(None, description="Operation type")

    workload_name: Optional[str] = Field(None, description="Workload name")
    operation_name: Optional[str] = Field(None, description="Operation name")

    # Geographic decisions
    baseline_region: Optional[Region] = Field(None, description="Baseline region")
    chosen_region: Optional[Region] = Field(None, description="Chosen region for routing")

    baseline_zone: Optional[Zone] = Field(None, description="Baseline zone")
    chosen_zone: Optional[Zone] = Field(None, description="Chosen zone for routing")

    # Performance metrics
    request_count: Optional[int] = Field(None, description="Number of requests")

    # Carbon intensity (grams CO2 per kWh)
    carbon_intensity_baseline: Optional[float] = Field(None, description="Baseline carbon intensity")
    carbon_intensity_chosen: Optional[float] = Field(None, description="Chosen carbon intensity")

    # Energy consumption
    estimated_energy_kwh: Optional[float] = Field(None, description="Estimated energy consumption in kWh")

    # CO2 emissions
    co2_baseline_grams: Optional[float] = Field(None, description="Baseline CO2 emissions in grams")
    co2_chosen_grams: Optional[float] = Field(None, description="Chosen CO2 emissions in grams")

    # Performance
    latency_estimate_ms: Optional[int] = Field(None, description="Estimated latency in milliseconds")
    latency_actual_ms: Optional[int] = Field(None, description="Actual latency in milliseconds")

    # Decision metadata
    reason: Optional[str] = Field(None, description="Reason for the decision")
    fallback_used: bool = Field(False, description="Whether fallback was used")
    data_freshness_seconds: Optional[int] = Field(None, description="How fresh the data is")

    # Additional metadata
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EnvironmentalService:
    """Service for carbon-aware routing and environmental decision-making."""

    def __init__(self):
        # Carbon intensity data (grams CO2 per kWh) - real-world averages
        self.carbon_intensity_data = {
            Region.US_WEST: 200,  # Lower carbon due to renewables
            Region.US_EAST: 350,  # Higher due to coal
            Region.EU_WEST: 150,  # Very low due to nuclear/renewables
            Region.EU_EAST: 250,  # Moderate
            Region.ASIA_PACIFIC: 400,  # Higher due to coal-heavy grid
            Region.SOUTH_AMERICA: 180,  # Moderate, improving renewables
            Region.AFRICA: 450,  # High due to limited infrastructure
        }

        # Latency estimates between regions (milliseconds)
        self.latency_matrix = {
            (Region.US_WEST, Region.US_WEST): 10,
            (Region.US_WEST, Region.US_EAST): 80,
            (Region.US_WEST, Region.EU_WEST): 150,
            (Region.US_WEST, Region.ASIA_PACIFIC): 200,
            (Region.US_EAST, Region.EU_WEST): 70,
            (Region.EU_WEST, Region.ASIA_PACIFIC): 250,
        }

    async def make_routing_decision(
        self,
        workload_name: str,
        operation_name: str,
        baseline_region: Region,
        request_count: int = 1,
        energy_estimate_kwh: float = 0.1,
        workspace_id: Optional[str] = None
    ) -> RoutingDecision:
        """Make a carbon-aware routing decision."""

        # Get carbon intensity for baseline
        baseline_carbon = self.carbon_intensity_data.get(baseline_region, 300)

        # Find the most environmentally friendly region
        chosen_region = min(
            self.carbon_intensity_data.keys(),
            key=lambda r: self.carbon_intensity_data[r]
        )
        chosen_carbon = self.carbon_intensity_data[chosen_region]

        # Calculate CO2 impact
        co2_baseline = baseline_carbon * energy_estimate_kwh * request_count
        co2_chosen = chosen_carbon * energy_estimate_kwh * request_count

        # Estimate latency
        latency_key = (baseline_region, chosen_region)
        latency_estimate = self.latency_matrix.get(latency_key, 100)

        # Add some randomness to simulate real-world variation
        import random
        latency_actual = int(latency_estimate * random.uniform(0.8, 1.3))

        # Determine zones (simple distribution)
        baseline_zone = Zone.A
        chosen_zone = random.choice([Zone.A, Zone.B, Zone.C])

        # Decision reason
        savings = co2_baseline - co2_chosen
        reason = f"Chose {chosen_region.value} over {baseline_region.value} for {savings:.1f}g CO2 savings"

        return RoutingDecision(
            workspace_id=workspace_id,
            operation=operation_name,
            workload_name=workload_name,
            operation_name=operation_name,
            baseline_region=baseline_region,
            chosen_region=chosen_region,
            baseline_zone=baseline_zone,
            chosen_zone=chosen_zone,
            request_count=request_count,
            carbon_intensity_baseline=baseline_carbon,
            carbon_intensity_chosen=chosen_carbon,
            estimated_energy_kwh=energy_estimate_kwh,
            co2_baseline_grams=co2_baseline,
            co2_chosen_grams=co2_chosen,
            latency_estimate_ms=latency_estimate,
            latency_actual_ms=latency_actual,
            reason=reason,
            data_freshness_seconds=random.randint(0, 3600),  # Mock freshness
        )

    async def get_carbon_intensity(self, region: Region) -> float:
        """Get carbon intensity for a region."""
        return self.carbon_intensity_data.get(region, 300.0)

    async def calculate_energy_impact(
        self,
        energy_kwh: float,
        region: Region,
        request_count: int = 1
    ) -> Dict[str, float]:
        """Calculate environmental impact of energy usage."""
        carbon_intensity = await self.get_carbon_intensity(region)
        co2_grams = carbon_intensity * energy_kwh * request_count

        return {
            "energy_kwh": energy_kwh,
            "carbon_intensity_g_per_kwh": carbon_intensity,
            "co2_emissions_grams": co2_grams,
            "co2_emissions_kg": co2_grams / 1000,
            "equivalent_car_miles": co2_grams / 400,  # Rough estimate: 400g CO2 per mile
        }

    async def get_routing_history(
        self,
        workspace_id: Optional[str] = None,
        limit: int = 100
    ) -> List[RoutingDecision]:
        """Get routing decision history."""
        # In a real implementation, this would query a database
        # For now, return mock data
        decisions = []
        regions = list(Region)

        for i in range(min(limit, 50)):  # Generate up to 50 mock decisions
            baseline_region = random.choice(regions)
            chosen_region = random.choice(regions)

            decision = RoutingDecision(
                id=f"decision_{i}",
                timestamp=datetime.utcnow(),
                workspace_id=workspace_id,
                operation="mock_operation",
                workload_name=f"workload_{i}",
                operation_name=f"op_{i}",
                baseline_region=baseline_region,
                chosen_region=chosen_region,
                baseline_zone=random.choice(list(Zone)),
                chosen_zone=random.choice(list(Zone)),
                request_count=random.randint(1, 100),
                carbon_intensity_baseline=self.carbon_intensity_data[baseline_region],
                carbon_intensity_chosen=self.carbon_intensity_data[chosen_region],
                estimated_energy_kwh=random.uniform(0.01, 1.0),
                co2_baseline_grams=random.uniform(10, 1000),
                co2_chosen_grams=random.uniform(5, 500),
                latency_estimate_ms=random.randint(10, 300),
                latency_actual_ms=random.randint(10, 400),
                reason=f"Mock decision {i}",
                data_freshness_seconds=random.randint(0, 3600),
            )
            decisions.append(decision)

        return decisions

    async def get_environmental_summary(
        self,
        workspace_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get environmental impact summary."""
        # In a real implementation, this would aggregate from database
        # For now, return mock summary

        total_decisions = random.randint(100, 1000)
        total_energy = random.uniform(10, 100)
        total_co2 = random.uniform(1000, 10000)
        co2_saved = random.uniform(100, 1000)

        return {
            "time_range_hours": hours,
            "total_decisions": total_decisions,
            "total_energy_kwh": total_energy,
            "total_co2_emissions_kg": total_co2 / 1000,
            "co2_savings_kg": co2_saved / 1000,
            "efficiency_percentage": (co2_saved / (total_co2 + co2_saved)) * 100,
            "average_latency_ms": random.randint(50, 150),
            "fallback_usage_percentage": random.uniform(1, 10),
        }


# Global environmental service instance
environmental_service = EnvironmentalService()
