"""Pydantic schemas for anomaly JSONB fields."""
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any, List, Union


class AnomalyMetadataSchema(BaseModel):
    """
    Schema for anomaly metadata JSONB field.
    
    Flexible schema for storing additional context about anomalies.
    Common fields:
    - operation_type: str
    - provider: str
    - affected_operations: List[str]
    - related_anomaly_ids: List[str]
    - context: Dict[str, Any]
    """
    
    operation_type: Optional[str] = Field(None, description="Operation type affected")
    provider: Optional[str] = Field(None, description="Provider involved")
    affected_operations: Optional[List[str]] = Field(None, description="List of affected operation IDs")
    related_anomaly_ids: Optional[List[str]] = Field(None, description="Related anomaly IDs")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    
    # Allow additional fields
    class Config:
        extra = "allow"
    
    @classmethod
    def validate_jsonb(cls, data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """
        Validate JSONB data and return validated dictionary.
        
        This is the main validation function to use before storing in DB.
        Returns None if data is None (metadata is optional).
        """
        if data is None:
            return None
        
        if not isinstance(data, dict):
            raise ValueError(f"metadata must be a dictionary, got: {type(data)}")
        
        # Validate known fields
        validated = {}
        
        if "operation_type" in data:
            if not isinstance(data["operation_type"], str):
                raise ValueError(f"operation_type must be string, got: {type(data['operation_type'])}")
            validated["operation_type"] = data["operation_type"]
        
        if "provider" in data:
            if not isinstance(data["provider"], str):
                raise ValueError(f"provider must be string, got: {type(data['provider'])}")
            validated["provider"] = data["provider"]
        
        if "affected_operations" in data:
            if not isinstance(data["affected_operations"], list):
                raise ValueError(f"affected_operations must be list, got: {type(data['affected_operations'])}")
            if not all(isinstance(op, str) for op in data["affected_operations"]):
                raise ValueError("All items in affected_operations must be strings")
            validated["affected_operations"] = data["affected_operations"]
        
        if "related_anomaly_ids" in data:
            if not isinstance(data["related_anomaly_ids"], list):
                raise ValueError(f"related_anomaly_ids must be list, got: {type(data['related_anomaly_ids'])}")
            if not all(isinstance(id, str) for id in data["related_anomaly_ids"]):
                raise ValueError("All items in related_anomaly_ids must be strings")
            validated["related_anomaly_ids"] = data["related_anomaly_ids"]
        
        if "context" in data:
            if not isinstance(data["context"], dict):
                raise ValueError(f"context must be dictionary, got: {type(data['context'])}")
            validated["context"] = data["context"]
        
        # Copy any additional fields
        for key, value in data.items():
            if key not in validated:
                validated[key] = value
        
        return validated
    
    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Create validated metadata dict from input data."""
        return cls.validate_jsonb(data)


def validate_anomaly_metadata(data: Optional[Dict]) -> Optional[Dict[str, Any]]:
    """
    Validate anomaly metadata JSONB field.
    
    Use this function before storing metadata in the database.
    
    Args:
        data: Dictionary of metadata (can be None)
        
    Returns:
        Validated dictionary or None
        
    Raises:
        ValueError: If validation fails
    """
    return AnomalyMetadataSchema.validate_jsonb(data)
