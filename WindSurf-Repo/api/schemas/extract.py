"""Extract schemas."""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class ExtractRequest(BaseModel):
    """Extract request."""

    asset_id: Optional[str] = None
    transcript_id: Optional[str] = None
    text: Optional[str] = None
    task: str  # "hooks", "summary", "timestamps", "titles"
    provider: Optional[str] = None  # "huggingface", "local_llm", "openai"
    options: Optional[Dict[str, Any]] = None


class ExtractResponse(BaseModel):
    """Extract response."""

    result: Dict[str, Any]
    provider: str
    model: str
    requested_provider: Optional[str] = None
    resolved_provider: Optional[str] = None
    policy_enforcement: Optional[str] = None
    was_fallback: Optional[bool] = None
