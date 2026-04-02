"""Database models for governance pipeline - runs, scores, intent vectors, blocks, memory patterns."""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, Boolean, JSON, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from db.session import Base
import uuid
from datetime import datetime


class GovernanceRun(Base):
    """Main governance run record - tracks every pipeline execution."""
    
    __tablename__ = "governance_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Request metadata
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user_tier = Column(String(50), nullable=False, default="free")
    
    # Operation details
    operation_type = Column(String(100), nullable=False)
    operation_plan = Column(JSONB, nullable=False)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time_ms = Column(Integer, nullable=False)
    
    # Results
    pipeline_passed = Column(Boolean, nullable=False, default=False)
    blocked_at_stage = Column(String(100), nullable=True)
    block_reason = Column(Text, nullable=True)
    
    # Cost and performance
    estimated_cost = Column(DECIMAL(10, 6), nullable=False, default=0)
    actual_cost = Column(DECIMAL(10, 6), nullable=False, default=0)
    tokens_used = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=False)
    
    # Provider information
    selected_provider = Column(String(100), nullable=True)
    selected_model = Column(String(200), nullable=True)
    routing_reasoning = Column(Text, nullable=True)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="governance_runs")
    user = relationship("User", back_populates="governance_runs")
    
    # Related records
    intent_vector = relationship("IntentVector", back_populates="governance_run", uselist=False)
    risk_scores = relationship("RiskScores", back_populates="governance_run", uselist=False)
    validation_results = relationship("ValidationResults", back_populates="governance_run", uselist=False)
    memory_gate_results = relationship("MemoryGateResults", back_populates="governance_run", uselist=False)
    execution_receipt = relationship("ExecutionReceipt", back_populates="governance_run", uselist=False)


class IntentVector(Base):
    """Intent vector records - normalized intent representation."""
    
    __tablename__ = "intent_vectors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    governance_run_id = Column(UUID(as_uuid=True), ForeignKey("governance_runs.id"), unique=True, nullable=False)
    
    # Core intent classification
    primary_intent = Column(String(100), nullable=False)
    secondary_intent = Column(String(100), nullable=True)
    
    # Content characteristics
    content_type = Column(String(100), nullable=False)
    complexity_score = Column(Float, nullable=False)
    sensitivity_level = Column(String(50), nullable=False)
    
    # Business context
    business_domain = Column(String(100), nullable=False)
    use_case = Column(String(100), nullable=False)
    
    # Operational parameters
    expected_quality_threshold = Column(Float, nullable=False)
    cost_sensitivity = Column(Float, nullable=False)
    latency_requirement_ms = Column(Integer, nullable=True)
    
    # Metadata
    session_id = Column(String(255), nullable=True)
    
    # Relationship
    governance_run = relationship("GovernanceRun", back_populates="intent_vector")


class RiskScores(Base):
    """Risk assessment scores for each governance run."""
    
    __tablename__ = "risk_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    governance_run_id = Column(UUID(as_uuid=True), ForeignKey("governance_runs.id"), unique=True, nullable=False)
    
    # Core risk scores
    fracture_score = Column(Float, nullable=False)
    detrimental_score = Column(Float, nullable=False)
    drift_score = Column(Float, nullable=False)
    
    # Coherence score (VCTT τ)
    coherence_score = Column(Float, nullable=False)
    
    # Overall risk assessment
    overall_risk = Column(String(50), nullable=False)
    risk_factors = Column(JSONB, nullable=False, default=list)
    
    # Relationship
    governance_run = relationship("GovernanceRun", back_populates="risk_scores")


class ValidationResults(Base):
    """Watchtower validation results."""
    
    __tablename__ = "validation_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    governance_run_id = Column(UUID(as_uuid=True), ForeignKey("governance_runs.id"), unique=True, nullable=False)
    
    # Individual validator results
    compliance_passed = Column(Boolean, nullable=False)
    budget_passed = Column(Boolean, nullable=False)
    hallucination_check_passed = Column(Boolean, nullable=False)
    schema_validation_passed = Column(Boolean, nullable=False)
    
    # Overall validation
    all_validators_passed = Column(Boolean, nullable=False)
    blocked_reasons = Column(JSONB, nullable=False, default=list)
    warnings = Column(JSONB, nullable=False, default=list)
    
    # Relationship
    governance_run = relationship("GovernanceRun", back_populates="validation_results")


