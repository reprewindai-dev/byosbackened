"""Smoke Relay - summary + receipts for governance pipeline."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from decimal import Decimal
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ExecutionReceipt:
    """Receipt for governance pipeline execution."""
    
    # Basic execution info
    request_id: str
    execution_time_ms: int
    success: bool
    
    # Cost and performance
    estimated_cost: Decimal
    actual_cost: Decimal
    tokens_used: Optional[int]
    latency_ms: int
    
    # Quality and risk metrics
    coherence_score: float  # VCTT τ
    risk_scores: Dict[str, float]
    overall_risk_level: str
    
    # Governance information
    patterns_applied: int
    validators_passed: int
    validators_failed: List[str]
    blocked_at_stage: Optional[str]
    block_reason: Optional[str]
    
    # ROI and value metrics (for demo)
    time_saved_minutes: Optional[float]
    cost_avoided_usd: Optional[Decimal]
    risk_reduction_score: Optional[float]
    before_after_diff: Optional[Dict[str, Any]]
    
    # Moat contribution
    moat_strength_delta: float
    community_patterns_contributed: int
    
    # Timestamp
    timestamp: datetime


class SmokeRelay:
    """
    Smoke Relay - generates summaries and receipts for every execution.
    
    This component:
    1. Calculates ROI metrics for demo purposes
    2. Generates detailed execution receipts
    3. Provides before/after comparisons
    4. Tracks moat contribution and value delivered
    """
    
    def __init__(self):
        # ROI calculation parameters
        self.value_multipliers = {
            "content_creation": {
                "time_per_minute": Decimal("2.50"),  # $2.50 per minute saved
                "risk_per_error": Decimal("50.00"),   # $50 per error avoided
                "quality_multiplier": 1.5,
            },
            "business_analysis": {
                "time_per_minute": Decimal("5.00"),   # $5.00 per minute saved
                "risk_per_error": Decimal("200.00"),  # $200 per error avoided
                "quality_multiplier": 2.0,
            },
            "customer_support": {
                "time_per_minute": Decimal("1.50"),   # $1.50 per minute saved
                "risk_per_error": Decimal("25.00"),   # $25 per error avoided
                "quality_multiplier": 1.2,
            },
            "data_processing": {
                "time_per_minute": Decimal("3.00"),   # $3.00 per minute saved
                "risk_per_error": Decimal("100.00"),  # $100 per error avoided
                "quality_multiplier": 1.8,
            },
        }
        
        # Default multiplier for unknown domains
        self.default_multiplier = {
            "time_per_minute": Decimal("2.00"),
            "risk_per_error": Decimal("50.00"),
            "quality_multiplier": 1.0,
        }
    
    def generate_receipt(
        self,
        governance_result: Dict[str, Any],
        execution_context: Dict[str, Any],
        business_context: Optional[Dict[str, Any]] = None
    ) -> ExecutionReceipt:
        """
        Generate execution receipt with ROI metrics.
        
        Returns: ExecutionReceipt with all metrics and value calculations
        """
        # Extract basic information
        request_id = governance_result.get("request_id", "")
        execution_time_ms = governance_result.get("execution_time_ms", 0)
        success = governance_result.get("pipeline_passed", False)
        
        # Extract cost and performance
        routing_decision = governance_result.get("routing_decision", {})
        execution_outcome = governance_result.get("execution_outcome", {})
        
        estimated_cost = Decimal(str(routing_decision.get("expected_cost", 0)))
        actual_cost = Decimal(str(execution_outcome.get("actual_cost", 0)))
        tokens_used = execution_outcome.get("tokens_used")
        latency_ms = execution_outcome.get("actual_latency_ms", 0)
        
        # Extract quality and risk
        risk_scores = governance_result.get("risk_scores", {})
        coherence_score = risk_scores.get("coherence_score", 0.0)
        overall_risk_level = risk_scores.get("overall_risk", "low")
        
        # Extract governance info
        memory_gate_results = governance_result.get("memory_gate_results", {})
        validation_results = governance_result.get("validation_results", {})
        
        patterns_applied = memory_gate_results.get("patterns_applied", 0)
        validators_passed = sum([
            validation_results.get("compliance_passed", False),
            validation_results.get("budget_passed", False),
            validation_results.get("hallucination_check_passed", False),
            validation_results.get("schema_validation_passed", False),
        ])
        
        validators_failed = []
        if not validation_results.get("compliance_passed", False):
            validators_failed.append("compliance")
        if not validation_results.get("budget_passed", False):
            validators_failed.append("budget")
        if not validation_results.get("hallucination_check_passed", False):
            validators_failed.append("hallucination")
        if not validation_results.get("schema_validation_passed", False):
            validators_failed.append("schema")
        
        blocked_at_stage = governance_result.get("blocked_at_stage")
        block_reason = governance_result.get("block_reason")
        
        # Calculate ROI metrics
        roi_metrics = self._calculate_roi_metrics(
            governance_result,
            execution_context,
            business_context
        )
        
        # Extract moat contribution
        moat_strength_delta = memory_gate_results.get("moat_strength_delta", 0.0)
        community_patterns_contributed = 1 if success and patterns_applied > 0 else 0
        
        return ExecutionReceipt(
            request_id=request_id,
            execution_time_ms=execution_time_ms,
            success=success,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            coherence_score=coherence_score,
            risk_scores=risk_scores,
            overall_risk_level=overall_risk_level,
            patterns_applied=patterns_applied,
            validators_passed=validators_passed,
            validators_failed=validators_failed,
            blocked_at_stage=blocked_at_stage,
            block_reason=block_reason,
            time_saved_minutes=roi_metrics.get("time_saved_minutes"),
            cost_avoided_usd=roi_metrics.get("cost_avoided_usd"),
            risk_reduction_score=roi_metrics.get("risk_reduction_score"),
            before_after_diff=roi_metrics.get("before_after_diff"),
            moat_strength_delta=moat_strength_delta,
            community_patterns_contributed=community_patterns_contributed,
            timestamp=datetime.utcnow()
        )
    
    def _calculate_roi_metrics(
        self,
        governance_result: Dict[str, Any],
        execution_context: Dict[str, Any],
        business_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate ROI metrics for demo purposes."""
        
        # Get business domain for value calculation
        intent_vector = governance_result.get("intent_vector", {})
        business_domain = intent_vector.get("business_domain", "unknown")
        
        # Get value multipliers for this domain
        multipliers = self.value_multipliers.get(business_domain, self.default_multiplier)
        
        # Calculate time saved
        time_saved = self._calculate_time_saved(governance_result, multipliers)
        
        # Calculate cost avoided
        cost_avoided = self._calculate_cost_avoided(governance_result, multipliers)
        
        # Calculate risk reduction
        risk_reduction = self._calculate_risk_reduction(governance_result)
        
        # Generate before/after comparison
        before_after = self._generate_before_after(governance_result, execution_context)
        
        return {
            "time_saved_minutes": time_saved,
            "cost_avoided_usd": cost_avoided,
            "risk_reduction_score": risk_reduction,
            "before_after_diff": before_after,
        }
    
    def _calculate_time_saved(self, governance_result: Dict[str, Any], multipliers: Dict[str, Any]) -> float:
        """Calculate time saved in minutes."""
        
        # Base time calculation based on operation type
        operation_type = governance_result.get("operation_plan", {}).get("operation_type", "")
        
        # Estimated manual time for each operation type (in minutes)
        manual_time_estimates = {
            "summarize": 15.0,      # 15 minutes to manually summarize
            "sentiment": 8.0,       # 8 minutes for manual sentiment analysis
            "ner": 12.0,            # 12 minutes for manual entity extraction
            "chat": 5.0,            # 5 minutes for manual response composition
            "embed": 3.0,           # 3 minutes for manual embedding setup
            "transcribe": 25.0,     # 25 minutes for manual transcription
            "caption": 10.0,        # 10 minutes for manual image captioning
        }
        
        base_time = manual_time_estimates.get(operation_type, 10.0)
        
        # Adjust based on complexity
        intent_vector = governance_result.get("intent_vector", {})
        complexity = intent_vector.get("complexity_score", 0.5)
        
        # Higher complexity = more time saved
        complexity_multiplier = 1.0 + (complexity * 0.5)
        
        # Adjust based on quality
        coherence_score = governance_result.get("risk_scores", {}).get("coherence_score", 0.5)
        quality_multiplier = 0.5 + (coherence_score * 0.5)  # Higher quality = more time saved
        
        # Calculate actual time saved
        time_saved = base_time * complexity_multiplier * quality_multiplier
        
        return max(time_saved, 0.5)  # Minimum 30 seconds saved
    
    def _calculate_cost_avoided(self, governance_result: Dict[str, Any], multipliers: Dict[str, Any]) -> Decimal:
        """Calculate cost avoided in USD."""
        
        risk_scores = governance_result.get("risk_scores", {})
        detrimental_score = risk_scores.get("detrimental_score", 0.0)
        fracture_score = risk_scores.get("fracture_score", 0.0)
        
        # Base risk cost from potential errors
        risk_per_error = multipliers.get("risk_per_error", Decimal("50.00"))
        
        # Calculate error probability reduction
        error_probability = (detrimental_score + fracture_score) / 2
        error_reduction = max(0.0, 1.0 - error_probability)
        
        # Cost avoided from error reduction
        error_cost_avoided = risk_per_error * Decimal(str(error_reduction))
        
        # Add cost savings from governance
        actual_cost = Decimal(str(governance_result.get("execution_outcome", {}).get("actual_cost", 0)))
        
        # Estimate what it would cost without governance (higher risk providers, more retries)
        estimated_cost_without_governance = actual_cost * Decimal("3.0")  # 3x cost without governance
        governance_savings = estimated_cost_without_governance - actual_cost
        
        total_cost_avoided = error_cost_avoided + governance_savings
        
        return max(total_cost_avoided, Decimal("0.01"))  # Minimum $0.01 avoided
    
    def _calculate_risk_reduction_score(self, governance_result: Dict[str, Any]) -> float:
        """Calculate risk reduction score (0-1)."""
        
        risk_scores = governance_result.get("risk_scores", {})
        
        # Calculate baseline risk (what it would be without governance)
        baseline_risk = (
            risk_scores.get("detrimental_score", 0.0) * 0.4 +
            risk_scores.get("fracture_score", 0.0) * 0.3 +
            risk_scores.get("drift_score", 0.0) * 0.3
        )
        
        # Governance reduces risk through validation and quality control
        validation_results = governance_result.get("validation_results", {})
        coherence_score = risk_scores.get("coherence_score", 0.0)
        
        # Calculate risk reduction factors
        governance_protection = 0.7  # Governance provides 70% risk reduction
        quality_protection = coherence_score * 0.3  # Quality provides additional protection
        
        total_protection = governance_protection + quality_protection
        
        # Final risk reduction score
        risk_reduction = baseline_risk * total_protection
        
        return min(risk_reduction, 1.0)
    
    def _generate_before_after(self, governance_result: Dict[str, Any], execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate before/after comparison."""
        
        # Before: What would happen without governance
        before_metrics = {
            "estimated_cost": float(governance_result.get("execution_outcome", {}).get("actual_cost", 0)) * 3.0,
            "quality_score": 0.4,  # Lower quality without governance
            "risk_level": "medium",
            "processing_time_ms": governance_result.get("execution_time_ms", 0) * 2.0,
            "success_probability": 0.6,  # Lower success rate
            "error_rate": 0.3,  # Higher error rate
        }
        
        # After: What happened with governance
        after_metrics = {
            "estimated_cost": float(governance_result.get("execution_outcome", {}).get("actual_cost", 0)),
            "quality_score": governance_result.get("risk_scores", {}).get("coherence_score", 0.0),
            "risk_level": governance_result.get("risk_scores", {}).get("overall_risk", "low"),
            "processing_time_ms": governance_result.get("execution_time_ms", 0),
            "success_probability": 0.95 if governance_result.get("pipeline_passed", False) else 0.0,
            "error_rate": 0.05 if governance_result.get("pipeline_passed", False) else 1.0,
        }
        
        # Calculate improvements
        cost_reduction = (before_metrics["estimated_cost"] - after_metrics["estimated_cost"]) / before_metrics["estimated_cost"]
        quality_improvement = after_metrics["quality_score"] - before_metrics["quality_score"]
        time_improvement = (before_metrics["processing_time_ms"] - after_metrics["processing_time_ms"]) / before_metrics["processing_time_ms"]
        success_improvement = after_metrics["success_probability"] - before_metrics["success_probability"]
        
        return {
            "before": before_metrics,
            "after": after_metrics,
            "improvements": {
                "cost_reduction_percent": cost_reduction * 100,
                "quality_improvement": quality_improvement,
                "time_improvement_percent": time_improvement * 100,
                "success_improvement": success_improvement * 100,
                "error_reduction": before_metrics["error_rate"] - after_metrics["error_rate"],
            }
        }
    
    def generate_summary_report(self, receipts: List[ExecutionReceipt]) -> Dict[str, Any]:
        """Generate summary report from multiple receipts."""
        
        if not receipts:
            return {"error": "No receipts provided"}
        
        # Calculate aggregates
        total_requests = len(receipts)
        successful_requests = sum(1 for r in receipts if r.success)
        success_rate = successful_requests / total_requests
        
        total_cost = sum(r.actual_cost for r in receipts)
        total_time_saved = sum(r.time_saved_minutes or 0 for r in receipts)
        total_cost_avoided = sum(r.cost_avoided_usd or Decimal("0") for r in receipts)
        
        avg_coherence = sum(r.coherence_score for r in receipts) / total_requests
        avg_latency = sum(r.latency_ms for r in receipts) / total_requests
        total_patterns_applied = sum(r.patterns_applied for r in receipts)
        total_moat_delta = sum(r.moat_strength_delta for r in receipts)
        
        # Risk distribution
        risk_distribution = {}
        for r in receipts:
            risk_level = r.overall_risk_level
            risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
        
        # Validator performance
        validator_stats = {
            "compliance_success_rate": sum(1 for r in receipts if "compliance" not in r.validators_failed) / total_requests,
            "budget_success_rate": sum(1 for r in receipts if "budget" not in r.validators_failed) / total_requests,
            "schema_success_rate": sum(1 for r in receipts if "schema" not in r.validators_failed) / total_requests,
        }
        
        return {
            "summary": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": success_rate,
                "total_cost_usd": float(total_cost),
                "total_time_saved_minutes": total_time_saved,
                "total_cost_avoided_usd": float(total_cost_avoided),
                "total_value_delivered": float(total_cost_avoided + (Decimal(str(total_time_saved)) * Decimal("2.00"))),  # $2/min value
            },
            "averages": {
                "coherence_score": avg_coherence,
                "latency_ms": avg_latency,
                "cost_per_request": float(total_cost / total_requests),
                "patterns_per_request": total_patterns_applied / total_requests,
            },
            "risk_distribution": risk_distribution,
            "validator_stats": validator_stats,
            "moat_contribution": {
                "total_patterns_applied": total_patterns_applied,
                "total_moat_strength_delta": total_moat_delta,
                "avg_moat_delta_per_request": total_moat_delta / total_requests,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def format_receipt_for_demo(self, receipt: ExecutionReceipt) -> Dict[str, Any]:
        """Format receipt for demo presentation."""
        
        return {
            "execution_id": receipt.request_id,
            "status": "✅ SUCCESS" if receipt.success else "❌ BLOCKED",
            "performance": {
                "latency": f"{receipt.latency_ms}ms",
                "cost": f"${receipt.actual_cost:.4f}",
                "tokens": receipt.tokens_used,
            },
            "quality_metrics": {
                "coherence_score": f"τ = {receipt.coherence_score:.2f}",
                "risk_level": receipt.overall_risk_level.upper(),
                "patterns_applied": receipt.patterns_applied,
            },
            "value_delivered": {
                "time_saved": f"{receipt.time_saved_minutes:.1f} min",
                "cost_avoided": f"${receipt.cost_avoided_usd:.2f}",
                "risk_reduction": f"{(receipt.risk_reduction_score or 0) * 100:.1f}%",
            },
            "governance_summary": {
                "validators_passed": f"{receipt.validators_passed}/4",
                "blocked_at": receipt.blocked_at_stage or "None",
                "moat_contribution": f"+{receipt.moat_strength_delta:.2f}",
            },
            "before_after": receipt.before_after_diff.get("improvements", {}) if receipt.before_after_diff else {},
        }
