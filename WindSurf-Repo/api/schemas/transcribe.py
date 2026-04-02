"""Transcribe schemas."""

from pydantic import BaseModel
from typing import Optional


class TranscribeRequest(BaseModel):
    """Transcribe request."""

    asset_id: str
    language: Optional[str] = None
    provider: Optional[str] = None  # "huggingface", "local_whisper", "openai"


class TranscribeResponse(BaseModel):
    """Transcribe response."""

    job_id: str
    status: str
    message: str
    requested_provider: Optional[str] = None
    resolved_provider: Optional[str] = None
    policy_enforcement: Optional[str] = None
    was_fallback: Optional[bool] = None
