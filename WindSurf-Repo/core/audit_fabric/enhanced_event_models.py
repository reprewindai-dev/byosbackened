"""
Enhanced Event Data Models with ISO/NIST Tagging
===============================================

Implementation of the enhanced event data models with ISO 42001 and NIST AI RMF
tagging as specified in the engineering brief.

This defines the canonical audit event schema that serves as the foundation for:
- Tamper-evident logging with compliance metadata
- Automated standards mapping and evidence generation
- Regulator-ready audit trails with ISO/NIST annotations
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
import structlog

from core.config import get_settings
from core.compliance.standards_mapping import standards_compliance


class EventType(Enum):
    """Canonical event types for Seked audit events."""
    CITIZENSHIP_GRANTED = "CITIZENSHIP_GRANTED"
    CITIZENSHIP_REVOKED = "CITIZENSHIP_REVOKED"
    TRUST_LEVEL_CHANGED = "TRUST_LEVEL_CHANGED"
    POLICY_DECISION = "POLICY_DECISION"
    AI_EXECUTION_ALLOWED = "AI_EXECUTION_ALLOWED"
    AI_EXECUTION_DENIED = "AI_EXECUTION_DENIED"
    AI_MESSAGE_SENT = "AI_MESSAGE_SENT"
    AI_MESSAGE_RECEIVED = "AI_MESSAGE_RECEIVED"
    CONFIGURATION_CHANGED = "CONFIGURATION_CHANGED"
    ADMIN_ACTION = "ADMIN_ACTION"
    AUDIT_EVENT_RECORDED = "AUDIT_EVENT_RECORDED"
    CONSENSUS_DECISION_REACHED = "CONSENSUS_DECISION_REACHED"
    COMPLIANCE_CHECK_PASSED = "COMPLIANCE_CHECK_PASSED"
    COMPLIANCE_CHECK_FAILED = "COMPLIANCE_CHECK_FAILED"


class EventSubtype(Enum):
    """Event subtypes for more granular classification."""
    # Policy decision subtypes
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    TRUST_EVALUATION = "TRUST_EVALUATION"

    # AI execution subtypes
    MODEL_INFERENCE = "MODEL_INFERENCE"
    DATA_PROCESSING = "DATA_PROCESSING"
    API_CALL = "API_CALL"

    # Message subtypes
    HANDSHAKE = "HANDSHAKE"
    PAYLOAD_TRANSFER = "PAYLOAD_TRANSFER"
    STATUS_UPDATE = "STATUS_UPDATE"

    # Admin subtypes
    POLICY_UPDATE = "POLICY_UPDATE"
    SYSTEM_MAINTENANCE = "SYSTEM_MAINTENANCE"
    EMERGENCY_OVERRIDE = "EMERGENCY_OVERRIDE"


class ActorType(Enum):
    """Types of actors that can perform actions."""
    AI = "AI"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"
    EXTERNAL = "EXTERNAL"


class ActorRole(Enum):
    """Roles that actors can have."""
    TENANT_ADMIN = "TENANT_ADMIN"
    OPERATOR = "OPERATOR"
    REGULATOR = "REGULATOR"
    SYSTEM = "SYSTEM"
    AI_CITIZEN = "AI_CITIZEN"
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE"


class ResourceType(Enum):
    """Types of resources that can be acted upon."""
    MODEL = "MODEL"
    ENDPOINT = "ENDPOINT"
    DATASET = "DATASET"
    PIPELINE = "PIPELINE"
    CONVERSATION = "CONVERSATION"
    MESSAGE = "MESSAGE"
    POLICY = "POLICY"
    CONFIGURATION = "CONFIGURATION"
    CITIZENSHIP = "CITIZENSHIP"


class RiskCategory(Enum):
    """AI risk categories for compliance."""
    SAFETY = "SAFETY"
    BIAS = "BIAS"
    SECURITY = "SECURITY"
    PRIVACY = "PRIVACY"
    REPUTATION = "REPUTATION"
    COMPLIANCE = "COMPLIANCE"
    PERFORMANCE = "PERFORMANCE"
    ETHICAL = "ETHICAL"


class TrustTier(Enum):
    """Trust tiers for AI systems."""
    EXPERIMENTAL = "EXPERIMENTAL"
    SUPERVISED = "SUPERVISED"
    AUTONOMOUS = "AUTONOMOUS"
    SOVEREIGN = "SOVEREIGN"


class RegulatoryReference(BaseModel):
    """Reference to regulatory framework requirements."""
    framework: str  # "ISO_42001", "NIST_AI_RMF", "EU_AI_ACT", etc.
    clause: str  # "8.4.3", "GV.1.1", etc.
    subcategory: Optional[str] = None  # For NIST: "M2", "GV.1", etc.
    description: str
    compliance_level: str = "mandatory"  # mandatory, recommended, optional


class InputMetadata(BaseModel):
    """Metadata about input data/process."""
    data_classification: str = "PUBLIC"  # PUBLIC, INTERNAL, CONFIDENTIAL, HIGHLY_CONFIDENTIAL
    contains_personal_data: bool = False
    contains_sensitive_data: bool = False
    data_volume_bytes: Optional[int] = None
    data_source: Optional[str] = None
    retention_policy: Optional[str] = None


class OutputMetadata(BaseModel):
    """Metadata about output/results."""
    content_risks: List[str] = []  # SELF_HARM, MALWARE, HARASSMENT, etc.
    blocked: bool = False
    reason: Optional[str] = None
    confidence_score: Optional[float] = None
    processing_duration_ms: Optional[int] = None
    output_classification: str = "PUBLIC"


class ExecutionContext(BaseModel):
    """Context information about execution environment."""
    trace_id: str
    request_id: str
    client_app_id: Optional[str] = None
    environment: str = "PROD"  # DEV, STAGING, PROD
    region: Optional[str] = None
    cluster: Optional[str] = None
    execution_node: Optional[str] = None


class ComplianceMetadata(BaseModel):
    """Compliance and regulatory metadata."""
    iso_42001_clauses: List[str] = []  # ["8.4.3", "9.1", etc.]
    nist_ai_rmf_categories: List[str] = []  # ["ME.1.1", "GV.2.1", etc.]
    regulatory_references: List[RegulatoryReference] = []
    compliance_evidence: Dict[str, Any] = {}  # Additional compliance data
    audit_trail_required: bool = True
    data_retention_days: int = 2555  # 7 years for compliance


class SekedAuditEvent(BaseModel):
    """Canonical Seked audit event with full compliance tagging."""

    # Core event identification
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_version: int = 1
    occurred_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    recorded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    # Tenant and system context
    tenant_id: str
    citizen_id: Optional[str] = None
    trust_tier: Optional[str] = None
    system_id: str = "seked-core"

    # Event classification
    event_type: str
    event_subtype: Optional[str] = None

    # Actor information
    actor_type: str
    actor_id: str
    actor_role: str

    # Resource information
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

    # Policy and decision context
    policy_id: Optional[str] = None
    policy_version: Optional[str] = None
    decision: Optional[str] = None  # ALLOW, DENY, FLAG, REQUIRE_REVIEW

    # Risk and compliance assessment
    risk_score: float = 0.0
    risk_category: List[str] = []
    jurisdiction: List[str] = ["global"]
    compliance_metadata: ComplianceMetadata = Field(default_factory=ComplianceMetadata)

    # Detailed metadata
    details: Dict[str, Any] = Field(default_factory=dict)

    # Tamper-evidence fields (set by audit system)
    prev_hash: Optional[str] = None
    entry_hash: Optional[str] = None
    log_stream_id: str = ""
    log_stream_type: str = "TENANT"
    log_sequence: Optional[int] = None

    @validator('event_type')
    def validate_event_type(cls, v):
        """Validate event type is from canonical list."""
        if hasattr(EventType, v):
            return v
        # Allow custom types but log warning
        return v.upper()

    @validator('trust_tier')
    def validate_trust_tier(cls, v):
        """Validate trust tier if provided."""
        if v and not hasattr(TrustTier, v):
            raise ValueError(f'Invalid trust tier: {v}')
        return v

    @validator('risk_score')
    def validate_risk_score(cls, v):
        """Validate risk score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Risk score must be between 0.0 and 1.0')
        return v

    def to_canonical_json(self) -> str:
        """Convert event to canonical JSON for hashing."""
        # Create deterministic representation excluding computed fields
        canonical_data = {
            "event_id": self.event_id,
            "event_version": self.event_version,
            "occurred_at": self.occurred_at,
            "tenant_id": self.tenant_id,
            "citizen_id": self.citizen_id,
            "trust_tier": self.trust_tier,
            "system_id": self.system_id,
            "event_type": self.event_type,
            "event_subtype": self.event_subtype,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "decision": self.decision,
            "risk_score": self.risk_score,
            "risk_category": sorted(self.risk_category),
            "jurisdiction": sorted(self.jurisdiction),
            "compliance_metadata": {
                "iso_42001_clauses": sorted(self.compliance_metadata.iso_42001_clauses),
                "nist_ai_rmf_categories": sorted(self.compliance_metadata.nist_ai_rmf_categories),
                "regulatory_references": [
                    ref.dict() for ref in sorted(
                        self.compliance_metadata.regulatory_references,
                        key=lambda x: (x.framework, x.clause)
                    )
                ],
                "compliance_evidence": self.compliance_metadata.compliance_evidence,
                "audit_trail_required": self.compliance_metadata.audit_trail_required,
                "data_retention_days": self.compliance_metadata.data_retention_days
            },
            "details": self.details
        }

        return json.dumps(canonical_data, sort_keys=True, separators=(',', ':'))

    def compute_entry_hash(self) -> str:
        """Compute tamper-evident entry hash."""
        import hashlib

        canonical_json = self.to_canonical_json()
        hash_obj = hashlib.sha256()
        hash_obj.update(canonical_json.encode('utf-8'))

        if self.prev_hash:
            hash_obj.update(self.prev_hash.encode('utf-8'))

        return hash_obj.hexdigest()

    def enrich_with_compliance_data(self) -> 'SekedAuditEvent':
        """
        Enrich event with automatic compliance tagging based on event type.

        This automatically populates ISO 42001 and NIST AI RMF references.
        """
        # Get compliance mapping for this event type
        compliance_mapping = standards_compliance.get_compliance_mapping(self.event_type)

        if compliance_mapping:
            # Add ISO 42001 clauses
            self.compliance_metadata.iso_42001_clauses = [
                clause.value for clause in compliance_mapping.iso_42001_clauses
            ]

            # Add NIST AI RMF categories
            self.compliance_metadata.nist_ai_rmf_categories = [
                cat.value for cat in compliance_mapping.nist_ai_rmf_categories
            ]

            # Add regulatory references
            regulatory_refs = []
            for clause in compliance_mapping.iso_42001_clauses:
                regulatory_refs.append(RegulatoryReference(
                    framework="ISO_42001",
                    clause=clause.value,
                    description=compliance_mapping.iso_42001_clauses[0].value  # Simplified
                ))

            for category in compliance_mapping.nist_ai_rmf_categories:
                regulatory_refs.append(RegulatoryReference(
                    framework="NIST_AI_RMF",
                    clause=category.value.split(":")[0],
                    subcategory=category.value.split(":")[0].split(".")[-1],
                    description=category.value
                ))

            self.compliance_metadata.regulatory_references = regulatory_refs

            # Add compliance evidence
            self.compliance_metadata.compliance_evidence = compliance_mapping.compliance_evidence

        return self

    def add_input_metadata(self, classification: str = "PUBLIC",
                          personal_data: bool = False,
                          sensitive_data: bool = False,
                          volume_bytes: Optional[int] = None,
                          source: Optional[str] = None) -> 'SekedAuditEvent':
        """Add input metadata to event."""
        self.details["input_metadata"] = {
            "data_classification": classification,
            "contains_personal_data": personal_data,
            "contains_sensitive_data": sensitive_data,
            "data_volume_bytes": volume_bytes,
            "data_source": source,
            "retention_policy": f"retain_{self.compliance_metadata.data_retention_days}_days"
        }
        return self

    def add_output_metadata(self, risks: List[str] = None,
                           blocked: bool = False,
                           reason: Optional[str] = None,
                           confidence: Optional[float] = None,
                           duration_ms: Optional[int] = None) -> 'SekedAuditEvent':
        """Add output metadata to event."""
        self.details["output_metadata"] = {
            "content_risks": risks or [],
            "blocked": blocked,
            "reason": reason,
            "confidence_score": confidence,
            "processing_duration_ms": duration_ms,
            "output_classification": "HIGHLY_CONFIDENTIAL" if risks else "PUBLIC"
        }
        return self

    def add_execution_context(self, trace_id: str, request_id: str,
                             client_app_id: Optional[str] = None,
                             environment: str = "PROD",
                             region: Optional[str] = None,
                             cluster: Optional[str] = None) -> 'SekedAuditEvent':
        """Add execution context to event."""
        self.details["execution_context"] = {
            "trace_id": trace_id,
            "request_id": request_id,
            "client_app_id": client_app_id,
            "environment": environment,
            "region": region,
            "cluster": cluster,
            "execution_node": os.getenv("NODE_NAME", "unknown")
        }
        return self