class MemoryGateResults(Base):
    """Community memory gate results."""
    
    __tablename__ = "memory_gate_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    governance_run_id = Column(UUID(as_uuid=True), ForeignKey("governance_runs.id"), unique=True, nullable=False)
    
    # Memory retrieval
    patterns_retrieved = Column(Integer, nullable=False)
    patterns_applied = Column(Integer, nullable=False)
    anti_generic_score = Column(Float, nullable=False)
    
    # Moat contribution
    pattern_sources = Column(JSONB, nullable=False, default=list)
    moat_strength_delta = Column(Float, nullable=False)
    
    # Gate decision
    gate_passed = Column(Boolean, nullable=False)
    gate_reason = Column(Text, nullable=True)
    
    # Relationship
    governance_run = relationship("GovernanceRun", back_populates="memory_gate_results")


class ExecutionReceipt(Base):
    """Execution receipt with ROI metrics and value tracking."""
    
    __tablename__ = "execution_receipts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    governance_run_id = Column(UUID(as_uuid=True), ForeignKey("governance_runs.id"), unique=True, nullable=False)
    
    # ROI and value metrics
    time_saved_minutes = Column(Float, nullable=True)
    cost_avoided_usd = Column(DECIMAL(10, 2), nullable=True)
    risk_reduction_score = Column(Float, nullable=True)
    
    # Before/after comparison
    before_after_diff = Column(JSONB, nullable=True)
    
    # Moat contribution
    moat_strength_delta = Column(Float, nullable=False)
    community_patterns_contributed = Column(Integer, nullable=False)
    
    # Receipt metadata
    receipt_generated = Column(Boolean, nullable=False, default=True)
    receipt_data = Column(JSONB, nullable=True)
    
    # Relationship
    governance_run = relationship("GovernanceRun", back_populates="execution_receipt")


