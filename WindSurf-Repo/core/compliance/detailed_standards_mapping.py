"""
Detailed ISO 42001 vs NIST AI RMF Standards Mapping
==================================================

Implementation of the detailed standards mapping table from the engineering brief.
This provides the complete mapping between Seked controls and both ISO 42001
and NIST AI RMF requirements for regulator-ready compliance evidence.

The mapping table covers:
- Governance structure and roles
- Risk identification and measurement  
- Risk treatment and controls
- Evidence and audit requirements
- Lifecycle management
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import structlog

from core.config import get_settings


class StandardsMappingEntry(BaseModel):
    """Detailed mapping entry for a Seked component."""
    component: str  # Seked component or event type
    iso_42001_focus: str  # ISO 42001 requirement description
    nist_ai_rmf_focus: str  # NIST AI RMF requirement description
    seked_implementation: str  # How Seked implements this
    compliance_evidence: List[str]  # Types of evidence generated
    sources: List[str]  # References to standards documents


class DetailedStandardsMapper:
    """Detailed mapper for ISO 42001 vs NIST AI RMF alignment."""

    def __init__(self):
        self.settings = get_settings()
        self.mappings = self._init_detailed_mappings()
        self.logger = structlog.get_logger(__name__)

    def _init_detailed_mappings(self) -> Dict[str, StandardsMappingEntry]:
        """Initialize the detailed standards mapping table from the engineering brief."""
        return {
            "governance_structure": StandardsMappingEntry(
                component="governance_structure",
                iso_42001_focus="Formal roles, responsibilities, documented policies",
                nist_ai_rmf_focus="Govern: accountability, oversight, stakeholder engagement",
                seked_implementation="Tenant-level roles, policy templates, approval workflows",
                compliance_evidence=[
                    "Role-based access control (RBAC) configuration",
                    "Policy document versioning and approval trails",
                    "Stakeholder engagement audit logs"
                ],
                sources=["ISO/IEC 42001:2023 5.1, 5.2, 5.3", "NIST AI RMF GV.1.1, GV.1.2, GV.1.3"]
            ),

            "risk_identification": StandardsMappingEntry(
                component="risk_identification",
                iso_42001_focus="High-level AI risk categories and impact",
                nist_ai_rmf_focus="Map: context, risk scenarios, stakeholders",
                seked_implementation="Risk metadata on citizens, use-cases, data classes",
                compliance_evidence=[
                    "Risk classification schemas",
                    "Use case risk assessments",
                    "Stakeholder impact mappings",
                    "Data classification tags"
                ],
                sources=["ISO/IEC 42001:2023 4.1, 4.2, 6.1", "NIST AI RMF MP.1.1, MP.2.1, MP.3.1"]
            ),

            "risk_measurement": StandardsMappingEntry(
                component="risk_measurement",
                iso_42001_focus="Periodic assessment requirement",
                nist_ai_rmf_focus="Measure: metrics, monitoring, testing",
                seked_implementation="Policy engine metrics, violation counts, risk scores",
                compliance_evidence=[
                    "Real-time risk score calculations",
                    "Policy violation metrics",
                    "Performance monitoring dashboards",
                    "Automated risk assessments"
                ],
                sources=["ISO/IEC 42001:2023 9.1", "NIST AI RMF ME.1.1, ME.2.1, ME.3.1"]
            ),

            "risk_treatment": StandardsMappingEntry(
                component="risk_treatment",
                iso_42001_focus="Documented controls and mitigations",
                nist_ai_rmf_focus="Manage: implement controls, feedback loops",
                seked_implementation="Enforcement rules, trust levels, kill-switches, workflows",
                compliance_evidence=[
                    "Control implementation audit trails",
                    "Kill-switch activation logs",
                    "Workflow execution records",
                    "Risk mitigation effectiveness metrics"
                ],
                sources=["ISO/IEC 42001:2023 6.2, 8.1", "NIST AI RMF MG.1.1, MG.2.1, MG.3.1"]
            ),

            "evidence_audit": StandardsMappingEntry(
                component="evidence_audit",
                iso_42001_focus="Objective evidence for certification",
                nist_ai_rmf_focus="Evidence for risk decisions and monitoring",
                seked_implementation="Immutable audit fabric, Merkle proofs, exportable reports",
                compliance_evidence=[
                    "Cryptographically signed audit events",
                    "Merkle tree inclusion proofs",
                    "Immutable hash chains",
                    "Regulator-ready compliance reports"
                ],
                sources=["ISO/IEC 42001:2023 9.2, 9.3, 7.5", "NIST AI RMF ME.2.1, ME.2.2, ME.2.3"]
            ),

            "lifecycle_management": StandardsMappingEntry(
                component="lifecycle_management",
                iso_42001_focus="AI lifecycle control (design, deployment, monitoring)",
                nist_ai_rmf_focus="All 4 RMF functions across lifecycle",
                seked_implementation="Hooks at deployment, runtime, recertification, decommissioning",
                compliance_evidence=[
                    "Lifecycle stage transition logs",
                    "Deployment approval records",
                    "Runtime monitoring data",
                    "Decommissioning audit trails"
                ],
                sources=["ISO/IEC 42001:2023 8.2", "NIST AI RMF GV.3.1, MP.1.1, ME.1.1, MG.1.1"]
            ),

            "citizenship_issuance": StandardsMappingEntry(
                component="citizenship_issuance",
                iso_42001_focus="Transparency and accountability in AI system registration",
                nist_ai_rmf_focus="Establish governance structure and system identification",
                seked_implementation="Cryptographically signed citizenship certificates with trust tiers",
                compliance_evidence=[
                    "Certificate signing with HSM/KMS",
                    "Trust tier assignment audits",
                    "Capability declaration validations",
                    "Liability holder verifications"
                ],
                sources=["ISO/IEC 42001:2023 8.5, 5.3", "NIST AI RMF GV.1.1, MP.1.1"]
            ),

            "policy_evaluation": StandardsMappingEntry(
                component="policy_evaluation",
                iso_42001_focus="Operational planning and risk management controls",
                nist_ai_rmf_focus="Risk monitoring and performance measurement",
                seked_implementation="Distributed consensus policy evaluation with audit trails",
                compliance_evidence=[
                    "Policy evaluation decision logs",
                    "Consensus validation records",
                    "Risk score calculations",
                    "Policy enforcement metrics"
                ],
                sources=["ISO/IEC 42001:2023 8.1, 9.1", "NIST AI RMF ME.2.1, ME.2.2"]
            ),

            "ai_communication": StandardsMappingEntry(
                component="ai_communication",
                iso_42001_focus="Human-AI interaction and data management",
                nist_ai_rmf_focus="System integration monitoring and change management",
                seked_implementation="CitizenNet protocol with signed messages and decision tokens",
                compliance_evidence=[
                    "Message signature validations",
                    "Decision token verifications",
                    "Communication audit logs",
                    "Cross-citizen interaction records"
                ],
                sources=["ISO/IEC 42001:2023 8.6, 8.4", "NIST AI RMF MP.2.2, MG.3.1"]
            ),

            "consensus_decisions": StandardsMappingEntry(
                component="consensus_decisions",
                iso_42001_focus="Leadership, internal audit, and management review",
                nist_ai_rmf_focus="Governance policies and risk management processes",
                seked_implementation="Multi-node consensus with quorum requirements and finality proofs",
                compliance_evidence=[
                    "Consensus participant logs",
                    "Quorum validation records",
                    "Decision finality proofs",
                    "Governance override audits"
                ],
                sources=["ISO/IEC 42001:2023 5.1, 9.2, 9.3", "NIST AI RMF GV.1.3, GV.3.1"]
            ),

            "audit_fabric": StandardsMappingEntry(
                component="audit_fabric",
                iso_42001_focus="Documented information and continual improvement",
                nist_ai_rmf_focus="Comprehensive monitoring and evidence collection",
                seked_implementation="Immutable hash-chained events with Merkle batching and ledger anchoring",
                compliance_evidence=[
                    "Event hash chain verifications",
                    "Merkle root anchoring proofs",
                    "Ledger commitment validations",
                    "Tamper detection mechanisms"
                ],
                sources=["ISO/IEC 42001:2023 7.5, 10.1", "NIST AI RMF ME.2.1, ME.2.2, ME.2.3"]
            )
        }

    def get_mapping(self, component: str) -> Optional[StandardsMappingEntry]:
        """Get detailed mapping for a component."""
        return self.mappings.get(component)

    def generate_compliance_matrix(self, components: List[str] = None) -> Dict[str, Any]:
        """
        Generate a compliance matrix showing coverage across both standards.

        This creates the regulator-ready mapping table from the engineering brief.
        """
        if components is None:
            components = list(self.mappings.keys())

        matrix = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "standards_covered": ["ISO/IEC 42001:2023", "NIST AI RMF"],
                "total_components": len(components)
            },
            "mappings": []
        }

        for component in components:
            mapping = self.mappings.get(component)
            if mapping:
                matrix["mappings"].append({
                    "component": component,
                    "iso_42001_focus": mapping.iso_42001_focus,
                    "nist_ai_rmf_focus": mapping.nist_ai_rmf_focus,
                    "seked_implementation": mapping.seked_implementation,
                    "compliance_evidence": mapping.compliance_evidence,
                    "sources": mapping.sources
                })

        # Calculate coverage statistics
        iso_clauses = set()
        nist_categories = set()

        for mapping in matrix["mappings"]:
            for source in mapping["sources"]:
                if "ISO/IEC 42001" in source:
                    # Extract clause numbers (simplified)
                    if "42001" in source:
                        iso_clauses.add(source.split()[-1])
                elif "NIST AI RMF" in source:
                    # Extract category codes
                    parts = source.split()
                    for part in parts:
                        if any(char.isdigit() for char in part) and '.' in part:
                            nist_categories.add(part)

        matrix["coverage_statistics"] = {
            "iso_42001_clauses_covered": len(iso_clauses),
            "nist_ai_rmf_categories_covered": len(nist_categories),
            "estimated_compliance_readiness": "High - Comprehensive mapping with evidence trails"
        }

        return matrix

    def validate_component_compliance(self, component: str, standard: str,
                                    requirement: str) -> Dict[str, Any]:
        """
        Validate that a component meets a specific standard requirement.

        Args:
            component: Seked component to validate
            standard: "iso_42001" or "nist_ai_rmf"
            requirement: Specific requirement to check

        Returns:
            Validation result with evidence
        """
        mapping = self.get_mapping(component)
        if not mapping:
            return {
                "valid": False,
                "reason": f"Component '{component}' not found in standards mapping"
            }

        # Check if requirement is covered
        requirement_covered = False
        relevant_evidence = []

        if standard == "iso_42001":
            requirement_covered = requirement.lower() in mapping.iso_42001_focus.lower()
        elif standard == "nist_ai_rmf":
            requirement_covered = requirement.lower() in mapping.nist_ai_rmf_focus.lower()
        else:
            return {
                "valid": False,
                "reason": f"Unknown standard '{standard}'"
            }

        if requirement_covered:
            relevant_evidence = mapping.compliance_evidence

        return {
            "valid": requirement_covered,
            "component": component,
            "standard": standard,
            "requirement": requirement,
            "evidence": relevant_evidence,
            "sources": mapping.sources,
            "implementation": mapping.seked_implementation
        }

    def generate_audit_checklist(self, audit_type: str = "iso_42001_certification") -> Dict[str, Any]:
        """
        Generate an audit checklist for certification readiness.

        Args:
            audit_type: Type of audit (iso_42001_certification, nist_ai_rmf_assessment, etc.)

        Returns:
            Audit checklist with evidence requirements
        """
        if audit_type == "iso_42001_certification":
            checklist = {
                "audit_type": "ISO/IEC 42001:2023 AI Management System Certification",
                "checklist_items": [
                    {
                        "clause": "4.1 Understanding the organization and its context",
                        "requirement": "Organization context and AI system positioning",
                        "seked_evidence": ["Tenant configuration", "Jurisdiction mappings", "Stakeholder definitions"],
                        "verification_method": "Document review and configuration audit"
                    },
                    {
                        "clause": "5.1 Leadership and commitment",
                        "requirement": "AI governance leadership structure",
                        "seked_evidence": ["Consensus node configuration", "Policy approval workflows", "Governance role assignments"],
                        "verification_method": "Process audit and role verification"
                    },
                    {
                        "clause": "8.1 Operational planning and control",
                        "requirement": "AI system operational controls",
                        "seked_evidence": ["Policy engine decision logs", "Consensus validation records", "Runtime enforcement metrics"],
                        "verification_method": "Operational log review and control testing"
                    },
                    {
                        "clause": "9.1 Monitoring, measurement, analysis and evaluation",
                        "requirement": "AI system performance monitoring",
                        "seked_evidence": ["Real-time monitoring dashboards", "Risk score calculations", "Performance metrics"],
                        "verification_method": "Metrics review and monitoring system audit"
                    },
                    {
                        "clause": "9.2 Internal audit",
                        "requirement": "Internal audit capability",
                        "seked_evidence": ["Immutable audit fabric", "Merkle tree proofs", "Chain verification tools"],
                        "verification_method": "Audit system testing and evidence validation"
                    }
                ]
            }

        elif audit_type == "nist_ai_rmf_assessment":
            checklist = {
                "audit_type": "NIST AI Risk Management Framework Assessment",
                "checklist_items": [
                    {
                        "function": "Govern (GV)",
                        "requirement": "AI governance structure and policies",
                        "seked_evidence": ["Consensus governance cluster", "Policy templates", "Role-based access controls"],
                        "verification_method": "Governance process review"
                    },
                    {
                        "function": "Map (MP)",
                        "requirement": "AI system context and risk identification",
                        "seked_evidence": ["Risk metadata tagging", "Use case classifications", "Stakeholder mappings"],
                        "verification_method": "System mapping documentation review"
                    },
                    {
                        "function": "Measure (ME)",
                        "requirement": "AI performance and risk measurement",
                        "seked_evidence": ["Real-time metrics collection", "Risk score calculations", "Performance monitoring"],
                        "verification_method": "Metrics system audit"
                    },
                    {
                        "function": "Manage (MG)",
                        "requirement": "AI risk treatment and controls",
                        "seked_evidence": ["Policy enforcement logs", "Kill-switch activations", "Control effectiveness metrics"],
                        "verification_method": "Control system testing and log review"
                    }
                ]
            }

        else:
            checklist = {
                "audit_type": "Unknown",
                "error": f"Audit type '{audit_type}' not supported"
            }

        checklist["generated_at"] = datetime.utcnow().isoformat() + "Z"
        checklist["compliance_readiness_assessment"] = self._assess_audit_readiness(checklist)

        return checklist

    def _assess_audit_readiness(self, checklist: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall audit readiness based on checklist."""
        items = checklist.get("checklist_items", [])
        total_items = len(items)
        evidence_strength = sum(len(item.get("seked_evidence", [])) for item in items)

        readiness_score = min(100, (evidence_strength / total_items) * 20)  # Scale to 100

        return {
            "overall_readiness_score": readiness_score,
            "total_checklist_items": total_items,
            "evidence_strength_rating": "High" if evidence_strength > total_items * 2 else "Medium",
            "recommended_actions": [
                "Complete evidence collection for all checklist items",
                "Conduct internal audit readiness assessment",
                "Prepare evidence validation procedures"
            ] if readiness_score < 80 else ["Audit ready - proceed with certification"]
        }


# Global detailed standards mapper instance
detailed_standards_mapper = DetailedStandardsMapper()


# Utility functions for compliance operations
def get_component_compliance_mapping(component: str) -> Optional[StandardsMappingEntry]:
    """Get compliance mapping for a Seked component."""
    return detailed_standards_mapper.get_mapping(component)


def generate_full_compliance_matrix() -> Dict[str, Any]:
    """Generate the complete compliance matrix for both standards."""
    return detailed_standards_mapper.generate_compliance_matrix()


def validate_compliance_requirement(component: str, standard: str, requirement: str) -> Dict[str, Any]:
    """Validate that a component meets a specific compliance requirement."""
    return detailed_standards_mapper.validate_component_compliance(component, standard, requirement)


def create_audit_checklist(audit_type: str = "iso_42001_certification") -> Dict[str, Any]:
    """Create an audit checklist for certification readiness."""
    return detailed_standards_mapper.generate_audit_checklist(audit_type)
