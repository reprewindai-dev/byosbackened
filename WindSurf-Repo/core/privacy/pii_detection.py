"""PII detection - regex + HuggingFace BERT-NER hybrid."""

import re
import asyncio
import logging
from typing import List, Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class PII_TYPE(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    PERSON = "person"
    ORG = "organization"
    LOCATION = "location"


PII_PATTERNS = {
    PII_TYPE.EMAIL: re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    PII_TYPE.PHONE: re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b"),
    PII_TYPE.CREDIT_CARD: re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    PII_TYPE.SSN: re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    PII_TYPE.IP_ADDRESS: re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
}

# NER entity groups that map to PII
NER_PII_MAP = {
    "PER": PII_TYPE.PERSON,
    "ORG": PII_TYPE.ORG,
    "LOC": PII_TYPE.LOCATION,
    "MISC": None,
}


def detect_pii(text: str) -> List[Dict[str, str]]:
    """Detect PII using regex patterns (sync, fast)."""
    detected = []
    for pii_type, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            detected.append({"type": pii_type.value, "value": match.group(), "start": match.start(), "end": match.end()})
    return detected


async def detect_pii_with_ner(text: str) -> List[Dict[str, Any]]:
    """Detect PII using regex + HuggingFace BERT-NER (async, comprehensive)."""
    # First get regex matches
    detected = detect_pii(text)

    # Then run HF NER
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        provider = HuggingFaceProvider()
        entities = await provider.detect_entities(text)
        for entity in entities:
            ner_group = entity.get("entity_group", "")
            pii_type = NER_PII_MAP.get(ner_group)
            if pii_type:
                detected.append({
                    "type": pii_type.value,
                    "value": entity.get("word", ""),
                    "score": entity.get("score", 0),
                    "start": entity.get("start", 0),
                    "end": entity.get("end", 0),
                    "source": "ner",
                })
    except Exception as e:
        logger.warning(f"HF NER detection failed, using regex only: {e}")

    return detected


def mask_pii(text: str, pii_types: Optional[List[PII_TYPE]] = None, strategy: str = "partial") -> str:
    """Mask PII in text."""
    types_to_mask = set(pii_types) if pii_types else set(PII_PATTERNS.keys())
    result = text
    for pii_type, pattern in PII_PATTERNS.items():
        if pii_type not in types_to_mask:
            continue
        if strategy == "full":
            result = pattern.sub("[REDACTED]", result)
        elif strategy == "partial":
            def partial_mask(m):
                val = m.group()
                keep = max(1, len(val) // 4)
                return val[:keep] + "*" * (len(val) - keep)
            result = pattern.sub(partial_mask, result)
    return result


def detect_and_mask_pii(text: str, strategy: str = "partial") -> Dict[str, Any]:
    """Detect and mask PII in one call."""
    detected = detect_pii(text)
    masked = mask_pii(text, strategy=strategy)
    return {"original": text, "masked": masked, "pii_detected": detected, "has_pii": len(detected) > 0}
