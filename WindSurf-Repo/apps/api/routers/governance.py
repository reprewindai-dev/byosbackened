"""Governance router - run receipts, benchmarks, drift alerts."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel

from db.session import get_db
from apps.api.deps import get_current_workspace_id, get_current_user
from db.models.governance import (
    GovernanceRun, IntentVector, RiskScores, ValidationResults,
    MemoryGateResults, ExecutionReceipt, CommunityMemoryPattern
)
from core.governance import GovernancePipeline, GovernanceRequest
from core.governance.schemas import OperationType
from core.governance.smoke_relay import SmokeRelay

import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/governance", tags=["governance"])


class GovernanceExecuteRequest(BaseModel):
    """Request for governance pipeline execution."""
    
    # Core request data
    operation_type: OperationType
    input_text: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    
    # Optional overrides
    provider_override: Optional[str] = None
    model_override: Optional[str] = None
    max_cost_override: Optional[Decimal] = None
    temperature: float = 0.7
    max_tokens: int = 512
    
    # Demo context (added by demo gate)
    demo_context: Optional[Dict[str, Any]] = None


class GovernanceExecuteResponse(BaseModel):
    """Response from governance pipeline execution."""
    
    # Execution results
    request_id: str
    success: bool
    execution_time_ms: int
    
    # Results
    result: Any
    cost_estimate: float
    tokens_used: Optional[int]
    
    # Quality metrics
    coherence_score: float
    risk_level: str
    patterns_applied: int
    
    # Value metrics (if available)
    time_saved_minutes: Optional[float]
    cost_avoided_usd: Optional[float]
    risk_reduction_score: Optional[float]
    
    # Governance info
    blocked_at_stage: Optional[str]
    block_reason: Optional[str]
    validators_passed: int
    moat_contribution: float


class RunReceiptResponse(BaseModel):
    """Detailed execution receipt."""
    
    request_id: str
    execution_time_ms: int
    success: bool
    
    # Cost and performance
    estimated_cost: float
    actual_cost: float
    tokens_used: Optional[int]
    latency_ms: int
    
    # Quality metrics
    coherence_score: float
    risk_scores: Dict[str, float]
    overall_risk_level: str
    
    # Governance information
    patterns_applied: int
    validators_passed: int
    validators_failed: List[str]
    blocked_at_stage: Optional[str]
    block_reason: Optional[str]
    
    # ROI metrics
    time_saved_minutes: Optional[float]
    cost_avoided_usd: Optional[float]
    risk_reduction_score: Optional[float]
    before_after_diff: Optional[Dict[str, Any]]
    
    # Moat contribution
    moat_strength_delta: float
    community_patterns_contributed: int
    
    # Timestamp
    timestamp: datetime


class BenchmarkResponse(BaseModel):
    """Benchmark performance metrics."""
    
    period: str
    total_requests: int
    success_rate: float
    avg_execution_time_ms: float
    avg_cost_usd: float
    avg_coherence_score: float
    
    # Risk metrics
    avg_fracture_score: float
    avg_detrimental_score: float
    avg_drift_score: float
    
    # Governance metrics
    patterns_applied_per_request: float
    validator_success_rate: float
    memory_gate_success_rate: float
    
    # Value metrics
    total_time_saved_hours: float
    total_cost_avoided_usd: float
    moat_strength_increase: float


class DriftAlertResponse(BaseModel):
    """Drift detection alert."""
    
    alert_id: str
    workspace_id: str
    alert_type: str
    severity: str
    
    # Drift metrics
    current_drift_score: float
    baseline_drift_score: float
    drift_increase_percent: float
    
    # Affected metrics
    affected_operations: List[str]
    affected_providers: List[str]
    
    # Recommendations
    recommended_actions: List[str]
    
    # Timestamp
    detected_at: datetime
    resolved_at: Optional[datetime]


# Initialize governance pipeline
governance_pipeline = GovernancePipeline()
smoke_relay = SmokeRelay()


@router.post("/execute", response_model=GovernanceExecuteResponse)
async def execute_governed_operation(
    request: GovernanceExecuteRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db)
):
    """
    Execute AI operation through governance pipeline.
    
    This is the canonical entrypoint for all AI operations.
    Enforces DOMINANCE SAAS DOCTRINE v4:
    - Intent normalization
    - Risk assessment
    - Quality convergence
    - Provider routing
    - Hard block validation
    - Memory gate enforcement
    - Receipt generation
    """
    
    try:
        # Get workspace context
        workspace_ctx = await _get_workspace_context(workspace_id, db)
        
        # Create governance request
        governance_request = GovernanceRequest(
            operation_type=request.operation_type,
            input_text=request.input_text,
            messages=request.messages,
            audio_url=request.audio_url,
            image_url=request.image_url,
            provider_override=request.provider_override,
            model_override=request.model_override,
            max_cost_override=request.max_cost_override,
            workspace_id=workspace_id,
            session_id=request.demo_context.get("session_id") if request.demo_context else None,
            demo_token=request.demo_context.get("demo_token") if request.demo_context else None,
            lead_id=request.demo_context.get("lead_id") if request.demo_context else None
        )
        
        # Add temperature and max_tokens to request (these aren't in the base schema)
        governance_request.temperature = request.temperature
        governance_request.max_tokens = request.max_tokens
        
        # Run governance pipeline
        result = await governance_pipeline.run(governance_request, workspace_ctx)
        
        # Store execution record
        await _store_governance_run(result, db)
        
        # Format response
        response_data = GovernanceExecuteResponse(
            request_id=result.request_id,
            success=result.pipeline_passed,
            execution_time_ms=result.execution_time_ms,
            result=result.execution_outcome.final_result,
            cost_estimate=float(result.execution_outcome.actual_cost),
            tokens_used=result.execution_outcome.tokens_used,
            coherence_score=result.risk_scores.coherence_score,
            risk_level=result.risk_scores.overall_risk,
            patterns_applied=result.memory_gate_results.patterns_applied,
            time_saved_minutes=result.receipt_data.get("time_saved_minutes") if result.receipt_data else None,
            cost_avoided_usd=result.receipt_data.get("cost_avoided_usd") if result.receipt_data else None,
            risk_reduction_score=result.receipt_data.get("risk_reduction_score") if result.receipt_data else None,
            blocked_at_stage=result.blocked_at_stage,
            block_reason=result.block_reason,
            validators_passed=result.validation_results.validators_passed,
            moat_contribution=result.memory_gate_results.moat_strength_delta
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"Governance execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Governance pipeline execution failed: {str(e)}"
        )


@router.get("/receipts/{request_id}", response_model=RunReceiptResponse)
async def get_execution_receipt(
    request_id: str,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db)
):
    """Get detailed execution receipt for a specific request."""
    
    # Find governance run
    run = db.query(GovernanceRun).filter(
        GovernanceRun.request_id == request_id,
        GovernanceRun.workspace_id == workspace_id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution receipt not found"
        )
    
    # Get related data
    intent_vector = db.query(IntentVector).filter(IntentVector.governance_run_id == run.id).first()
    risk_scores = db.query(RiskScores).filter(RiskScores.governance_run_id == run.id).first()
    validation_results = db.query(ValidationResults).filter(ValidationResults.governance_run_id == run.id).first()
    memory_gate_results = db.query(MemoryGateResults).filter(MemoryGateResults.governance_run_id == run.id).first()
    execution_receipt = db.query(ExecutionReceipt).filter(ExecutionReceipt.governance_run_id == run.id).first()
    
    # Format response
    return RunReceiptResponse(
        request_id=run.request_id,
        execution_time_ms=run.execution_time_ms,
        success=run.pipeline_passed,
        estimated_cost=float(run.estimated_cost),
        actual_cost=float(run.actual_cost),
        tokens_used=run.tokens_used,
        latency_ms=run.latency_ms,
        coherence_score=risk_scores.coherence_score if risk_scores else 0.0,
        risk_scores={
            "fracture": risk_scores.fracture_score if risk_scores else 0.0,
            "detrimental": risk_scores.detrimental_score if risk_scores else 0.0,
            "drift": risk_scores.drift_score if risk_scores else 0.0,
            "coherence": risk_scores.coherence_score if risk_scores else 0.0,
        },
        overall_risk_level=risk_scores.overall_risk if risk_scores else "unknown",
        patterns_applied=memory_gate_results.patterns_applied if memory_gate_results else 0,
        validators_passed=validation_results.validators_passed if validation_results else 0,
        validators_failed=validation_results.blocked_reasons if validation_results else [],
        blocked_at_stage=run.blocked_at_stage,
        block_reason=run.block_reason,
        time_saved_minutes=execution_receipt.time_saved_minutes if execution_receipt else None,
        cost_avoided_usd=float(execution_receipt.cost_avoided_usd) if execution_receipt and execution_receipt.cost_avoided_usd else None,
        risk_reduction_score=execution_receipt.risk_reduction_score if execution_receipt else None,
        before_after_diff=execution_receipt.before_after_diff if execution_receipt else None,
        moat_strength_delta=execution_receipt.moat_strength_delta if execution_receipt else 0.0,
        community_patterns_contributed=execution_receipt.community_patterns_contributed if execution_receipt else 0,
        timestamp=run.started_at
    )


@router.get("/receipts", response_model=List[RunReceiptResponse])
async def list_execution_receipts(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db)
):
    """List execution receipts for the workspace."""
    
    # Get governance runs with pagination
    runs = db.query(GovernanceRun).filter(
        GovernanceRun.workspace_id == workspace_id
    ).order_by(GovernanceRun.started_at.desc()).offset(offset).limit(limit).all()
    
    receipts = []
    for run in runs:
        # Get related data
        risk_scores = db.query(RiskScores).filter(RiskScores.governance_run_id == run.id).first()
        validation_results = db.query(ValidationResults).filter(ValidationResults.governance_run_id == run.id).first()
        memory_gate_results = db.query(MemoryGateResults).filter(MemoryGateResults.governance_run_id == run.id).first()
        execution_receipt = db.query(ExecutionReceipt).filter(ExecutionReceipt.governance_run_id == run.id).first()
        
        receipts.append(RunReceiptResponse(
            request_id=run.request_id,
            execution_time_ms=run.execution_time_ms,
            success=run.pipeline_passed,
            estimated_cost=float(run.estimated_cost),
            actual_cost=float(run.actual_cost),
            tokens_used=run.tokens_used,
            latency_ms=run.latency_ms,
            coherence_score=risk_scores.coherence_score if risk_scores else 0.0,
            risk_scores={
                "fracture": risk_scores.fracture_score if risk_scores else 0.0,
                "detrimental": risk_scores.detrimental_score if risk_scores else 0.0,
                "drift": risk_scores.drift_score if risk_scores else 0.0,
                "coherence": risk_scores.coherence_score if risk_scores else 0.0,
            },
            overall_risk_level=risk_scores.overall_risk if risk_scores else "unknown",
            patterns_applied=memory_gate_results.patterns_applied if memory_gate_results else 0,
            validators_passed=validation_results.validators_passed if validation_results else 0,
            validators_failed=validation_results.blocked_reasons if validation_results else [],
            blocked_at_stage=run.blocked_at_stage,
            block_reason=run.block_reason,
            time_saved_minutes=execution_receipt.time_saved_minutes if execution_receipt else None,
            cost_avoided_usd=float(execution_receipt.cost_avoided_usd) if execution_receipt and execution_receipt.cost_avoided_usd else None,
            risk_reduction_score=execution_receipt.risk_reduction_score if execution_receipt else None,
            before_after_diff=execution_receipt.before_after_diff if execution_receipt else None,
            moat_strength_delta=execution_receipt.moat_strength_delta if execution_receipt else 0.0,
            community_patterns_contributed=execution_receipt.community_patterns_contributed if execution_receipt else 0,
            timestamp=run.started_at
        ))
    
    return receipts


@router.get("/benchmarks", response_model=BenchmarkResponse)
async def get_performance_benchmarks(
    period: str = Query(default="7d", regex="^(1d|7d|30d)$"),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db)
):
    """Get performance benchmarks for the workspace."""
    
    # Calculate period start/end
    period_days = {"1d": 1, "7d": 7, "30d": 30}
    days = period_days.get(period, 7)
    period_start = datetime.utcnow() - timedelta(days=days)
    
    # Get governance runs for period
    runs = db.query(GovernanceRun).filter(
        GovernanceRun.workspace_id == workspace_id,
        GovernanceRun.started_at >= period_start
    ).all()
    
    if not runs:
        return BenchmarkResponse(
            period=period,
            total_requests=0,
            success_rate=0.0,
            avg_execution_time_ms=0.0,
            avg_cost_usd=0.0,
            avg_coherence_score=0.0,
            avg_fracture_score=0.0,
            avg_detrimental_score=0.0,
            avg_drift_score=0.0,
            patterns_applied_per_request=0.0,
            validator_success_rate=0.0,
            memory_gate_success_rate=0.0,
            total_time_saved_hours=0.0,
            total_cost_avoided_usd=0.0,
            moat_strength_increase=0.0
        )
    
    # Calculate metrics
    total_requests = len(runs)
    successful_requests = sum(1 for run in runs if run.pipeline_passed)
    success_rate = successful_requests / total_requests
    
    avg_execution_time_ms = sum(run.execution_time_ms for run in runs) / total_requests
    avg_cost_usd = sum(float(run.actual_cost) for run in runs) / total_requests
    
    # Get risk scores
    run_ids = [run.id for run in runs]
    risk_scores_list = db.query(RiskScores).filter(RiskScores.governance_run_id.in_(run_ids)).all()
    
    if risk_scores_list:
        avg_coherence_score = sum(rs.coherence_score for rs in risk_scores_list) / len(risk_scores_list)
        avg_fracture_score = sum(rs.fracture_score for rs in risk_scores_list) / len(risk_scores_list)
        avg_detrimental_score = sum(rs.detrimental_score for rs in risk_scores_list) / len(risk_scores_list)
        avg_drift_score = sum(rs.drift_score for rs in risk_scores_list) / len(risk_scores_list)
    else:
        avg_coherence_score = avg_fracture_score = avg_detrimental_score = avg_drift_score = 0.0
    
    # Get governance metrics
    validation_results_list = db.query(ValidationResults).filter(ValidationResults.governance_run_id.in_(run_ids)).all()
    memory_gate_results_list = db.query(MemoryGateResults).filter(MemoryGateResults.governance_run_id.in_(run_ids)).all()
    
    if validation_results_list:
        validator_success_rate = sum(1 for vr in validation_results_list if vr.all_validators_passed) / len(validation_results_list)
    else:
        validator_success_rate = 0.0
    
    if memory_gate_results_list:
        patterns_applied_total = sum(mgr.patterns_applied for mgr in memory_gate_results_list)
        patterns_applied_per_request = patterns_applied_total / total_requests
        memory_gate_success_rate = sum(1 for mgr in memory_gate_results_list if mgr.gate_passed) / len(memory_gate_results_list)
        moat_strength_increase = sum(mgr.moat_strength_delta for mgr in memory_gate_results_list)
    else:
        patterns_applied_per_request = 0.0
        memory_gate_success_rate = 0.0
        moat_strength_increase = 0.0
    
    # Get value metrics
    execution_receipts_list = db.query(ExecutionReceipt).filter(ExecutionReceipt.governance_run_id.in_(run_ids)).all()
    
    if execution_receipts_list:
        total_time_saved_minutes = sum(er.time_saved_minutes or 0 for er in execution_receipts_list)
        total_time_saved_hours = total_time_saved_minutes / 60
        total_cost_avoided_usd = sum(float(er.cost_avoided_usd or 0) for er in execution_receipts_list)
    else:
        total_time_saved_hours = 0.0
        total_cost_avoided_usd = 0.0
    
    return BenchmarkResponse(
        period=period,
        total_requests=total_requests,
        success_rate=success_rate,
        avg_execution_time_ms=avg_execution_time_ms,
        avg_cost_usd=avg_cost_usd,
        avg_coherence_score=avg_coherence_score,
        avg_fracture_score=avg_fracture_score,
        avg_detrimental_score=avg_detrimental_score,
        avg_drift_score=avg_drift_score,
        patterns_applied_per_request=patterns_applied_per_request,
        validator_success_rate=validator_success_rate,
        memory_gate_success_rate=memory_gate_success_rate,
        total_time_saved_hours=total_time_saved_hours,
        total_cost_avoided_usd=total_cost_avoided_usd,
        moat_strength_increase=moat_strength_increase
    )


@router.get("/drift-alerts", response_model=List[DriftAlertResponse])
async def get_drift_alerts(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db)
):
    """Get drift detection alerts for the workspace."""
    
    # For now, return empty list
    # In production, this would query a drift alerts table or calculate drift in real-time
    return []


@router.get("/patterns/analytics")
async def get_pattern_analytics(
    workspace_id: str = Depends(get_current_workspace_id)
):
    """Get community memory pattern analytics."""
    
    analytics = governance_pipeline.memory_gate.get_pattern_analytics()
    return analytics


@router.get("/health")
async def governance_health():
    """Health check for governance pipeline."""
    
    return {
        "status": "healthy",
        "pipeline_version": "v4.0",
        "components": {
            "navigator": "operational",
            "listener": "operational",
            "risk_assessment": "operational",
            "convergeos": "operational",
            "ecobe_routing": "operational",
            "watchtower": "operational",
            "memory_gate": "operational",
            "smoke_relay": "operational"
        },
        "patterns_stored": len(governance_pipeline.memory_gate.patterns_db),
        "moat_strength": "building"
    }


# Helper functions
async def _get_workspace_context(workspace_id: str, db: Session) -> Dict[str, Any]:
    """Get workspace context for governance pipeline."""
    
    # This would typically query the database for workspace info
    # For now, return mock context
    
    return {
        "user_tier": "free",  # Would come from user/workspace relationship
        "workspace_policy": {
            "restricted_keywords": ["confidential", "proprietary"],
            "allow_pii": False,
        },
        "budget_remaining": Decimal("10.00"),
        "tier_limits": {
            "max_cost_per_request": 0.01,
            "daily_cost_limit": 1.0,
        },
        "prior_runs": [],  # Would query recent runs
        "user_preferences": {},
        "ip_address": None,
        "user_agent": None,
    }


async def _store_governance_run(result, db: Session):
    """Store governance run results in database."""
    
    try:
        # Create governance run record
        run = GovernanceRun(
            request_id=result.request_id,
            workspace_id=result.execution_context.workspace_id,
            user_id=result.execution_context.user_id,
            user_tier=result.execution_context.user_tier,
            operation_type=result.operation_plan.operation_type,
            operation_plan=result.operation_plan.dict(),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            execution_time_ms=result.execution_time_ms,
            pipeline_passed=result.pipeline_passed,
            blocked_at_stage=result.blocked_at_stage,
            block_reason=result.block_reason,
            estimated_cost=result.routing_decision.expected_cost,
            actual_cost=result.execution_outcome.actual_cost,
            tokens_used=result.execution_outcome.tokens_used,
            latency_ms=result.execution_outcome.actual_latency_ms,
            selected_provider=result.routing_decision.selected_provider,
            selected_model=result.routing_decision.selected_model,
            routing_reasoning=result.routing_decision.reasoning,
        )
        
        db.add(run)
        db.flush()  # Get the ID
        
        # Store intent vector
        intent_vector = IntentVector(
            governance_run_id=run.id,
            primary_intent=result.intent_vector.primary_intent,
            secondary_intent=result.intent_vector.secondary_intent,
            content_type=result.intent_vector.content_type,
            complexity_score=result.intent_vector.complexity_score,
            sensitivity_level=result.intent_vector.sensitivity_level,
            business_domain=result.intent_vector.business_domain,
            use_case=result.intent_vector.use_case,
            expected_quality_threshold=result.intent_vector.expected_quality_threshold,
            cost_sensitivity=result.intent_vector.cost_sensitivity,
            latency_requirement_ms=result.intent_vector.latency_requirement_ms,
            session_id=result.intent_vector.session_id,
        )
        
        db.add(intent_vector)
        
        # Store risk scores
        risk_scores = RiskScores(
            governance_run_id=run.id,
            fracture_score=result.risk_scores.fracture_score,
            detrimental_score=result.risk_scores.detrimental_score,
            drift_score=result.risk_scores.drift_score,
            coherence_score=result.risk_scores.coherence_score,
            overall_risk=result.risk_scores.overall_risk,
            risk_factors=result.risk_scores.risk_factors,
        )
        
        db.add(risk_scores)
        
        # Store validation results
        validation_results = ValidationResults(
            governance_run_id=run.id,
            compliance_passed=result.validation_results.compliance_passed,
            budget_passed=result.validation_results.budget_passed,
            hallucination_check_passed=result.validation_results.hallucination_check_passed,
            schema_validation_passed=result.validation_results.schema_validation_passed,
            all_validators_passed=result.validation_results.all_validators_passed,
            blocked_reasons=result.validation_results.blocked_reasons,
            warnings=result.validation_results.warnings,
        )
        
        db.add(validation_results)
        
        # Store memory gate results
        memory_gate_results = MemoryGateResults(
            governance_run_id=run.id,
            patterns_retrieved=result.memory_gate_results.patterns_retrieved,
            patterns_applied=result.memory_gate_results.patterns_applied,
            anti_generic_score=result.memory_gate_results.anti_generic_score,
            pattern_sources=result.memory_gate_results.pattern_sources,
            moat_strength_delta=result.memory_gate_results.moat_strength_delta,
            gate_passed=result.memory_gate_results.gate_passed,
            gate_reason=result.memory_gate_results.gate_reason,
        )
        
        db.add(memory_gate_results)
        
        # Store execution receipt if available
        if result.receipt_data:
            execution_receipt = ExecutionReceipt(
                governance_run_id=run.id,
                time_saved_minutes=result.receipt_data.get("time_saved_minutes"),
                cost_avoided_usd=result.receipt_data.get("cost_avoided_usd"),
                risk_reduction_score=result.receipt_data.get("risk_reduction_score"),
                before_after_diff=result.receipt_data.get("before_after_diff"),
                moat_strength_delta=result.receipt_data.get("moat_strength_delta", 0.0),
                community_patterns_contributed=result.receipt_data.get("community_patterns_contributed", 0),
                receipt_data=result.receipt_data,
            )
            
            db.add(execution_receipt)
        
        db.commit()
        logger.info(f"Stored governance run {result.request_id}")
        
    except Exception as e:
        logger.error(f"Failed to store governance run: {e}")
        db.rollback()
        # Don't raise - the execution succeeded, just storage failed
