"""Strict request/response contracts for governance pipeline."""

from decimal import Decimal
from typing import Optional, Dict, List, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime


class OperationType(str, Enum):
    """Supported AI operation types."""
    CHAT = "chat"
    EMBED = "embed"
    TRANSCRIBE = "transcribe"
    CAPTION = "caption"
    SUMMARIZE = "summarize"
    SENTIMENT = "sentiment"
    NER = "ner"


class ProviderStrategy(str, Enum):
    """Provider routing strategies."""
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    SPEED_OPTIMIZED = "speed_optimized"
    HYBRID = "hybrid"


class IntentVector(BaseModel):
    """Normalized intent representation for analytics and moat loops."""
    
    # Core intent classification
    primary_intent: str = Field(..., description="Primary intent category")
    secondary_intent: Optional[str] = Field(None, description="Secondary intent category")
    
    # Content characteristics
    content_type: str = Field(..., description="Type of content being processed")
    complexity_score: float = Field(ge=0.0, le=1.0, description="Content complexity (0-1)")
    sensitivity_level: str = Field(..., description="Data sensitivity (public, internal, confidential, restricted)")
    
    # Business context
    business_domain: str = Field(..., description="Business domain/vertical")
    use_case: str = Field(..., description="Specific use case within domain")
    
    # Operational parameters
    expected_quality_threshold: float = Field(ge=0.0, le=1.0, default=0.8, description="Minimum acceptable quality")
    cost_sensitivity: float = Field(ge=0.0, le=1.0, description="Cost sensitivity (0=cost-insensitive, 1=cost-sensitive)")
    latency_requirement_ms: Optional[int] = Field(None, description="Maximum acceptable latency")
    
    # Metadata for moat loops
    session_id: Optional[str] = Field(None, description="Session identifier for tracking")
    user_tier: str = Field(default="free", description="User tier (free, pro, enterprise)")
    workspace_id: str = Field(..., description="Workspace identifier")
    
    # Sovereign governance extensions
    entropy_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Request entropy score")
    fracture_detected: Optional[bool] = Field(None, description="Multi-domain fracture detected")
    governance_tier_boost: Optional[str] = Field(None, description="Governance tier boost based on ambiguity")
    
    @validator('complexity_score')
    def validate_complexity(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Complexity score must be between 0 and 1')
        return v


class OperationPlan(BaseModel):
    """Structured execution plan derived from intent."""
    
    # Operation details
    operation_type: OperationType
    provider_strategy: ProviderStrategy = ProviderStrategy.HYBRID
    model_preferences: Optional[List[str]] = Field(None, description="Preferred models in order")
    
    # Constraints
    max_cost_usd: Optional[Decimal] = Field(None, description="Maximum cost in USD")
    min_quality_score: float = Field(ge=0.0, le=1.0, default=0.7, description="Minimum quality score")
    max_latency_ms: Optional[int] = Field(None, description="Maximum latency in milliseconds")
    
    # Execution parameters
    temperature: float = Field(ge=0.0, le=2.0, default=0.7, description="Generation temperature")
    max_tokens: int = Field(ge=1, le=4096, default=512, description="Maximum tokens to generate")
    
    # Governance flags
    requires_compliance_check: bool = Field(default=True, description="Whether compliance check is required")
    requires_memory_gate: bool = Field(default=True, description="Whether community memory gate is required")
    max_retry_attempts: int = Field(ge=1, le=5, default=3, description="Maximum retry attempts for convergence")
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError('Temperature must be between 0 and 2')
        return v


class ExecutionContext(BaseModel):
    """Complete execution context for governance pipeline."""
    
    # Request metadata
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")
    
    # User and workspace context
    user_id: Optional[str] = Field(None, description="User identifier")
    workspace_id: str = Field(..., description="Workspace identifier")
    user_tier: str = Field(default="free", description="User tier")
    
    # Policy and limits
    workspace_policy: Dict[str, Any] = Field(default_factory=dict, description="Workspace-specific policies")
    budget_remaining: Optional[Decimal] = Field(None, description="Remaining budget for period")
    tier_limits: Dict[str, Any] = Field(default_factory=dict, description="Tier-specific limits")
    
    # Historical context
    prior_runs: List[Dict[str, Any]] = Field(default_factory=list, description="Recent similar runs")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    
    # Security context
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    risk_score: float = Field(ge=0.0, le=1.0, default=0.1, description="Initial risk assessment")


class RiskScores(BaseModel):
    """All risk assessment scores for a request."""
    
    # Core risk scores
    fracture_score: float = Field(ge=0.0, le=1.0, description="Input contradictions/missing fields score")
    detrimental_score: float = Field(ge=0.0, le=1.0, description="Policy violation/unsafe content score")
    drift_score: float = Field(ge=0.0, le=1.0, description="Deviation from norms score")
    
    # Coherence score (VCTT τ)
    coherence_score: float = Field(ge=0.0, le=1.0, description="VCTT coherence score (τ)")
    
    # Overall risk assessment
    overall_risk: str = Field(..., description="Overall risk level (low, medium, high, critical)")
    risk_factors: List[str] = Field(default_factory=list, description="Specific risk factors identified")
    assigned_tier: Optional[str] = Field(None, description="Governance tier assigned based on risk profile")
    
    @validator('overall_risk')
    def validate_risk_level(cls, v):
        if v not in ['low', 'medium', 'high', 'critical']:
            raise ValueError('Risk level must be low, medium, high, or critical')
        return v


class ValidationResults(BaseModel):
    """Results from Watchtower validators."""
    
    # Individual validator results
    compliance_passed: bool = Field(..., description="Compliance validator result")
    budget_passed: bool = Field(..., description="Budget validator result")
    hallucination_check_passed: bool = Field(..., description="Hallucination validator result")
    schema_validation_passed: bool = Field(..., description="Schema validation result")
    
    # Overall validation
    all_validators_passed: bool = Field(..., description="Whether all validators passed")
    blocked_reasons: List[str] = Field(default_factory=list, description="Reasons for blocking if any")
    warnings: List[str] = Field(default_factory=list, description="Warnings from validators")


class MemoryGateResults(BaseModel):
    """Results from Community Memory Gate."""
    
    # Memory retrieval
    patterns_retrieved: int = Field(ge=0, description="Number of patterns retrieved")
    patterns_applied: int = Field(ge=0, description="Number of patterns applied")
    anti_generic_score: float = Field(ge=0.0, le=1.0, description="Anti-generic compliance score")
    
    # Moat contribution
    pattern_sources: List[str] = Field(default_factory=list, description="Sources of applied patterns")
    moat_strength_delta: float = Field(ge=-1.0, le=1.0, description="Change in moat strength")
    
    # Gate decision
    gate_passed: bool = Field(..., description="Whether memory gate was passed")
    gate_reason: Optional[str] = Field(None, description="Reason for gate failure")


class RoutingDecision(BaseModel):
    """Provider routing decision from ECOBE."""
    
    selected_provider: str = Field(..., description="Selected AI provider")
    selected_model: str = Field(..., description="Selected model within provider")
    reasoning: str = Field(..., description="Reasoning for selection")
    
    # Predicted performance
    expected_cost: Decimal = Field(..., description="Expected cost in USD")
    expected_quality_score: float = Field(ge=0.0, le=1.0, description="Expected quality score")
    expected_latency_ms: int = Field(ge=0, description="Expected latency in milliseconds")
    
    # Alternatives considered
    alternatives_considered: List[Dict[str, Any]] = Field(default_factory=list, description="Alternative providers considered")
    ml_enhanced: bool = Field(default=False, description="Whether ML routing was used")


class ExecutionOutcome(BaseModel):
    """Final execution outcome and results."""
    
    # Execution status
    success: bool = Field(..., description="Whether execution succeeded")
    final_result: Any = Field(..., description="Final execution result")
    attempts_made: int = Field(ge=1, description="Number of attempts made")
    
    # Performance metrics
    actual_cost: Decimal = Field(..., description="Actual cost incurred")
    actual_quality_score: Optional[float] = Field(ge=0.0, le=1.0, description="Actual quality score if measured")
    actual_latency_ms: int = Field(ge=0, description="Actual latency in milliseconds")
    tokens_used: Optional[int] = Field(ge=0, description="Tokens used if applicable")
    
    # Convergence information
    convergence_achieved: bool = Field(default=True, description="Whether convergence was achieved")
    convergence_iterations: int = Field(ge=0, description="Number of convergence iterations")


class GovernanceResult(BaseModel):
    """Complete governance pipeline result."""
    
    # Metadata
    request_id: str = Field(..., description="Request identifier")
    execution_time_ms: int = Field(ge=0, description="Total pipeline execution time")
    
    # Pipeline components
    intent_vector: IntentVector = Field(..., description="Normalized intent vector")
    operation_plan: OperationPlan = Field(..., description="Derived operation plan")
    execution_context: ExecutionContext = Field(..., description="Execution context")
    
    # Assessment results
    risk_scores: RiskScores = Field(..., description="Risk assessment scores")
    validation_results: ValidationResults = Field(..., description="Watchtower validation results")
    memory_gate_results: MemoryGateResults = Field(..., description="Memory gate results")
    routing_decision: RoutingDecision = Field(..., description="Provider routing decision")
    execution_outcome: ExecutionOutcome = Field(..., description="Final execution outcome")
    
    # Final decision
    pipeline_passed: bool = Field(..., description="Whether entire pipeline passed")
    blocked_at_stage: Optional[str] = Field(None, description="Stage where execution was blocked")
    block_reason: Optional[str] = Field(None, description="Reason for blocking")
    
    # Receipt information
    receipt_generated: bool = Field(default=True, description="Whether receipt was generated")
    receipt_data: Dict[str, Any] = Field(default_factory=dict, description="Receipt data for demo/ROI")


class GovernanceRequest(BaseModel):
    """Input request for governance pipeline."""
    
    # Core request data
    operation_type: OperationType
    input_text: Optional[str] = Field(None, description="Text input for processing")
    messages: Optional[List[Dict[str, str]]] = Field(None, description="Chat messages")
    audio_url: Optional[str] = Field(None, description="Audio file URL")
    image_url: Optional[str] = Field(None, description="Image file URL")
    
    # Optional overrides
    provider_override: Optional[str] = Field(None, description="Override provider selection")
    model_override: Optional[str] = Field(None, description="Override model selection")
    max_cost_override: Optional[Decimal] = Field(None, description="Override maximum cost")
    
    # Context
    workspace_id: str = Field(..., description="Workspace identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    # Demo-specific
    demo_token: Optional[str] = Field(None, description="Demo execution token")
    lead_id: Optional[str] = Field(None, description="Lead identifier for demo tracking")
    
    # Execution parameters
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: Optional[int] = Field(512, ge=1, le=4096, description="Maximum tokens to generate")
