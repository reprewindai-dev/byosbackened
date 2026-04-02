"""
Standards Compliance Mapping
============================

This module implements the formal mapping of Seked controls to ISO 42001 and NIST AI RMF standards.
Every event and decision is tagged with the specific clauses and functions it supports.

This transforms Seked from "governance narrative" to "turnkey evidence engine for
ISO 42001 + NIST AI RMF compliance" that regulators and insurers can immediately recognize.

Standards Mapping:
- ISO/IEC 42001: AI management system (governance, documentation, accountability)
- NIST AI RMF: Govern/Map/Measure/Manage framework for responsible AI
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
import structlog

from core.config import get_settings


class ISO42001Clause(Enum):
    """ISO 42001 AI Management System clauses."""
    # Context of the organization
    CLAUSE_4_1 = "4.1 Understanding the organization and its context"
    CLAUSE_4_2 = "4.2 Understanding the needs and expectations of interested parties"
    CLAUSE_4_3 = "4.3 Determining the scope of the AI management system"
    CLAUSE_4_4 = "4.4 AI management system"

    # Leadership
    CLAUSE_5_1 = "5.1 Leadership and commitment"
    CLAUSE_5_2 = "5.2 Policy"
    CLAUSE_5_3 = "5.3 Organizational roles, responsibilities and authorities"

    # Planning
    CLAUSE_6_1 = "6.1 Actions to address risks and opportunities"
    CLAUSE_6_2 = "6.2 AI objectives and planning to achieve them"

    # Support
    CLAUSE_7_1 = "7.1 Resources"
    CLAUSE_7_2 = "7.2 Competence"
    CLAUSE_7_3 = "7.3 Awareness"
    CLAUSE_7_4 = "7.4 Communication"
    CLAUSE_7_5 = "7.5 Documented information"

    # Operation
    CLAUSE_8_1 = "8.1 Operational planning and control"
    CLAUSE_8_2 = "8.2 AI system lifecycle"
    CLAUSE_8_3 = "8.3 Procurement"
    CLAUSE_8_4 = "8.4 Data management"
    CLAUSE_8_5 = "8.5 Transparency and accountability"
    CLAUSE_8_6 = "8.6 Human-AI interaction"
    CLAUSE_8_7 = "8.7 Performance monitoring and measurement"

    # Performance evaluation
    CLAUSE_9_1 = "9.1 Monitoring, measurement, analysis and evaluation"
    CLAUSE_9_2 = "9.2 Internal audit"
    CLAUSE_9_3 = "9.3 Management review"

    # Improvement
    CLAUSE_10_1 = "10.1 Continual improvement"
    CLAUSE_10_2 = "10.2 Nonconformity and corrective action"


class NISTAIRMFFunction(Enum):
    """NIST AI RMF Core Functions."""
    GOVERN = "Govern: Govern the AI system and its deployment context"
    MAP = "Map: Map the AI system and its context"
    MEASURE = "Measure: Measure the AI system and its context"
    MANAGE = "Manage: Manage the AI system and its context"


class NISTAIRMFSubcategory(Enum):
    """NIST AI RMF Subcategories."""
    # Govern
    GV_1_1 = "GV.1.1: Establish an AI governance structure"
    GV_1_2 = "GV.1.2: Assign AI governance roles and responsibilities"
    GV_1_3 = "GV.1.3: Establish AI policies and procedures"
    GV_2_1 = "GV.2.1: Identify applicable AI laws and regulations"
    GV_2_2 = "GV.2.2: Identify applicable AI ethical principles"
    GV_2_3 = "GV.2.3: Identify applicable AI standards and guidelines"
    GV_3_1 = "GV.3.1: Establish AI risk management processes"
    GV_3_2 = "GV.3.2: Establish AI supply chain risk management"
    GV_3_3 = "GV.3.3: Establish AI incident response processes"

    # Map
    MP_1_1 = "MP.1.1: Identify AI system components and capabilities"
    MP_1_2 = "MP.1.2: Identify AI system data and data processing"
    MP_1_3 = "MP.1.3: Identify AI system users and user interactions"
    MP_2_1 = "MP.2.1: Identify AI system context and environment"
    MP_2_2 = "MP.2.2: Identify AI system dependencies and integrations"
    MP_2_3 = "MP.2.3: Identify AI system limitations and failure modes"
    MP_3_1 = "MP.3.1: Map AI system risks and impacts"
    MP_3_2 = "MP.3.2: Map AI system assurance and trustworthiness"
    MP_3_3 = "MP.3.3: Map AI system monitoring and measurement"

    # Measure
    ME_1_1 = "ME.1.1: Establish AI performance measures"
    ME_1_2 = "ME.1.2: Establish AI risk measures"
    ME_1_3 = "ME.1.3: Establish AI impact measures"
    ME_2_1 = "ME.2.1: Implement AI performance monitoring"
    ME_2_2 = "ME.2.2: Implement AI risk monitoring"
    ME_2_3 = "ME.2.3: Implement AI impact monitoring"
    ME_3_1 = "ME.3.1: Analyze AI performance data"
    ME_3_2 = "ME.3.2: Analyze AI risk data"
    ME_3_3 = "ME.3.3: Analyze AI impact data"

    # Manage
    MG_1_1 = "MG.1.1: Respond to AI performance issues"
    MG_1_2 = "MG.1.2: Respond to AI risk issues"
    MG_1_3 = "MG.1.3: Respond to AI impact issues"
    MG_2_1 = "MG.2.1: Update AI system components"
    MG_2_2 = "MG.2.2: Update AI system data and processing"
    MG_2_3 = "MG.2.3: Update AI system policies and procedures"
    MG_3_1 = "MG.3.1: Communicate AI system changes"
    MG_3_2 = "MG.3.2: Document AI system changes"
    MG_3_3 = "MG.3.3: Review AI system changes"


class ComplianceMapping(BaseModel):
    """Compliance mapping for an event or control."""
    event_type: str
    iso_42001_clauses: List[ISO42001Clause] = []
    nist_ai_rmf_categories: List[NISTAIRMFSubcategory] = []
    compliance_evidence: Dict[str, str] = {}  # Additional compliance metadata
    regulatory_mappings: Dict[str, List[str]] = {}  # EU AI Act, etc.


class StandardsComplianceEngine:
    """Engine for mapping Seked controls to standards compliance."""

    def __init__(self):
        self.settings = get_settings()
        self.compliance_path = os.path.join(self.settings.DATA_DIR, "compliance")
        self.mappings_db_path = os.path.join(self.compliance_path, "mappings.db")
        self.logger = structlog.get_logger(__name__)

        # Pre-defined compliance mappings for Seked events
        self.event_compliance_mappings = self._init_compliance_mappings()

        self._init_compliance_storage()

    def _init_compliance_storage(self) -> None:
        """Initialize compliance mappings storage."""
        import os
        os.makedirs(self.compliance_path, exist_ok=True)

        if not os.path.exists(self.mappings_db_path):
            self._init_mappings_db()

        self.logger.info("Standards compliance storage initialized")

    def _init_mappings_db(self) -> None:
        """Initialize compliance mappings database."""
        import sqlite3

        conn = sqlite3.connect(self.mappings_db_path)
        conn.execute("""
            CREATE TABLE compliance_mappings (
                event_type TEXT PRIMARY KEY,
                iso_42001_clauses TEXT NOT NULL,  -- JSON array
                nist_ai_rmf_categories TEXT NOT NULL,  -- JSON array
                compliance_evidence TEXT NOT NULL,  -- JSON object
                regulatory_mappings TEXT NOT NULL,  -- JSON object
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def _init_compliance_mappings(self) -> Dict[str, ComplianceMapping]:
        """Initialize pre-defined compliance mappings for Seked events."""
        return {
            # Citizenship events
            "ai_citizenship_created": ComplianceMapping(
                event_type="ai_citizenship_created",
                iso_42001_clauses=[
                    ISO42001Clause.CLAUSE_8_5,  # Transparency and accountability
                    ISO42001Clause.CLAUSE_8_6,  # Human-AI interaction
                    ISO42001Clause.CLAUSE_5_3,  # Organizational roles
                ],
                nist_ai_rmf_categories=[
                    NISTAIRMFSubcategory.GV_1_1,  # Establish governance structure
                    NISTAIRMFSubcategory.GV_1_2,  # Assign roles and responsibilities
                    NISTAIRMFSubcategory.MP_1_1,  # Identify system components
                ],
                compliance_evidence={
                    "accountability": "Cryptographically signed citizenship certificate",
                    "transparency": "Public key infrastructure with certificate chain",
                    "governance": "Consensus-backed citizenship issuance"
                },
                regulatory_mappings={
                    "eu_ai_act": ["Article 5: Classification rules", "Article 28: Fundamental rights"],
                    "nist_ai_rmf": ["Govern function", "Map function"]
                }
            ),

            # Policy evaluation events
            "policy_evaluation_completed": ComplianceMapping(
                event_type="policy_evaluation_completed",
                iso_42001_clauses=[
                    ISO42001Clause.CLAUSE_8_1,  # Operational planning and control
                    ISO42001Clause.CLAUSE_9_1,  # Monitoring, measurement, analysis
                    ISO42001Clause.CLAUSE_6_1,  # Risk management
                ],
                nist_ai_rmf_categories=[
                    NISTAIRMFSubcategory.GV_3_1,  # Risk management processes
                    NISTAIRMFSubcategory.ME_2_1,  # Performance monitoring
                    NISTAIRMFSubcategory.ME_2_2,  # Risk monitoring
                ],
                compliance_evidence={
                    "risk_assessment": "Automated policy evaluation with risk scoring",
                    "monitoring": "Real-time policy enforcement monitoring",
                    "accountability": "Audit trail of all policy decisions"
                },
                regulatory_mappings={
                    "eu_ai_act": ["Article 9: Risk management system"],
                    "nist_ai_rmf": ["Measure function", "Manage function"]
                }
            ),

            # Execution events
            "ai_execution_allowed": ComplianceMapping(
                event_type="ai_execution_allowed",
                iso_42001_clauses=[
                    ISO42001Clause.CLAUSE_8_1,  # Operational planning and control
                    ISO42001Clause.CLAUSE_8_7,  # Performance monitoring
                    ISO42001Clause.CLAUSE_9_1,  # Monitoring and measurement
                ],
                nist_ai_rmf_categories=[
                    NISTAIRMFSubcategory.ME_1_1,  # Performance measures
                    NISTAIRMFSubcategory.ME_2_1,  # Performance monitoring
                    NISTAIRMFSubcategory.MG_1_1,  # Respond to performance issues
                ],
                compliance_evidence={
                    "monitoring": "Execution telemetry with performance metrics",
                    "control": "Automated approval workflows",
                    "traceability": "Complete execution audit trail"
                },
                regulatory_mappings={
                    "eu_ai_act": ["Article 15: Data governance", "Article 20: Transparency"],
                    "nist_ai_rmf": ["Measure function", "Manage function"]
                }
            ),

            # CitizenNet communication events
            "citizennet_message_sent": ComplianceMapping(
                event_type="citizennet_message_sent",
                iso_42001_clauses=[
                    ISO42001Clause.CLAUSE_8_6,  # Human-AI interaction
                    ISO42001Clause.CLAUSE_8_4,  # Data management
                    ISO42001Clause.CLAUSE_7_4,  # Communication
                ],
                nist_ai_rmf_categories=[
                    NISTAIRMFSubcategory.MP_2_2,  # System dependencies and integrations
                    NISTAIRMFSubcategory.ME_3_1,  # Performance data analysis
                    NISTAIRMFSubcategory.MG_3_1,  # Communicate system changes
                ],
                compliance_evidence={
                    "data_protection": "Encrypted AI-to-AI communication",
                    "accountability": "Signed messages with citizen identity",
                    "monitoring": "Communication audit trails"
                },
                regulatory_mappings={
                    "eu_ai_act": ["Article 10: Transparency obligations"],
                    "gdpr": ["Article 5: Data protection principles"]
                }
            ),

            # Consensus decision events
            "consensus_decision_reached": ComplianceMapping(
                event_type="consensus_decision_reached",
                iso_42001_clauses=[
                    ISO42001Clause.CLAUSE_5_1,  # Leadership and commitment
                    ISO42001Clause.CLAUSE_9_2,  # Internal audit
                    ISO42001Clause.CLAUSE_9_3,  # Management review
                ],
                nist_ai_rmf_categories=[
                    NISTAIRMFSubcategory.GV_1_1,  # Governance structure
                    NISTAIRMFSubcategory.GV_1_3,  # Policies and procedures
                    NISTAIRMFSubcategory.ME_3_3,  # Impact data analysis
                ],
                compliance_evidence={
                    "governance": "Multi-node consensus validation",
                    "audit": "Distributed audit trails",
                    "accountability": "Consensus-backed decision authority"
                },
                regulatory_mappings={
                    "eu_ai_act": ["Article 25: Governance obligations"],
                    "nist_ai_rmf": ["Govern function"]
                }
            ),

            # Audit fabric events
            "audit_event_recorded": ComplianceMapping(
                event_type="audit_event_recorded",
                iso_42001_clauses=[
                    ISO42001Clause.CLAUSE_9_1,  # Monitoring, measurement, analysis
                    ISO42001Clause.CLAUSE_9_2,  # Internal audit
                    ISO42001Clause.CLAUSE_7_5,  # Documented information
                ],
                nist_ai_rmf_categories=[
                    NISTAIRMFSubcategory.ME_2_1,  # Performance monitoring
                    NISTAIRMFSubcategory.ME_2_2,  # Risk monitoring
                    NISTAIRMFSubcategory.ME_2_3,  # Impact monitoring
                ],
                compliance_evidence={
                    "immutability": "Cryptographic hash chaining",
                    "integrity": "Hybrid on-chain/off-chain verification",
                    "auditability": "Independent verification capabilities"
                },
                regulatory_mappings={
                    "eu_ai_act": ["Article 12: Logging capabilities"],
                    "gdpr": ["Article 30: Records of processing activities"]
                }
            ),
        }

    def get_compliance_mapping(self, event_type: str) -> Optional[ComplianceMapping]:
        """Get compliance mapping for an event type."""
        return self.event_compliance_mappings.get(event_type)

    def map_event_to_standards(self, event_type: str, jurisdiction: str = "global") -> Dict[str, any]:
        """
        Map an event to its compliance standards and evidence.

        Returns regulator-ready compliance information.
        """
        mapping = self.get_compliance_mapping(event_type)
        if not mapping:
            return {}

        # Build compliance report
        compliance_report = {
            "event_type": event_type,
            "jurisdiction": jurisdiction,
            "iso_42001_compliance": {
                "standard": "ISO/IEC 42001:2023 - AI Management System",
                "supported_clauses": [clause.value for clause in mapping.iso_42001_clauses],
                "evidence": mapping.compliance_evidence
            },
            "nist_ai_rmf_compliance": {
                "framework": "NIST AI Risk Management Framework",
                "supported_categories": [cat.value for cat in mapping.nist_ai_rmf_categories],
                "core_functions": list(set(cat.value.split(":")[0].split(".")[0] for cat in mapping.nist_ai_rmf_categories)),
                "evidence": mapping.compliance_evidence
            },
            "regulatory_alignment": mapping.regulatory_mappings,
            "compliance_readiness": self._assess_compliance_readiness(mapping, jurisdiction)
        }

        return compliance_report

    def _assess_compliance_readiness(self, mapping: ComplianceMapping, jurisdiction: str) -> Dict[str, any]:
        """Assess how ready this control is for regulatory compliance."""
        readiness_score = 0
        total_possible = 0

        # ISO 42001 assessment
        iso_score = len(mapping.iso_42001_clauses) * 10  # 10 points per clause
        total_possible += 100  # Max 10 clauses

        # NIST AI RMF assessment
        nist_score = len(mapping.nist_ai_rmf_categories) * 5  # 5 points per subcategory
        total_possible += 50  # Max 10 subcategories

        # Evidence quality assessment
        evidence_score = len(mapping.compliance_evidence) * 10
        total_possible += 30

        # Regulatory mapping assessment
        regulatory_score = len(mapping.regulatory_mappings) * 15
        total_possible += 30

        readiness_score = iso_score + nist_score + evidence_score + regulatory_score

        readiness_percentage = min(100, (readiness_score / total_possible) * 100)

        return {
            "overall_readiness": f"{readiness_percentage:.1f}%",
            "iso_42001_coverage": f"{len(mapping.iso_42001_clauses)}/{len(ISO42001Clause)} clauses",
            "nist_ai_rmf_coverage": f"{len(mapping.nist_ai_rmf_categories)}/{len(NISTAIRMFSubcategory)} subcategories",
            "evidence_strength": "strong" if len(mapping.compliance_evidence) >= 3 else "adequate",
            "regulatory_alignment": f"{len(mapping.regulatory_mappings)} frameworks mapped",
            "jurisdiction_specific": jurisdiction in ["eu", "us", "global"]
        }

    def generate_compliance_report(self, event_types: List[str] = None,
                                  jurisdiction: str = "global") -> Dict[str, any]:
        """
        Generate a comprehensive compliance report for Seked.

        This creates regulator-ready documentation showing how Seked implements
        ISO 42001 and NIST AI RMF requirements.
        """
        if event_types is None:
            event_types = list(self.event_compliance_mappings.keys())

        event_compliance = {}
        for event_type in event_types:
            event_compliance[event_type] = self.map_event_to_standards(event_type, jurisdiction)

        # Calculate system-wide compliance metrics
        total_events = len(event_compliance)
        iso_clauses_covered = set()
        nist_categories_covered = set()
        regulatory_frameworks = set()

        for event_data in event_compliance.values():
            if event_data:
                iso_clauses_covered.update(event_data["iso_42001_compliance"]["supported_clauses"])
                nist_categories_covered.update(event_data["nist_ai_rmf_compliance"]["supported_categories"])
                regulatory_frameworks.update(event_data["regulatory_alignment"].keys())

        system_compliance = {
            "system_overview": {
                "name": "Seked AI Governance Infrastructure",
                "version": "1.0.0",
                "architecture": "Distributed consensus with immutable audit fabric",
                "standards_supported": ["ISO/IEC 42001:2023", "NIST AI RMF"]
            },
            "compliance_coverage": {
                "iso_42001": {
                    "total_clauses": len(ISO42001Clause),
                    "covered_clauses": len(iso_clauses_covered),
                    "coverage_percentage": f"{(len(iso_clauses_covered) / len(ISO42001Clause)) * 100:.1f}%",
                    "covered_clause_list": sorted(list(iso_clauses_covered))
                },
                "nist_ai_rmf": {
                    "total_subcategories": len(NISTAIRMFSubcategory),
                    "covered_subcategories": len(nist_categories_covered),
                    "coverage_percentage": f"{(len(nist_categories_covered) / len(NISTAIRMFSubcategory)) * 100:.1f}%",
                    "core_functions_covered": list(set(cat.split(":")[0].split(".")[0] for cat in nist_categories_covered))
                }
            },
            "regulatory_alignment": {
                "frameworks_supported": sorted(list(regulatory_frameworks)),
                "jurisdiction": jurisdiction,
                "certification_readiness": "Ready for ISO 42001 certification audit"
            },
            "event_level_compliance": event_compliance,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "report_type": "Seked Standards Compliance Assessment"
        }

        self.logger.info("Compliance report generated",
                        events_analyzed=total_events,
                        iso_coverage=len(iso_clauses_covered),
                        nist_coverage=len(nist_categories_covered))

        return system_compliance

    def validate_against_standard(self, event_type: str, standard: str,
                                requirement: str) -> Dict[str, any]:
        """
        Validate that an event type meets a specific standard requirement.

        Args:
            event_type: The type of event to validate
            standard: The standard (e.g., "iso_42001", "nist_ai_rmf")
            requirement: The specific requirement to check

        Returns:
            Validation result with evidence
        """
        mapping = self.get_compliance_mapping(event_type)
        if not mapping:
            return {"valid": False, "reason": "Event type not mapped to standards"}

        if standard == "iso_42001":
            requirement_matches = [clause for clause in mapping.iso_42001_clauses
                                 if requirement in clause.value]
            return {
                "valid": len(requirement_matches) > 0,
                "requirement": requirement,
                "matched_clauses": [clause.value for clause in requirement_matches],
                "evidence": mapping.compliance_evidence
            }

        elif standard == "nist_ai_rmf":
            requirement_matches = [cat for cat in mapping.nist_ai_rmf_categories
                                 if requirement in cat.value]
            return {
                "valid": len(requirement_matches) > 0,
                "requirement": requirement,
                "matched_categories": [cat.value for cat in requirement_matches],
                "evidence": mapping.compliance_evidence
            }

        return {"valid": False, "reason": f"Unknown standard: {standard}"}


# Global standards compliance engine instance
standards_compliance = StandardsComplianceEngine()
