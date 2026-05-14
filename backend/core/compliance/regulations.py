"""Regulation definitions."""
from typing import Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Regulation(str, Enum):
    """Supported regulations."""

    GDPR = "gdpr"
    CCPA = "ccpa"
    PIPEDA = "pipeda"
    LGPD = "lgpd"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    EU_AI_ACT = "eu_ai_act"
    PCI_DSS = "pci_dss"  # Future


class RegulationManager:
    """Manage regulation definitions and requirements."""

    def __init__(self):
        self.regulations: Dict[str, Dict] = {
            Regulation.GDPR.value: {
                "name": "General Data Protection Regulation",
                "region": "EU",
                "requirements": [
                    "data_minimization",
                    "purpose_limitation",
                    "storage_limitation",
                    "right_to_access",
                    "right_to_deletion",
                    "data_portability",
                    "audit_trail",
                    "pii_protection",
                ],
            },
            Regulation.CCPA.value: {
                "name": "California Consumer Privacy Act",
                "region": "California, US",
                "requirements": [
                    "right_to_know",
                    "right_to_delete",
                    "right_to_opt_out",
                    "audit_trail",
                ],
            },
            Regulation.SOC2.value: {
                "name": "SOC 2",
                "region": "Global",
                "requirements": [
                    "security_controls",
                    "access_controls",
                    "audit_logging",
                    "incident_response",
                ],
            },
            Regulation.HIPAA.value: {
                "name": "Health Insurance Portability and Accountability Act",
                "region": "United States",
                "requirements": [
                    "access_controls",
                    "audit_trail",
                    "encryption_at_rest",
                    "encryption_in_transit",
                    "phi_protection",
                    "pii_protection",
                ],
            },
            Regulation.EU_AI_ACT.value: {
                "name": "EU AI Act",
                "region": "EU",
                "requirements": [
                    "risk_management",
                    "logging",
                    "transparency",
                    "human_oversight",
                    "audit_trail",
                    "pii_protection",
                ],
            },
        }

    def register_regulation(self, regulation_id: str, definition: Dict):
        """Register new regulation."""
        self.regulations[regulation_id] = definition
        logger.info(f"Registered regulation: {regulation_id}")

    def get_regulation(self, regulation_id: str) -> Optional[Dict]:
        """Get regulation definition."""
        return self.regulations.get(regulation_id)

    def list_regulations(self) -> List[str]:
        """List all supported regulations."""
        return list(self.regulations.keys())

    def get_requirements(self, regulation_id: str) -> List[str]:
        """Get requirements for regulation."""
        regulation = self.get_regulation(regulation_id)
        if not regulation:
            return []
        return regulation.get("requirements", [])


# Global regulation manager
_regulation_manager = RegulationManager()


def get_regulation_manager() -> RegulationManager:
    """Get regulation manager."""
    return _regulation_manager
