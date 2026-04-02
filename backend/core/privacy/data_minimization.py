"""Data minimization - only collect necessary data."""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def minimize_data_collection(
    data: Dict[str, Any],
    required_fields: List[str],
    optional_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Minimize data collection - only keep required and optional fields.
    
    Removes any fields not in required_fields or optional_fields.
    """
    if optional_fields is None:
        optional_fields = []
    
    allowed_fields = set(required_fields + optional_fields)
    minimized = {k: v for k, v in data.items() if k in allowed_fields}
    
    removed_fields = set(data.keys()) - allowed_fields
    if removed_fields:
        logger.info(f"Data minimization: removed fields {removed_fields}")
    
    return minimized


def validate_purpose_limitation(
    data: Dict[str, Any],
    stated_purpose: str,
    purpose_mapping: Dict[str, List[str]]
) -> bool:
    """
    Validate that data is only used for stated purpose.
    
    purpose_mapping: Maps purpose to allowed fields.
    """
    allowed_fields = purpose_mapping.get(stated_purpose, [])
    data_fields = set(data.keys())
    
    if not data_fields.issubset(allowed_fields):
        disallowed = data_fields - set(allowed_fields)
        logger.warning(f"Purpose limitation violation: fields {disallowed} not allowed for purpose {stated_purpose}")
        return False
    
    return True
