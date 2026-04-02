"""Pydantic schemas for routing strategy JSONB fields."""

from pydantic import BaseModel, Field, field_validator
from typing import Dict
from decimal import Decimal


class ProviderWeightsSchema(BaseModel):
    """
    Schema for provider_weights JSONB field.

    Format: {provider_name: weight (0.0-1.0)}
    Example: {"openai": 0.7, "huggingface": 0.3}
    """

    weights: Dict[str, float] = Field(
        ...,
        description="Provider weights dictionary",
        min_length=1,
    )

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate weights are between 0.0 and 1.0."""
        for provider, weight in v.items():
            if not isinstance(provider, str) or not provider:
                raise ValueError(f"Provider name must be non-empty string, got: {provider}")
            if not isinstance(weight, (int, float)):
                raise ValueError(f"Weight must be numeric, got: {weight} for provider {provider}")
            if weight < 0.0 or weight > 1.0:
                raise ValueError(
                    f"Weight must be between 0.0 and 1.0, got: {weight} for provider {provider}"
                )
        return v

    @classmethod
    def validate_jsonb(cls, data: Dict) -> Dict[str, float]:
        """
        Validate JSONB data and return validated dictionary.

        This is the main validation function to use before storing in DB.
        """
        # If data is already a dict of weights, validate it
        if isinstance(data, dict) and all(isinstance(k, str) for k in data.keys()):
            schema = cls(weights=data)
            return schema.weights

        # If data has 'weights' key, extract it
        if isinstance(data, dict) and "weights" in data:
            schema = cls(**data)
            return schema.weights

        raise ValueError(f"Invalid provider_weights format: {data}")

    @classmethod
    def from_dict(cls, data: Dict) -> Dict[str, float]:
        """Create validated weights dict from input data."""
        return cls.validate_jsonb(data)


def validate_provider_weights(data: Dict) -> Dict[str, float]:
    """
    Validate provider_weights JSONB field.

    Use this function before storing provider_weights in the database.

    Args:
        data: Dictionary of provider weights

    Returns:
        Validated dictionary

    Raises:
        ValueError: If validation fails
    """
    return ProviderWeightsSchema.validate_jsonb(data)
