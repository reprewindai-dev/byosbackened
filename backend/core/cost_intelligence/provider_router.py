"""Intelligent provider routing."""
from decimal import Decimal
from typing import Optional, Dict, List, Any
from pydantic import BaseModel
from core.cost_intelligence.cost_calculator import CostCalculator
from core.autonomous.ml_models.routing_optimizer import get_routing_optimizer_ml
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
routing_optimizer_ml = get_routing_optimizer_ml()


class RoutingConstraints(BaseModel):
    """Routing constraints."""

    max_cost: Optional[Decimal] = None
    min_quality: Optional[float] = None
    max_latency_ms: Optional[int] = None
    strategy: str = "cost_optimized"  # cost_optimized, quality_optimized, speed_optimized, hybrid


class ProviderOption(BaseModel):
    """Provider option for routing."""

    provider: str
    cost: Decimal
    quality_score: float
    latency_ms: int
    score: float  # Combined score for ranking


class RoutingDecision(BaseModel):
    """Routing decision result."""

    selected_provider: str
    reasoning: str
    expected_cost: Decimal
    expected_quality_score: float
    expected_latency_ms: int
    alternatives_considered: List[Dict[str, Any]]


class ProviderRouter:
    """Intelligent provider router."""

    # Provider metrics (updated from actual usage)
    PROVIDER_METRICS = {
        "huggingface": {
            "avg_cost": Decimal("0.00"),
            "avg_quality": 0.85,
            "avg_latency_ms": 2000,
        },
        "openai": {
            "avg_cost": Decimal("0.002"),
            "avg_quality": 0.95,
            "avg_latency_ms": 1500,
        },
        "local": {
            "avg_cost": Decimal("0.001"),
            "avg_quality": 0.80,
            "avg_latency_ms": 5000,
        },
    }

    def __init__(self):
        self.cost_calculator = CostCalculator()

    def select_provider(
        self,
        operation_type: str,
        constraints: RoutingConstraints,
        input_text: Optional[str] = None,
        workspace_id: Optional[str] = None,
        use_ml: bool = True,
    ) -> RoutingDecision:
        """
        Select optimal provider based on constraints.
        
        Uses ML routing optimizer if workspace_id provided, otherwise uses rule-based.
        This is what creates the moat - ML routing improves over time per workspace.
        """
        # Try ML routing first if workspace_id provided
        if use_ml and workspace_id:
            try:
                available_providers = list(self.PROVIDER_METRICS.keys())
                selected_provider = routing_optimizer_ml.select_provider(
                    workspace_id=workspace_id,
                    operation_type=operation_type,
                    available_providers=available_providers,
                    constraints=constraints.dict() if hasattr(constraints, 'dict') else {},
                )
                
                # Get stats to show learning progress
                stats = routing_optimizer_ml.get_routing_stats(workspace_id, operation_type)
                
                # Predict cost for selected provider
                cost_pred = self.cost_calculator.predict_cost(
                    operation_type, selected_provider, input_text=input_text,
                    workspace_id=workspace_id, use_ml=True
                )
                
                metrics = self.PROVIDER_METRICS.get(selected_provider, {
                    "avg_quality": 0.85,
                    "avg_latency_ms": 2000,
                })
                
                reasoning = (
                    f"Selected {selected_provider} using learned patterns "
                    f"(exploration rate: {stats.get('exploration_rate', 0.1):.1%}, "
                    f"learning samples: {stats.get('learning_samples', 0)}). "
                    f"Best provider: {stats.get('best_provider', 'learning')}"
                )
                
                return RoutingDecision(
                    selected_provider=selected_provider,
                    reasoning=reasoning,
                    expected_cost=cost_pred.predicted_cost,
                    expected_quality_score=metrics["avg_quality"],
                    expected_latency_ms=metrics["avg_latency_ms"],
                    alternatives_considered=[],
                )
            except Exception as e:
                logger.warning(f"ML routing failed, using fallback: {e}")
        
        # Fallback to rule-based routing
        # Evaluate all providers
        options = []
        
        for provider_name, metrics in self.PROVIDER_METRICS.items():
            # Predict cost
            cost_pred = self.cost_calculator.predict_cost(
                operation_type, provider_name, input_text=input_text
            )
            
            # Check constraints
            if constraints.max_cost and cost_pred.predicted_cost > constraints.max_cost:
                continue
            if constraints.min_quality and metrics["avg_quality"] < constraints.min_quality:
                continue
            if constraints.max_latency_ms and metrics["avg_latency_ms"] > constraints.max_latency_ms:
                continue
            
            # Calculate score based on strategy
            score = self._calculate_score(
                cost_pred.predicted_cost,
                metrics["avg_quality"],
                metrics["avg_latency_ms"],
                constraints.strategy,
            )
            
            options.append(
                ProviderOption(
                    provider=provider_name,
                    cost=cost_pred.predicted_cost,
                    quality_score=metrics["avg_quality"],
                    latency_ms=metrics["avg_latency_ms"],
                    score=score,
                )
            )
        
        if not options:
            # No provider meets constraints, use cheapest
            options = [
                ProviderOption(
                    provider="huggingface",
                    cost=Decimal("0.00"),
                    quality_score=0.85,
                    latency_ms=2000,
                    score=1.0,
                )
            ]
        
        # Sort by score (higher is better)
        options.sort(key=lambda x: x.score, reverse=True)
        selected = options[0]
        
        # Generate reasoning
        reasoning = self._generate_reasoning(selected, options, constraints)
        
        return RoutingDecision(
            selected_provider=selected.provider,
            reasoning=reasoning,
            expected_cost=selected.cost,
            expected_quality_score=selected.quality_score,
            expected_latency_ms=selected.latency_ms,
            alternatives_considered=options[1:] if len(options) > 1 else [],
        )

    def _calculate_score(
        self,
        cost: Decimal,
        quality: float,
        latency_ms: int,
        strategy: str,
    ) -> float:
        """Calculate provider score based on strategy."""
        if strategy == "cost_optimized":
            # Lower cost = higher score
            max_cost = Decimal("0.01")
            cost_score = 1.0 - min(float(cost / max_cost), 1.0)
            return cost_score * 0.7 + quality * 0.3  # Weight cost more
        
        elif strategy == "quality_optimized":
            # Higher quality = higher score
            return quality * 0.7 + (1.0 - min(cost / Decimal("0.01"), 1.0)) * 0.3
        
        elif strategy == "speed_optimized":
            # Lower latency = higher score
            max_latency = 10000
            latency_score = 1.0 - min(latency_ms / max_latency, 1.0)
            return latency_score * 0.7 + quality * 0.3
        
        else:  # hybrid
            # Balance all factors
            cost_score = 1.0 - min(float(cost / Decimal("0.01")), 1.0)
            latency_score = 1.0 - min(latency_ms / 10000, 1.0)
            return (cost_score * 0.4 + quality * 0.4 + latency_score * 0.2)

    def _generate_reasoning(
        self,
        selected: ProviderOption,
        alternatives: List[ProviderOption],
        constraints: RoutingConstraints,
    ) -> str:
        """Generate human-readable reasoning."""
        reasons = [f"Selected {selected.provider}"]
        
        if constraints.strategy == "cost_optimized":
            reasons.append(f"lowest cost (${selected.cost})")
        elif constraints.strategy == "quality_optimized":
            reasons.append(f"highest quality ({selected.quality_score:.2f})")
        elif constraints.strategy == "speed_optimized":
            reasons.append(f"lowest latency ({selected.latency_ms}ms)")
        
        if alternatives:
            alt = alternatives[0]
            savings = ((alt.cost - selected.cost) / alt.cost * 100) if alt.cost > 0 else 0
            reasons.append(f"saves {savings:.1f}% vs {alt.provider}")
        
        return ". ".join(reasons) + "."

    def update_provider_metrics(
        self,
        provider: str,
        cost: Decimal,
        quality: float,
        latency_ms: int,
    ):
        """Update provider metrics from actual usage."""
        if provider not in self.PROVIDER_METRICS:
            return
        
        metrics = self.PROVIDER_METRICS[provider]
        # Moving average
        metrics["avg_cost"] = metrics["avg_cost"] * 0.9 + cost * 0.1
        metrics["avg_quality"] = metrics["avg_quality"] * 0.9 + quality * 0.1
        metrics["avg_latency_ms"] = int(metrics["avg_latency_ms"] * 0.9 + latency_ms * 0.1)
        
        logger.info(f"Updated provider metrics: {provider} = {metrics}")
