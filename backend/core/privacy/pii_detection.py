"""PII detection and masking."""
import re
from typing import List, Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PII_TYPE(str, Enum):
    """PII types."""

    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    IP_ADDRESS = "ip_address"
    NAME = "name"


# Regex patterns for PII detection
PII_PATTERNS = {
    PII_TYPE.EMAIL: re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    PII_TYPE.PHONE: re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b'),
    PII_TYPE.CREDIT_CARD: re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
    PII_TYPE.SSN: re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    PII_TYPE.IP_ADDRESS: re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
}


def detect_pii(text: str) -> List[Dict[str, str]]:
    """
    Detect PII in text.
    
    Returns list of detected PII with type and value.
    """
    detected = []
    
    for pii_type, pattern in PII_PATTERNS.items():
        matches = pattern.findall(text)
        for match in matches:
            detected.append({
                "type": pii_type.value,
                "value": match,
            })
    
    return detected


def mask_pii(text: str, pii_types: Optional[List[PII_TYPE]] = None, strategy: str = "partial") -> str:
    """
    Mask PII in text.
    
    Strategies:
    - "full": Complete masking (email@example.com -> ***@***.com)
    - "partial": Partial masking (John Doe -> J*** D***)
    - "hash": Hash the value (for searchable but non-readable)
    """
    if pii_types is None:
        pii_types = list(PII_TYPE)
    
    masked_text = text
    
    for pii_type in pii_types:
        if pii_type not in PII_PATTERNS:
            continue
            
        pattern = PII_PATTERNS[pii_type]
        
        def mask_match(match):
            value = match.group(0)
            if strategy == "full":
                if pii_type == PII_TYPE.EMAIL:
                    return "***@***.***"
                elif pii_type == PII_TYPE.PHONE:
                    return "***-***-****"
                elif pii_type == PII_TYPE.CREDIT_CARD:
                    return "****-****-****-****"
                elif pii_type == PII_TYPE.SSN:
                    return "***-**-****"
                elif pii_type == PII_TYPE.IP_ADDRESS:
                    return "***.***.***.***"
                else:
                    return "***"
            elif strategy == "partial":
                if len(value) <= 2:
                    return "**"
                return value[0] + "*" * (len(value) - 2) + value[-1]
            else:  # hash
                import hashlib
                return hashlib.sha256(value.encode()).hexdigest()[:8]
        
        masked_text = pattern.sub(mask_match, masked_text)
    
    return masked_text


def detect_and_mask_pii(text: str, mask_strategy: str = "partial") -> tuple[str, List[Dict[str, str]]]:
    """Detect and mask PII in one call."""
    detected = detect_pii(text)
    if detected:
        masked = mask_pii(text, [PII_TYPE(d["type"]) for d in detected], mask_strategy)
        return masked, detected
    return text, []
