"""Pydantic schemas for savings report JSONB fields."""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional
from decimal import Decimal


class OperationBreakdownItem(BaseModel):
    """Schema for a single operation breakdown item."""
    
    savings: Decimal = Field(..., description="Savings for this operation type")
    count: int = Field(..., ge=0, description="Number of operations")
    baseline_cost: Optional[Decimal] = Field(None, description="Baseline cost")
    actual_cost: Optional[Decimal] = Field(None, description="Actual cost")


class BreakdownByOperationSchema(BaseModel):
    """
    Schema for breakdown_by_operation JSONB field.
    
    Format: {operation_type: {savings: Decimal, count: int, ...}}
    Example: {"transcribe": {"savings": 10.50, "count": 100}, ...}
    """
    
    breakdown: Dict[str, OperationBreakdownItem] = Field(
        ...,
        description="Breakdown by operation type",
        min_length=0,
    )
    
    @field_validator("breakdown")
    @classmethod
    def validate_breakdown(cls, v: Dict[str, Dict]) -> Dict[str, OperationBreakdownItem]:
        """Validate breakdown dictionary."""
        validated = {}
        for operation_type, data in v.items():
            if not isinstance(operation_type, str) or not operation_type:
                raise ValueError(f"Operation type must be non-empty string, got: {operation_type}")
            if not isinstance(data, dict):
                raise ValueError(f"Breakdown item must be dictionary, got: {type(data)}")
            
            # Convert to OperationBreakdownItem
            validated[operation_type] = OperationBreakdownItem(**data)
        
        return validated
    
    @classmethod
    def validate_jsonb(cls, data: Optional[Dict]) -> Optional[Dict[str, Dict]]:
        """
        Validate JSONB data and return validated dictionary.
        
        This is the main validation function to use before storing in DB.
        Returns None if data is None (field is optional).
        """
        if data is None:
            return None
        
        if not isinstance(data, dict):
            raise ValueError(f"breakdown_by_operation must be dictionary, got: {type(data)}")
        
        # If data has 'breakdown' key, use it
        if "breakdown" in data:
            schema = cls(**data)
            # Convert back to dict format for storage
            return {
                op_type: item.model_dump() for op_type, item in schema.breakdown.items()
            }
        else:
            # Assume entire dict is the breakdown
            schema = cls(breakdown=data)
            return {
                op_type: item.model_dump() for op_type, item in schema.breakdown.items()
            }
    
    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional[Dict[str, Dict]]:
        """Create validated breakdown dict from input data."""
        return cls.validate_jsonb(data)


class ProviderBreakdownItem(BaseModel):
    """Schema for a single provider breakdown item."""
    
    cost: Decimal = Field(..., description="Total cost for this provider")
    savings: Optional[Decimal] = Field(None, description="Savings vs baseline")
    count: Optional[int] = Field(None, ge=0, description="Number of operations")


class BreakdownByProviderSchema(BaseModel):
    """
    Schema for breakdown_by_provider JSONB field.
    
    Format: {provider: {cost: Decimal, savings: Decimal, count: int}}
    Example: {"openai": {"cost": 50.00, "savings": 10.00, "count": 100}, ...}
    """
    
    breakdown: Dict[str, ProviderBreakdownItem] = Field(
        ...,
        description="Breakdown by provider",
        min_length=0,
    )
    
    @field_validator("breakdown")
    @classmethod
    def validate_breakdown(cls, v: Dict[str, Dict]) -> Dict[str, ProviderBreakdownItem]:
        """Validate breakdown dictionary."""
        validated = {}
        for provider, data in v.items():
            if not isinstance(provider, str) or not provider:
                raise ValueError(f"Provider must be non-empty string, got: {provider}")
            if not isinstance(data, dict):
                raise ValueError(f"Breakdown item must be dictionary, got: {type(data)}")
            
            # Convert to ProviderBreakdownItem
            validated[provider] = ProviderBreakdownItem(**data)
        
        return validated
    
    @classmethod
    def validate_jsonb(cls, data: Optional[Dict]) -> Optional[Dict[str, Dict]]:
        """
        Validate JSONB data and return validated dictionary.
        
        This is the main validation function to use before storing in DB.
        Returns None if data is None (field is optional).
        """
        if data is None:
            return None
        
        if not isinstance(data, dict):
            raise ValueError(f"breakdown_by_provider must be dictionary, got: {type(data)}")
        
        # If data has 'breakdown' key, use it
        if "breakdown" in data:
            schema = cls(**data)
            # Convert back to dict format for storage
            return {
                provider: item.model_dump() for provider, item in schema.breakdown.items()
            }
        else:
            # Assume entire dict is the breakdown
            schema = cls(breakdown=data)
            return {
                provider: item.model_dump() for provider, item in schema.breakdown.items()
            }
    
    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional[Dict[str, Dict]]:
        """Create validated breakdown dict from input data."""
        return cls.validate_jsonb(data)


def validate_breakdown_by_operation(data: Optional[Dict]) -> Optional[Dict[str, Dict]]:
    """
    Validate breakdown_by_operation JSONB field.
    
    Use this function before storing breakdown_by_operation in the database.
    
    Args:
        data: Dictionary of operation breakdown (can be None)
        
    Returns:
        Validated dictionary or None
        
    Raises:
        ValueError: If validation fails
    """
    return BreakdownByOperationSchema.validate_jsonb(data)


def validate_breakdown_by_provider(data: Optional[Dict]) -> Optional[Dict[str, Dict]]:
    """
    Validate breakdown_by_provider JSONB field.
    
    Use this function before storing breakdown_by_provider in the database.
    
    Args:
        data: Dictionary of provider breakdown (can be None)
        
    Returns:
        Validated dictionary or None
        
    Raises:
        ValueError: If validation fails
    """
    return BreakdownByProviderSchema.validate_jsonb(data)