class CommunityMemoryPattern(Base):
    """Community memory patterns - data moat #1."""
    
    __tablename__ = "community_memory_patterns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pattern_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Pattern classification
    intent_category = Column(String(100), nullable=False, index=True)
    business_domain = Column(String(100), nullable=False, index=True)
    use_case = Column(String(100), nullable=False)
    
    # Pattern template
    pattern_template = Column(Text, nullable=False)
    
    # Success metrics
    success_rate = Column(Float, nullable=False)
    usage_count = Column(Integer, nullable=False, default=0)
    quality_score = Column(Float, nullable=False)
    cost_efficiency = Column(Float, nullable=False)
    anti_generic_score = Column(Float, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Source tracking
    source_workspaces = Column(JSONB, nullable=False, default=list)
    contributor_workspaces = Column(JSONB, nullable=False, default=list)
    
    # Pattern metadata
    pattern_hash = Column(String(64), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    pattern_applications = relationship("PatternApplication", back_populates="pattern")


class PatternApplication(Base):
    """Records of pattern applications - tracks moat contribution."""
    
    __tablename__ = "pattern_applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to pattern and run
    pattern_id = Column(String(255), ForeignKey("community_memory_patterns.pattern_id"), nullable=False)
    governance_run_id = Column(UUID(as_uuid=True), ForeignKey("governance_runs.id"), nullable=False)
    
    # Application details
    relevance_score = Column(Float, nullable=False)
    application_success = Column(Boolean, nullable=False)
    quality_contribution = Column(Float, nullable=False)
    
    # Timing
    applied_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    pattern = relationship("CommunityMemoryPattern", back_populates="pattern_applications")
    governance_run = relationship("GovernanceRun")


class GovernanceBlock(Base):
    """Records of governance blocks - for analytics and improvement."""
    
    __tablename__ = "governance_blocks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(255), nullable=False, index=True)
    
    # Block details
    blocked_at_stage = Column(String(100), nullable=False, index=True)
    block_reason = Column(Text, nullable=False)
    block_category = Column(String(100), nullable=False)  # compliance, budget, memory_gate, etc.
    
    # Request context
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user_tier = Column(String(50), nullable=False)
    operation_type = Column(String(100), nullable=False)
    
    # Risk scores at time of block
    fracture_score = Column(Float, nullable=True)
    detrimental_score = Column(Float, nullable=True)
    drift_score = Column(Float, nullable=True)
    coherence_score = Column(Float, nullable=True)
    
    # Timing
    blocked_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Resolution
    resolved = Column(Boolean, nullable=False, default=False)
    resolution_method = Column(String(100), nullable=True)  # user_action, auto_retry, appeal, etc.
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    workspace = relationship("Workspace")
    user = relationship("User")


class CollapseMonitor(Base):
    """Collapse prevention monitors - detects repeated failures and degrading performance."""
    
    __tablename__ = "collapse_monitors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Monitor scope
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    monitor_type = Column(String(50), nullable=False)  # workspace, user, operation_type, provider
    
    # Monitor configuration
    failure_threshold = Column(Integer, nullable=False, default=5)  # failures per period
    monitoring_period_minutes = Column(Integer, nullable=False, default=60)
    cost_threshold_usd = Column(DECIMAL(10, 2), nullable=True)
    drift_threshold = Column(Float, nullable=True)
    
    # Current state
    current_failure_count = Column(Integer, nullable=False, default=0)
    current_drift_score = Column(Float, nullable=False, default=0.0)
    current_cost_total = Column(DECIMAL(10, 2), nullable=False, default=0)
    
    # Monitor status
    is_active = Column(Boolean, nullable=False, default=True)
    is_triggered = Column(Boolean, nullable=False, default=False)
    trigger_reason = Column(Text, nullable=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Actions taken
    auto_degrade_applied = Column(Boolean, nullable=False, default=False)
    kill_switch_triggered = Column(Boolean, nullable=False, default=False)
    notification_sent = Column(Boolean, nullable=False, default=False)
    
    # Timing
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_reset_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    next_reset_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    workspace = relationship("Workspace")
    user = relationship("User")


class GovernanceAnalytics(Base):
    """Aggregated governance analytics for performance monitoring."""
    
    __tablename__ = "governance_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Analytics period
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    granularity = Column(String(20), nullable=False)  # hourly, daily, weekly, monthly
    
    # Scope
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True)
    user_tier = Column(String(50), nullable=True, index=True)
    operation_type = Column(String(100), nullable=True, index=True)
    
    # Volume metrics
    total_requests = Column(Integer, nullable=False, default=0)
    successful_requests = Column(Integer, nullable=False, default=0)
    blocked_requests = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    avg_execution_time_ms = Column(Float, nullable=False, default=0)
    avg_cost_usd = Column(DECIMAL(10, 6), nullable=False, default=0)
    avg_coherence_score = Column(Float, nullable=False, default=0)
    
    # Risk metrics
    avg_fracture_score = Column(Float, nullable=False, default=0)
    avg_detrimental_score = Column(Float, nullable=False, default=0)
    avg_drift_score = Column(Float, nullable=False, default=0)
    
    # Governance metrics
    patterns_applied_total = Column(Integer, nullable=False, default=0)
    validators_passed_rate = Column(Float, nullable=False, default=0)
    memory_gate_success_rate = Column(Float, nullable=False, default=0)
    
    # Value metrics
    total_time_saved_minutes = Column(Float, nullable=False, default=0)
    total_cost_avoided_usd = Column(DECIMAL(10, 2), nullable=False, default=0)
    moat_strength_delta_total = Column(Float, nullable=False, default=0)
    
    # Relationships
    workspace = relationship("Workspace")
    
    # Unique constraint on period and scope
    __table_args__ = (
        {"schema": "public"},
    )
