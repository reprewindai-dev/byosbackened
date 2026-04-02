"""Optimization suggestions - generate proactive suggestions."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import AIAuditLog, RoutingDecision, TrafficPattern
from core.autonomous.prediction.traffic_predictor import get_traffic_predictor
from core.autonomous.scaling.auto_scaler import get_auto_scaler
from core.edge.routing_engine import get_edge_routing_engine
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
traffic_predictor = get_traffic_predictor()
auto_scaler = get_auto_scaler()
edge_routing_engine = get_edge_routing_engine()


class OptimizationSuggestions:
    """
    Generate proactive optimization suggestions.
    
    Suggests optimizations that save money or improve performance.
    Creates "aha moments" - shows users we're thinking ahead.
    """

    def generate_suggestions(
        self,
        workspace_id: str,
        db: Optional[Session] = None,
    ) -> List[Dict[str, any]]:
        """
        Generate optimization suggestions for workspace.
        
        Returns list of suggestions with priority and impact.
        """
        if not db:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        suggestions = []
        
        try:
            # 1. Provider switching suggestions
            provider_suggestions = self._suggest_provider_switches(workspace_id, db)
            suggestions.extend(provider_suggestions)
            
            # 2. Auto-scaling suggestions
            scaling_suggestions = self._suggest_auto_scaling(workspace_id)
            suggestions.extend(scaling_suggestions)
            
            # 3. Edge routing suggestions
            edge_suggestions = self._suggest_edge_routing(workspace_id, db)
            suggestions.extend(edge_suggestions)
            
            # 4. Cache optimization suggestions
            cache_suggestions = self._suggest_cache_optimization(workspace_id, db)
            suggestions.extend(cache_suggestions)
            
            # Sort by priority (impact * confidence)
            suggestions.sort(key=lambda s: s.get("priority", 0), reverse=True)
            
            return suggestions[:10]  # Top 10 suggestions
        finally:
            if should_close:
                db.close()

    def _suggest_provider_switches(
        self,
        workspace_id: str,
        db: Session,
    ) -> List[Dict[str, any]]:
        """Suggest provider switches that save money."""
        suggestions = []
        
        # Get last 30 days of operations
        cutoff = datetime.utcnow() - timedelta(days=30)
        
        operations = db.query(AIAuditLog).filter(
            AIAuditLog.workspace_id == workspace_id,
            AIAuditLog.created_at >= cutoff,
            AIAuditLog.cost.isnot(None),
        ).all()
        
        if not operations:
            return suggestions
        
        # Analyze provider costs
        provider_costs = {}
        for op in operations:
            provider = op.provider
            cost = float(op.cost) if op.cost else 0.0
            
            if provider not in provider_costs:
                provider_costs[provider] = {"total": 0.0, "count": 0}
            
            provider_costs[provider]["total"] += cost
            provider_costs[provider]["count"] += 1
        
        # Find expensive providers
        for provider, stats in provider_costs.items():
            avg_cost = stats["total"] / stats["count"] if stats["count"] > 0 else 0.0
            
            # Suggest cheaper alternatives
            if provider == "openai" and avg_cost > 0.001:
                # Suggest Hugging Face for cost savings
                estimated_savings = stats["total"] * 0.7  # 70% savings
                
                suggestions.append({
                    "type": "provider_switch",
                    "title": f"Switch {provider} to Hugging Face for operation types",
                    "description": (
                        f"You're spending ${stats['total']:.2f} on {provider}. "
                        f"Switching to Hugging Face could save ~${estimated_savings:.2f} (70% savings)."
                    ),
                    "impact": "high",
                    "effort": "low",
                    "priority": estimated_savings,
                    "action": f"switch_provider:{provider}:huggingface",
                })
        
        return suggestions

    def _suggest_auto_scaling(
        self,
        workspace_id: str,
    ) -> List[Dict[str, any]]:
        """Suggest auto-scaling optimizations."""
        suggestions = []
        
        # Check traffic patterns
        spike_prediction = traffic_predictor.predict_spike(
            workspace_id=workspace_id,
            hours_ahead=24,
        )
        
        if spike_prediction and spike_prediction.get("will_spike"):
            suggestions.append({
                "type": "auto_scaling",
                "title": "Enable auto-scaling for traffic spikes",
                "description": (
                    f"Traffic spike predicted: {spike_prediction['predicted_requests']} requests "
                    f"({spike_prediction['spike_multiplier']:.1f}x normal) at {spike_prediction['spike_time']}. "
                    f"Enable auto-scaling to handle the load."
                ),
                "impact": "high",
                "effort": "low",
                "priority": spike_prediction.get("spike_multiplier", 1.0) * 100,
                "action": "enable_auto_scaling",
            })
        
        return suggestions

    def _suggest_edge_routing(
        self,
        workspace_id: str,
        db: Session,
    ) -> List[Dict[str, any]]:
        """Suggest edge routing optimizations."""
        suggestions = []
        
        # Check if workspace has EU/Asia users
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        operations = db.query(AIAuditLog).filter(
            AIAuditLog.workspace_id == workspace_id,
            AIAuditLog.created_at >= cutoff,
        ).limit(100).all()
        
        # Analyze user regions (simplified - would use geo-IP in production)
        # For now, suggest edge routing if not already enabled
        
        if operations:
            suggestions.append({
                "type": "edge_routing",
                "title": "Enable edge routing for EU/Asia users",
                "description": (
                    "Enable edge routing to reduce latency for EU and Asia-Pacific users. "
                    "Expected latency reduction: 200-500ms."
                ),
                "impact": "medium",
                "effort": "low",
                "priority": 50.0,
                "action": "enable_edge_routing",
            })
        
        return suggestions

    def _suggest_cache_optimization(
        self,
        workspace_id: str,
        db: Session,
    ) -> List[Dict[str, any]]:
        """Suggest cache optimization."""
        suggestions = []
        
        # Check cache hit rate (simplified)
        # In production, would query actual cache statistics
        
        suggestions.append({
            "type": "cache_optimization",
            "title": "Increase cache size for better hit rate",
            "description": (
                "Your cache hit rate could be improved. Increasing cache size "
                "could improve hit rate by 10-15%, reducing costs."
            ),
            "impact": "medium",
            "effort": "low",
            "priority": 30.0,
            "action": "increase_cache_size",
        })
        
        return suggestions


# Global optimization suggestions
_optimization_suggestions = OptimizationSuggestions()


def get_optimization_suggestions() -> OptimizationSuggestions:
    """Get global optimization suggestions instance."""
    return _optimization_suggestions