class EventFactory:
    """Factory for creating properly structured Seked audit events."""

    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    def create_citizenship_event(self, tenant_id: str, citizen_id: str,
                                action: str, trust_tier: str = "EXPERIMENTAL",
                                actor_id: str = "seked-system",
                                **kwargs) -> SekedAuditEvent:
        """Create a citizenship-related event."""
        event = SekedAuditEvent(
            tenant_id=tenant_id,
            citizen_id=citizen_id,
            trust_tier=trust_tier,
            event_type=f"CITIZENSHIP_{action.upper()}",
            actor_type="SYSTEM",
            actor_id=actor_id,
            actor_role="SYSTEM",
            resource_type="CITIZENSHIP",
            resource_id=citizen_id,
            decision="ALLOW" if action.lower() == "granted" else "DENY",
            risk_score=0.1 if trust_tier == "EXPERIMENTAL" else 0.3,
            **kwargs
        )

        return event.enrich_with_compliance_data()

    def create_policy_decision_event(self, tenant_id: str, policy_id: str,
                                    decision: str, risk_score: float,
                                    actor_id: str, resource_type: str = None,
                                    resource_id: str = None, **kwargs) -> SekedAuditEvent:
        """Create a policy decision event."""
        event = SekedAuditEvent(
            tenant_id=tenant_id,
            event_type="POLICY_DECISION",
            event_subtype="COMPLIANCE_CHECK",
            actor_type="SYSTEM",
            actor_id=actor_id,
            actor_role="SYSTEM",
            policy_id=policy_id,
            decision=decision,
            risk_score=risk_score,
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs
        )

        # Add risk categories based on score
        if risk_score > 0.7:
            event.risk_category = ["SAFETY", "COMPLIANCE"]
        elif risk_score > 0.4:
            event.risk_category = ["BIAS", "PRIVACY"]

        return event.enrich_with_compliance_data()

    def create_ai_execution_event(self, tenant_id: str, citizen_id: str,
                                 decision: str, risk_score: float,
                                 model_id: str, **kwargs) -> SekedAuditEvent:
        """Create an AI execution event."""
        event = SekedAuditEvent(
            tenant_id=tenant_id,
            citizen_id=citizen_id,
            event_type=f"AI_EXECUTION_{decision.upper()}",
            event_subtype="MODEL_INFERENCE",
            actor_type="AI",
            actor_id=citizen_id,
            actor_role="AI_CITIZEN",
            resource_type="MODEL",
            resource_id=model_id,
            decision=decision,
            risk_score=risk_score,
            **kwargs
        )

        return event.enrich_with_compliance_data()

    def create_ai_message_event(self, tenant_id: str, sender_id: str,
                               receiver_id: str, message_type: str,
                               **kwargs) -> SekedAuditEvent:
        """Create an AI-to-AI message event."""
        event = SekedAuditEvent(
            tenant_id=tenant_id,
            citizen_id=sender_id,
            event_type="AI_MESSAGE_SENT" if sender_id else "AI_MESSAGE_RECEIVED",
            event_subtype=message_type.upper(),
            actor_type="AI",
            actor_id=sender_id,
            actor_role="AI_CITIZEN",
            resource_type="MESSAGE",
            decision="ALLOW",  # Messages are sent/received after authorization
            risk_score=0.2,  # Base risk for inter-AI communication
            **kwargs
        )

        return event.enrich_with_compliance_data()

    def create_admin_action_event(self, tenant_id: str, admin_id: str,
                                 action: str, target_resource: str = None,
                                 **kwargs) -> SekedAuditEvent:
        """Create an administrative action event."""
        event = SekedAuditEvent(
            tenant_id=tenant_id,
            event_type="ADMIN_ACTION",
            event_subtype=action.upper(),
            actor_type="HUMAN",
            actor_id=admin_id,
            actor_role="TENANT_ADMIN",
            resource_type=target_resource,
            decision="ALLOW",  # Admin actions are authorized
            risk_score=0.1,  # Low risk for admin actions
            **kwargs
        )

        return event.enrich_with_compliance_data()


