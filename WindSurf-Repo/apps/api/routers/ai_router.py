"""AI router - routes AI requests to the right provider (HuggingFace, etc.)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from db.models.ai_audit import AIAuditLog
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import logging
import time

# Import governance pipeline
from core.governance import GovernancePipeline, GovernanceRequest
from core.governance.schemas import OperationType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai-router"])

# Initialize governance pipeline
governance_pipeline = GovernancePipeline()


class AIRequest(BaseModel):
    operation_type: OperationType  # "chat", "transcribe", "embed", "caption", "summarize", "sentiment", "ner"
    provider: str = "huggingface"
    model: Optional[str] = None
    input_text: Optional[str] = None
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    temperature: float = 0.7
    max_tokens: int = 512
    language: Optional[str] = None
    
    # Demo-specific fields (added by demo gate)
    demo_token: Optional[str] = None
    demo_context: Optional[Dict[str, Any]] = None


class AIResponse(BaseModel):
    operation_type: str
    provider: str
    model: str
    result: Any
    cost_estimate: float = 0.0
    latency_ms: Optional[int] = None
    audit_log_id: Optional[str] = None
    
    # Governance pipeline results
    governance_passed: bool = True
    coherence_score: Optional[float] = None
    risk_level: Optional[str] = None
    patterns_applied: Optional[int] = None
    blocked_at_stage: Optional[str] = None
    block_reason: Optional[str] = None
    
    # Value metrics (if available)
    time_saved_minutes: Optional[float] = None
    cost_avoided_usd: Optional[float] = None
    risk_reduction_score: Optional[float] = None


@router.post("/execute", response_model=AIResponse)
async def execute_ai_operation(
    request: AIRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """
    Execute any AI operation through the DOMINANCE SAAS DOCTRINE v4 governance pipeline.
    
    This is the canonical entrypoint - ALL AI operations go through governance.
    No exceptions. No direct provider calls.
    """
    start = time.time()

    try:
        # Get workspace context for governance
        workspace_ctx = await _get_workspace_context(workspace_id, db)
        
        # Create governance request
        governance_request = GovernanceRequest(
            operation_type=request.operation_type,
            input_text=request.input_text,
            messages=request.messages,
            audio_url=request.audio_url,
            image_url=request.image_url,
            provider_override=request.provider,
            model_override=request.model,
            max_cost_override=None,  # Would come from tier limits
            workspace_id=workspace_id,
            session_id=request.demo_context.get("session_id") if request.demo_context else None,
            demo_token=request.demo_token,
            lead_id=request.demo_context.get("lead_id") if request.demo_context else None
        )
        
        # Add temperature and max_tokens
        governance_request.temperature = request.temperature
        governance_request.max_tokens = request.max_tokens
        
        # Run governance pipeline
        logger.info(f"Running governance pipeline for {request.operation_type} operation")
        result = await governance_pipeline.run(governance_request, workspace_ctx)
        
        # Store execution record
        await _store_governance_run(result, db)
        
        # Log to AIAuditLog for compatibility
        log_id = str(uuid.uuid4())
        try:
            cost = float(result.execution_outcome.actual_cost)
            log = AIAuditLog(
                id=log_id,
                workspace_id=workspace_id,
                user_id="system",  # System operation
                operation_type=request.operation_type.value,
                provider=result.routing_decision.selected_provider,
                model=result.routing_decision.selected_model,
                input_preview=(request.input_text or "")[:500],
                input_hash="",  # Would need SHA256 hashing in production
                output_hash="",  # Would need SHA256 hashing in production
                cost=cost,
                actual_latency_ms=result.execution_outcome.actual_latency_ms,
            )
            db.add(log)
            db.commit()
        except Exception as log_err:
            logger.warning(f"Failed to write audit log: {log_err}")
            db.rollback()

        # Format response
        return AIResponse(
            operation_type=request.operation_type.value,
            provider=result.routing_decision.selected_provider,
            model=result.routing_decision.selected_model,
            result=result.execution_outcome.final_result,
            cost_estimate=float(result.execution_outcome.actual_cost),
            latency_ms=result.execution_outcome.actual_latency_ms,
            audit_log_id=log_id,
            
            # Governance pipeline results
            governance_passed=result.pipeline_passed,
            coherence_score=result.risk_scores.coherence_score,
            risk_level=result.risk_scores.overall_risk,
            patterns_applied=result.memory_gate_results.patterns_applied,
            blocked_at_stage=result.blocked_at_stage,
            block_reason=result.block_reason,
            
            # Value metrics
            time_saved_minutes=result.receipt_data.get("time_saved_minutes") if result.receipt_data else None,
            cost_avoided_usd=result.receipt_data.get("cost_avoided_usd") if result.receipt_data else None,
            risk_reduction_score=result.receipt_data.get("risk_reduction_score") if result.receipt_data else None,
        )

    except Exception as e:
        logger.error(f"Governance pipeline execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI operation failed: {str(e)}")


# Helper functions
async def _get_workspace_context(workspace_id: str, db: Session) -> Dict[str, Any]:
    """Get workspace context for governance pipeline."""
    
    # This would typically query the database for workspace info
    # For now, return mock context based on workspace
    
    return {
        "user_tier": "free",  # Would come from user/workspace relationship
        "workspace_policy": {
            "restricted_keywords": ["confidential", "proprietary"],
            "allow_pii": False,
        },
        "budget_remaining": 10.00,
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
        # Import here to avoid circular imports
        from db.models.governance import (
            GovernanceRun, IntentVector, RiskScores, ValidationResults,
            MemoryGateResults, ExecutionReceipt
        )
        
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


def _estimate_cost(operation_type: str, text: str, model: str) -> float:
    """Rough cost estimate for HuggingFace operations (free tier = near $0)."""
    tokens = len(text.split())
    cost_per_1k = {
        "chat": 0.0002,
        "embed": 0.00001,
        "transcribe": 0.006,  # per minute equivalent
        "caption": 0.00005,
        "summarize": 0.0002,
        "sentiment": 0.00001,
        "ner": 0.00001,
    }
    rate = cost_per_1k.get(operation_type, 0.0001)
    return round((tokens / 1000) * rate, 6)


@router.get("/providers")
async def list_providers():
    """List all available AI providers and their models."""
    return {
        "providers": [
            {
                "id": "huggingface",
                "name": "HuggingFace Inference API",
                "status": "active",
                "free_tier": True,
                "models": {
                    "chat": "mistralai/Mistral-7B-Instruct-v0.3",
                    "embed": "sentence-transformers/all-MiniLM-L6-v2",
                    "transcribe": "openai/whisper-large-v3",
                    "caption": "Salesforce/blip-image-captioning-large",
                    "ner": "dslim/bert-base-NER",
                    "musicgen": "facebook/musicgen-small",
                    "summarize": "facebook/bart-large-cnn",
                    "sentiment": "distilbert-base-uncased-finetuned-sst-2-english",
                },
            }
        ]
    }


@router.get("/test/{provider}")
async def test_provider(provider: str):
    """Test a provider connection with a simple inference."""
    if provider != "huggingface":
        raise HTTPException(status_code=400, detail="Only 'huggingface' supported")

    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        from apps.ai.contracts import ChatMessage
        hf = HuggingFaceProvider()
        result = await hf.chat(
            [ChatMessage(role="user", content="Say 'BYOS AI backend online' in 5 words.")],
            max_tokens=20,
        )
        return {"status": "ok", "provider": provider, "response": result.content, "model": hf.chat_model}
    except Exception as e:
        return {"status": "error", "provider": provider, "error": str(e)}
