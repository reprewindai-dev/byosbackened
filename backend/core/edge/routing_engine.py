"""Edge routing engine - decide which region to use."""
from typing import Optional, Dict, Any
from decimal import Decimal
from core.edge.region_manager import RegionManager
from core.edge.latency_monitor import get_latency_monitor
from core.edge.cost_calculator import get_edge_cost_calculator
from core.edge.placement_learner import PlacementLearner
from core.tracing.tracer import get_tracer
from core.autonomous.feature_flags import get_feature_flags
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
region_manager = RegionManager()
latency_monitor = get_latency_monitor()
edge_cost_calculator = get_edge_cost_calculator()
placement_learner = PlacementLearner()
tracer = get_tracer()
feature_flags = get_feature_flags()


class EdgeRoutingEngine:
    """
    Edge routing engine - decides which region to use.
    
    Considers:
    - Latency (route to nearest)
    - Cost (data transfer, compute)
    - Data residency requirements
    - Learned patterns (which operations benefit from edge)
    """

    def select_region(
        self,
        workspace_id: str,
        operation_type: str,
        user_region: Optional[str] = None,  # From geo-IP
        data_residency: Optional[str] = None,  # From workspace settings
        input_size_bytes: int = 0,
        prioritize_latency: bool = True,
        prioritize_cost: bool = False,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Select optimal region for operation.
        
        Returns region selection with reasoning.
        Includes distributed tracing for edge routing decisions.
        """
        # Check kill switch
        if not feature_flags.is_enabled("edge_routing_enabled"):
            logger.warning("Edge routing disabled via kill switch, using default region")
            return {
                "region": "us-east",  # Default region
                "reasoning": "Edge routing disabled via kill switch",
                "factors": {},
            }
        
        with tracer.span(
            name="edge_routing.select_region",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            attributes={
                "workspace_id": workspace_id,
                "operation_type": operation_type,
                "user_region": user_region or "unknown",
                "data_residency": data_residency or "none",
                "input_size_bytes": input_size_bytes,
                "prioritize_latency": prioritize_latency,
                "prioritize_cost": prioritize_cost,
            },
        ) as span:
            # Data residency takes priority
            if data_residency:
                region_map = {
                    "eu": "eu-west",
                    "us": "us-east",
                    "asia": "asia-pacific",
                }
                if data_residency.lower() in region_map:
                    selected = region_map[data_residency.lower()]
                    span.set_attribute("selected_region", selected)
                    span.set_attribute("routing_reason", "data_residency")
                    result = {
                        "region": selected,
                        "reasoning": f"Data residency requirement: {data_residency}",
                        "factors": {
                            "data_residency": True,
                            "latency_ms": latency_monitor.get_latency_stats(selected)["avg"] if latency_monitor.get_latency_stats(selected) else 0.0,
                        },
                    }
                    span.add_event("region_selected", {"region": selected, "reason": "data_residency"})
                    return result
            
            # Try learned placement
            with tracer.span(
                name="edge_routing.learned_placement",
                trace_id=trace_id,
                parent_span_id=span.span_id,
            ) as placement_span:
                learned_region = placement_learner.get_optimal_region(
                    workspace_id=workspace_id,
                    operation_type=operation_type,
                )
                
                if learned_region:
                    stats = latency_monitor.get_latency_stats(learned_region)
                    span.set_attribute("selected_region", learned_region)
                    span.set_attribute("routing_reason", "learned")
                    result = {
                        "region": learned_region,
                        "reasoning": "Learned optimal region from historical patterns",
                        "factors": {
                            "learned": True,
                            "latency_ms": stats["avg"] if stats else 0.0,
                        },
                    }
                    span.add_event("region_selected", {"region": learned_region, "reason": "learned"})
                    return result
            
            # Choose based on priority
            if prioritize_latency:
                # Route to nearest region
                with tracer.span(
                    name="edge_routing.latency_check",
                    trace_id=trace_id,
                    parent_span_id=span.span_id,
                ) as latency_span:
                    if user_region:
                        # Map user region to nearest data center
                        region_map = {
                            "eu": "eu-west",
                            "europe": "eu-west",
                            "asia": "asia-pacific",
                            "apac": "asia-pacific",
                        }
                        if user_region.lower() in region_map:
                            selected = region_map[user_region.lower()]
                        else:
                            selected = latency_monitor.get_best_region(user_region)
                    else:
                        selected = latency_monitor.get_best_region()
                    
                    stats = latency_monitor.get_latency_stats(selected)
                    span.set_attribute("selected_region", selected)
                    span.set_attribute("routing_reason", "latency_optimized")
                    result = {
                        "region": selected,
                        "reasoning": f"Lowest latency region (avg: {stats['avg']:.1f}ms)" if stats else "Lowest latency region",
                        "factors": {
                            "latency_optimized": True,
                            "latency_ms": stats["avg"] if stats else 0.0,
                        },
                    }
                    span.add_event("region_selected", {"region": selected, "reason": "latency"})
                    return result
            
            elif prioritize_cost:
                # Route to cheapest region
                with tracer.span(
                    name="edge_routing.cost_check",
                    trace_id=trace_id,
                    parent_span_id=span.span_id,
                ) as cost_span:
                    selected = edge_cost_calculator.get_cheapest_region(
                        operation_type=operation_type,
                        input_size_bytes=input_size_bytes,
                        source_region=user_region,
                    )
                    
                    costs = edge_cost_calculator.compare_region_costs(
                        operation_type=operation_type,
                        input_size_bytes=input_size_bytes,
                        source_region=user_region,
                    )
                    
                    span.set_attribute("selected_region", selected)
                    span.set_attribute("routing_reason", "cost_optimized")
                    result = {
                        "region": selected,
                        "reasoning": f"Lowest cost region (${costs[selected]['total_cost']:.6f})",
                        "factors": {
                            "cost_optimized": True,
                            "total_cost": float(costs[selected]["total_cost"]),
                        },
                    }
                    span.add_event("region_selected", {"region": selected, "reason": "cost"})
                    return result
            
            else:
                # Hybrid: balance latency and cost
                with tracer.span(
                    name="edge_routing.hybrid_scoring",
                    trace_id=trace_id,
                    parent_span_id=span.span_id,
                ) as hybrid_span:
                    # Score each region
                    region_scores = {}
                    
                    for region in region_manager.get_regions():
                        stats = latency_monitor.get_latency_stats(region)
                        costs = edge_cost_calculator.calculate_region_cost(
                            region=region,
                            operation_type=operation_type,
                            input_size_bytes=input_size_bytes,
                        )
                        
                        # Normalize scores (lower is better)
                        latency_score = stats["avg"] / 1000.0 if stats and stats["avg"] > 0 else 1.0  # Normalize to 0-1
                        cost_score = float(costs["total_cost"]) / 0.01  # Normalize to 0-1 (assuming max $0.01)
                        
                        # Combined score (weighted)
                        combined_score = latency_score * 0.6 + cost_score * 0.4
                        region_scores[region] = {
                            "score": combined_score,
                            "latency_ms": stats["avg"] if stats else 0.0,
                            "cost": float(costs["total_cost"]),
                        }
                    
                    # Select best region
                    selected = min(region_scores.keys(), key=lambda r: region_scores[r]["score"])
                    
                    span.set_attribute("selected_region", selected)
                    span.set_attribute("routing_reason", "hybrid")
                    result = {
                        "region": selected,
                        "reasoning": f"Optimal balance of latency ({region_scores[selected]['latency_ms']:.1f}ms) and cost (${region_scores[selected]['cost']:.6f})",
                        "factors": {
                            "hybrid": True,
                            "latency_ms": region_scores[selected]["latency_ms"],
                            "cost": region_scores[selected]["cost"],
                        },
                    }
                    span.add_event("region_selected", {"region": selected, "reason": "hybrid"})
                    return result

    def should_route_to_edge(
        self,
        workspace_id: str,
        operation_type: str,
        input_size_bytes: int,
    ) -> bool:
        """
        Decide if operation should route to edge.
        
        Media/real-time operations benefit from edge.
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


# Global edge routing engine
_edge_routing_engine = EdgeRoutingEngine()


def get_edge_routing_engine() -> EdgeRoutingEngine:
    """Get global edge routing engine instance."""
    return _edge_routing_engine