# Global event factory instance
event_factory = EventFactory()


# Utility functions for event creation
def create_citizenship_granted_event(tenant_id: str, citizen_id: str,
                                   trust_tier: str = "EXPERIMENTAL") -> SekedAuditEvent:
    """Create a citizenship granted event."""
    return event_factory.create_citizenship_event(
        tenant_id, citizen_id, "granted", trust_tier
    )


def create_policy_allow_event(tenant_id: str, policy_id: str, risk_score: float,
                             actor_id: str) -> SekedAuditEvent:
    """Create a policy allow decision event."""
    return event_factory.create_policy_decision_event(
        tenant_id, policy_id, "ALLOW", risk_score, actor_id
    )


def create_ai_execution_denied_event(tenant_id: str, citizen_id: str,
                                   model_id: str, risk_score: float) -> SekedAuditEvent:
    """Create an AI execution denied event."""
    return event_factory.create_ai_execution_event(
        tenant_id, citizen_id, "DENIED", risk_score, model_id
    )


def create_inter_ai_message_event(tenant_id: str, sender_id: str,
                                receiver_id: str, message_type: str) -> SekedAuditEvent:
    """Create an inter-AI message event."""
    return event_factory.create_ai_message_event(
        tenant_id, sender_id, receiver_id, message_type
    )
