"""UACP Pydantic models."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    IDLE = "idle"
    INTERROGATING = "interrogating"
    PHASE_LOCKED = "phase_locked"
    ERROR = "error"


class SpeculativePath(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    label: str
    confidence: float  # 0.0 – 1.0
    pruned: bool = False
    reasoning: Optional[str] = None


class OrchestrationRequest(BaseModel):
    prompt: str
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    temperature: float = 0.7
    zeno_cycles: int = Field(default=64, ge=1, le=512)
    stream: bool = True


class OrchestrationResult(BaseModel):
    session_id: str
    request_id: str
    response: str
    model: str
    speculative_paths: List[SpeculativePath]
    zeno_cycles_used: int
    confidence: float
    tokens_used: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SessionState(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.IDLE
    tenant_id: Optional[str] = None
    message_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)


class TelemetryEvent(BaseModel):
    event: str  # e.g. "zeno_tick", "path_pruned", "phase_locked", "token"
    session_id: str
    data: Dict[str, Any] = {}
    ts: datetime = Field(default_factory=datetime.utcnow)


class MeshNode(BaseModel):
    id: str
    role: str  # "host", "client", "server"
    label: str
    status: str = "active"
    capabilities: List[str] = []


class MeshTopology(BaseModel):
    nodes: List[MeshNode]
    edges: List[Dict[str, str]]  # [{"from": id, "to": id, "label": str}]
    session_id: Optional[str] = None
