"""Pydantic models for Veklom SDK request/response shapes."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class CompletionRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.7
    workspace_id: Optional[str] = None


class CompleteResponse(BaseModel):
    text: str
    audit_log_id: Optional[str] = None
    provider: Optional[str] = None          # "ollama" | "groq"
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    requested_model: Optional[str] = None
    bedrock_model_id: Optional[str] = None  # kept for contract compatibility
