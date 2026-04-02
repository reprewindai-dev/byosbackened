"""Environmental decision-making API endpoints for carbon-aware routing."""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from core.environmental.service import environmental_service, RoutingDecision, Region
from core.dependencies import get_current_workspace

router = APIRouter(prefix="/environmental", tags=["environmental"])


@router.post("/decide-route", response_model=RoutingDecision)
async def make_routing_decision(
    workload_name: str = Query(..., description="Name of the workload"),
    operation_name: str = Query(..., description="Name of the operation"),
    baseline_region: Region = Query(..., description="Baseline region to compare against"),
    request_count: int = Query(1, ge=1, description="Number of requests"),
    energy_estimate_kwh: float = Query(0.1, ge=0, description="Estimated energy consumption in kWh"),
    workspace_id: str = Depends(get_current_workspace)
):
    """Make a carbon-aware routing decision."""
    try:
        decision = await environmental_service.make_routing_decision(
            workload_name=workload_name,
            operation_name=operation_name,
            baseline_region=baseline_region,
            request_count=request_count,
            energy_estimate_kwh=energy_estimate_kwh,
            workspace_id=workspace_id
        )
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing decision failed: {str(e)}")


@router.get("/carbon-intensity/{region}")
async def get_carbon_intensity(region: Region):
    """Get carbon intensity for a specific region."""
    try:
        intensity = await environmental_service.get_carbon_intensity(region)
        return {
            "region": region.value,
            "carbon_intensity_g_per_kwh": intensity,
            "description": f"Carbon intensity for {region.value} region"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get carbon intensity: {str(e)}")


@router.post("/calculate-impact")
async def calculate_energy_impact(
    energy_kwh: float = Query(..., ge=0, description="Energy consumption in kWh"),
    region: Region = Query(..., description="Region where energy is consumed"),
    request_count: int = Query(1, ge=1, description="Number of requests")
):
    """Calculate environmental impact of energy usage."""
    try:
        impact = await environmental_service.calculate_energy_impact(
            energy_kwh=energy_kwh,
            region=region,
            request_count=request_count
        )
        return impact
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Impact calculation failed: {str(e)}")


@router.get("/decisions", response_model=List[RoutingDecision])
async def get_routing_history(
    workspace_id: str = Depends(get_current_workspace),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of decisions to return")
):
    """Get routing decision history."""
    try:
        decisions = await environmental_service.get_routing_history(
            workspace_id=workspace_id,
            limit=limit
        )
        return decisions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get routing history: {str(e)}")


@router.get("/summary")
async def get_environmental_summary(
    workspace_id: str = Depends(get_current_workspace),
    hours: int = Query(24, ge=1, le=168, description="Time range in hours (max 1 week)")
):
    """Get environmental impact summary."""
    try:
        summary = await environmental_service.get_environmental_summary(
            workspace_id=workspace_id,
            hours=hours
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get environmental summary: {str(e)}")


@router.get("/regions")
async def get_available_regions():
    """Get list of available geographic regions."""
    regions = [region.value for region in Region]
    carbon_data = {}

    for region in Region:
        intensity = await environmental_service.get_carbon_intensity(region)
        carbon_data[region.value] = {
            "carbon_intensity_g_per_kwh": intensity,
            "description": f"Carbon intensity for {region.value}"
        }

    return {
        "regions": regions,
        "carbon_intensity_data": carbon_data,
        "features": {
            "carbon_aware_routing": True,
            "energy_tracking": True,
            "co2_calculations": True,
            "latency_estimation": True
        }
    }
