"""Canonical VeklomRun model for UACP V5 run truth."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text

from db.session import Base


class VeklomRun(Base):
    """Atomic UACP run record.

    This table is the durable V5 bridge between legacy request logs and the
    deterministic run object used by UACP routing, evidence, replay, and billing.
    """

    __tablename__ = "veklom_runs"

    run_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    actor_id = Column(String, nullable=True, index=True)
    parent_run_id = Column(String, nullable=True, index=True)
    delegation_depth = Column(Integer, nullable=False, default=0)

    raw_intent = Column(Text, nullable=False)
    compiled_plan_json = Column(Text, nullable=True)
    task_graph_json = Column(Text, nullable=True)

    human_attestation_json = Column(Text, nullable=True)
    ai_attestation_json = Column(Text, nullable=True)
    execution_attestation_json = Column(Text, nullable=True)

    policy_version = Column(String, nullable=False, default="uacp-v5")
    constitution_hash = Column(String, nullable=False, default="unsealed")
    governance_decision = Column(String, nullable=False, default="ALLOW", index=True)
    risk_tier = Column(String, nullable=False, default="LOW", index=True)
    hitl_required = Column(Integer, nullable=False, default=0)

    genome_hash = Column(String, nullable=False, index=True)
    input_hash = Column(String, nullable=False, index=True)
    output_hash = Column(String, nullable=True, index=True)
    decision_frame_hash = Column(String, nullable=True, index=True)
    provenance_json = Column(Text, nullable=True)

    provider = Column(String, nullable=True, index=True)
    model = Column(String, nullable=True, index=True)
    route_json = Column(Text, nullable=True)

    reserve_before_cents = Column(Integer, nullable=False, default=0)
    approved_budget_cents = Column(Integer, nullable=False, default=0)
    debit_cents = Column(Numeric(10, 6), nullable=False, default=0)
    reserve_after_cents = Column(Integer, nullable=False, default=0)
    over_budget = Column(Integer, nullable=False, default=0)

    evidence_json = Column(Text, nullable=True)
    feedback_json = Column(Text, nullable=True)

    source_table = Column(String, nullable=False, index=True)
    source_id = Column(String, nullable=False, index=True)
    request_log_id = Column(String, nullable=True, index=True)

    status = Column(String, nullable=False, default="SEALED", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sealed_at = Column(DateTime, nullable=True, index=True)
