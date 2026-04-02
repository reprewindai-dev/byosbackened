"""Pydantic schemas for traffic pattern JSONB fields."""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional, List, Union


class PatternDataSchema(BaseModel):
    """
    Schema for pattern_data JSONB field.
    
    Format varies by pattern_type:
    - "daily": {hour: count} where hour is 0-23
    - "weekly": {day: count} where day is 0-6 (Monday=0)
    - "seasonal": {month: count} where month is 1-12
    - "custom": {key: value} flexible format
    """
    
    pattern_type: str = Field(..., description="Pattern type: daily, weekly, seasonal, custom")
    data: Dict[str, Union[int, float]] = Field(
        ...,
        description="Pattern data dictionary",
        min_length=1,
    )
    
    @field_validator("pattern_type")
    @classmethod
    def validate_pattern_type(cls, v: str) -> str:
        """Validate pattern type."""
        valid_types = ["daily", "weekly", "seasonal", "custom"]
        if v not in valid_types:
            raise ValueError(f"pattern_type must be one of {valid_types}, got: {v}")
        return v
    
    @field_validator("data")
    @classmethod
    def validate_data(cls, v: Dict, info) -> Dict[str, Union[int, float]]:
        """Validate pattern data based on pattern type."""
        pattern_type = info.data.get("pattern_type", "custom")
        
        if pattern_type == "daily":
            # Validate hour keys are 0-23
            for key in v.keys():
                try:
                    hour = int(key)
                    if hour < 0 or hour > 23:
                        raise ValueError(f"Hour must be 0-23, got: {hour}")
                except ValueError:
                    raise ValueError(f"Invalid hour key: {key}")
        
        elif pattern_type == "weekly":
            # Validate day keys are 0-6
            for key in v.keys():
                try:
                    day = int(key)
                    if day < 0 or day > 6:
                        raise ValueError(f"Day must be 0-6, got: {day}")
                except ValueError:
                    raise ValueError(f"Invalid day key: {key}")
        
        elif pattern_type == "seasonal":
            # Validate month keys are 1-12
            for key in v.keys():
                try:
                    month = int(key)
                    if month < 1 or month > 12:
                        raise ValueError(f"Month must be 1-12, got: {month}")
                except ValueError:
                    raise ValueError(f"Invalid month key: {key}")
        
        # Validate values are numeric and non-negative
        for key, value in v.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Value must be numeric, got: {value} for key {key}")
            if value < 0:
                raise ValueError(f"Value must be non-negative, got: {value} for key {key}")
        
        return v
    
    @classmethod
    def validate_jsonb(cls, data: Dict, pattern_type: Optional[str] = None) -> Dict[str, Union[int, float]]:
        """
        Validate JSONB data and return validated dictionary.
        
        This is the main validation function to use before storing in DB.
        """
        # If data is already a dict, validate it
        if isinstance(data, dict):
            # Extract pattern_type from data if not provided
            if pattern_type is None:
                pattern_type = data.get("pattern_type", "custom")
            
            # If data has 'data' key, use it
            if "data" in data:
                schema = cls(pattern_type=pattern_type, data=data["data"])
                return schema.data
            else:
                # Assume entire dict is the pattern data
                schema = cls(pattern_type=pattern_type, data=data)
                return schema.data
        
        raise ValueError(f"Invalid pattern_data format: {data}")
    
    @classmethod
    def from_dict(cls, data: Dict, pattern_type: str) -> Dict[str, Union[int, float]]:
        """Create validated pattern data dict from input data."""
        return cls.validate_jsonb(data, pattern_type)


def validate_pattern_data(data: Dict, pattern_type: str) -> Dict[str, Union[int, float]]:
    """
    Validate pattern_data JSONB field.
    
    Use this function before storing pattern_data in the database.
    
    Args:
        data: Dictionary of pattern data
        pattern_type: Type of pattern (daily, weekly, seasonal, custom)
        
    Returns:
        Validated dictionary
        
    Raises:
        ValueError: If validation fails
    """
    return PatternDataSchema.validate_jsonb(data, pattern_type)
