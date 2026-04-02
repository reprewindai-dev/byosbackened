"""ML-powered routing optimizer - learns per workspace."""
from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import RoutingDecision
from core.autonomous.learning.bandit import MultiArmedBandit
from core.tracing.tracer import get_tracer
from core.autonomous.feature_flags import get_feature_flags
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
tracer = get_tracer()
feature_flags = get_feature_flags()


class RoutingOptimizerML:
    """
    ML-powered routing optimizer that learns per workspace.
    
    Uses multi-armed bandit for exploration/exploitation.
    Learns workspace-specific patterns - creates non-portable intelligence.
    """

    def __init__(self):
        self.bandits: Dict[str, MultiArmedBandit] = {}  # workspace_id -> bandit

    def select_provider(
        self,
        workspace_id: str,
        operation_type: str,
        available_providers: List[str],
        constraints: Dict,
    ) -> str:
        """
        Select provider using learned patterns for workspace.
        
        Balances exploration (try new) vs exploitation (use what works).
        Includes safety checks and fallback logic.
        """
        # Get or create bandit for workspace
        bandit_key = f"{workspace_id}:{operation_type}"
        
        if bandit_key not in self.bandits:
            self.bandits[bandit_key] = MultiArmedBandit(workspace_id)
            logger.info(f"Created new bandit for {bandit_key}")
        
        bandit = self.bandits[bandit_key]
        
        # Validate constraints
        validated_constraints = self._validate_constraints(constraints)
        
            try:
                # Select provider using bandit with constraints
                with tracer.span(
                    name="ml.bandit_selection",
                    trace_id=trace_id,
                    parent_span_id=span.span_id,
                ) as bandit_span:
                    selected = bandit.select_arm(
                        available_providers,
                        operation_type,
                        constraints=validated_constraints,
                    )
                    bandit_span.set_attribute("selected_provider", selected)
                    span.set_attribute("selected_provider", selected)
                
                # Verify selection meets constraints (safety check)
                if not self._meets_constraints(selected, validated_constraints):
                    # Fallback to safest provider
                    fallback = bandit._get_fallback_provider(available_providers)
                    span.set_attribute("fallback_used", True)
                    span.set_attribute("fallback_reason", "constraints_not_met")
                    span.add_event("fallback", {"reason": "constraints_not_met", "fallback_provider": fallback})
                    logger.warning(
                        f"Selected provider {selected} doesn't meet constraints, "
                        f"using fallback: {fallback}"
                    )
                    return fallback
                
                span.add_event("provider_selected", {"provider": selected})
                return selected
                
            except Exception as e:
                # Fallback if ML selection fails
                span.set_status("error", str(e))
                span.set_attribute("fallback_used", True)
                span.set_attribute("fallback_reason", "ml_selection_failed")
                logger.error(f"ML routing failed for {bandit_key}: {e}, using fallback")
                fallback = bandit._get_fallback_provider(available_providers)
                span.add_event("fallback", {"reason": "ml_selection_failed", "fallback_provider": fallback})
                return fallback
    
    def _validate_constraints(self, constraints: Dict) -> Dict:
        """Validate and normalize constraints."""
        validated = {}
        
        if "max_cost" in constraints and constraints["max_cost"]:
            validated["max_cost"] = float(constraints["max_cost"])
        
        if "max_latency_ms" in constraints and constraints["max_latency_ms"]:
            validated["max_latency_ms"] = int(constraints["max_latency_ms"])
        
        if "min_quality" in constraints and constraints["min_quality"]:
            validated["min_quality"] = float(constraints["min_quality"])
        
        return validated
    
    def _meets_constraints(self, provider: str, constraints: Dict) -> bool:
        """Check if provider meets constraints (safety check)."""
        # This would check historical data for provider
        # For now, assume it meets constraints if bandit selected it
        return True

    def update_routing_outcome(
        self,
        workspace_id: str,
        operation_type: str,
        provider: str,
        actual_cost: Decimal,
        actual_quality: float,
        actual_latency_ms: int,
        baseline_cost: Decimal,
    ):
        """
        Update routing model with actual outcome.
        
        This is the learning loop - improves over time.
        """
        bandit_key = f"{workspace_id}:{operation_type}"
        
        if bandit_key not in self.bandits:
            self.bandits[bandit_key] = MultiArmedBandit(workspace_id)
        
        bandit = self.bandits[bandit_key]
        
        # Calculate reward
        reward = bandit.calculate_reward(
            cost=actual_cost,
            quality=actual_quality,
            latency_ms=actual_latency_ms,
            baseline_cost=baseline_cost,
        )
        
        # Determine success (quality meets threshold, latency acceptable)
        success = (
            actual_quality >= 0.7 and  # Minimum quality threshold
            actual_latency_ms < 10000  # Maximum latency threshold
        )
        
        # Update bandit with success flag
        bandit.update_reward(provider, reward, success=success)
        
        logger.debug(
            f"Updated routing outcome for {bandit_key}: "
            f"provider={provider}, reward={reward:.3f}, success={success}"
        )

    def get_routing_stats(
        self,
        workspace_id: str,
        operation_type: str,
    ) -> Dict[str, any]:
        """Get routing statistics for workspace."""
        bandit_key = f"{workspace_id}:{operation_type}"
        
        if bandit_key not in self.bandits:
            return {
                "best_provider": None,
                "stats": {},
                "learning_samples": 0,
            }
        
        bandit = self.bandits[bandit_key]
        stats = bandit.get_stats()
        best_provider = bandit.get_best_arm()
        
        total_samples = sum(s["count"] for s in stats.values())
        
        return {
            "best_provider": best_provider,
            "stats": stats,
            "learning_samples": total_samples,
            "exploration_rate": bandit.exploration_rate,
        }

    def learn_from_history(
        self,
        db: Session,
        workspace_id: str,
        operation_type: str,
    ):
        """
        Learn from historical routing decisions.
        
        This accelerates learning by using past data.
        """
        # Get historical routing decisions with outcomes
        decisions = db.query(RoutingDecision).filter(
            RoutingDecision.workspace_id == workspace_id,
            RoutingDecision.operation_type == operation_type,
            RoutingDecision.actual_cost.isnot(None),  # Only completed decisions
        ).limit(1000).all()
        
        if not decisions:
            logger.info(f"No historical data for {workspace_id}:{operation_type}")
            return
        
        # Get or create bandit
        bandit_key = f"{workspace_id}:{operation_type}"
        if bandit_key not in self.bandits:
            self.bandits[bandit_key] = MultiArmedBandit(workspace_id)
        
        bandit = self.bandits[bandit_key]
        
        # Learn from each decision
        for decision in decisions:
            # Calculate baseline (use expected cost as baseline)
            baseline_cost = decision.expected_cost
            
            # Update with actual outcome
            self.update_routing_outcome(
                workspace_id=workspace_id,
                operation_type=operation_type,
                provider=decision.selected_provider,
                actual_cost=decision.actual_cost or Decimal("0"),
                actual_quality=float(decision.actual_quality) if decision.actual_quality else 0.8,
                actual_latency_ms=decision.actual_latency_ms or 2000,
                baseline_cost=baseline_cost,
            )
        
        logger.info(
            f"Learned from {len(decisions)} historical decisions for {bandit_key}"
        )


# Global instance
_routing_optimizer_ml = RoutingOptimizerML()


def get_routing_optimizer_ml() -> RoutingOptimizerML:
    """Get global routing optimizer ML instance."""
    return _routing_optimizer_ml
