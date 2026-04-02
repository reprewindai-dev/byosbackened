"""Data models for signal coherence AGI system."""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class ReferenceStar(BaseModel):
    """Reference star in the signal field."""
    id: Optional[str] = None
    name: str
    coordinates: Dict[str, float]
    intensity: float
    metadata: Dict[str, Any] = {}


class IntentVector(BaseModel):
    """Intent vector in the signal field."""
    id: Optional[str] = None
    direction: List[float]
    magnitude: float
    source: str
    timestamp: Optional[datetime] = None


class TrustWeight(BaseModel):
    """Trust weight in the system."""
    id: Optional[str] = None
    source: str
    target: str
    weight: float


class FracturePoint(BaseModel):
    """Fracture point in the signal field."""
    id: Optional[str] = None
    location: List[float]
    severity: float
    timestamp: datetime


class InteractionLog(BaseModel):
    """Log of an interaction in the system."""
    id: Optional[str] = None
    timestamp: datetime
    interaction_type: str
    data: Dict[str, Any]


class StructuralElement(BaseModel):
    """Structural element in the signal field."""
    id: Optional[str] = None
    element_type: str
    properties: Dict[str, Any]


class CollapseIndicator(BaseModel):
    """Collapse indicator for system health."""
    indicator_type: str
    severity: float
    timestamp: datetime
    details: Dict[str, Any]


class NorthStar(BaseModel):
    """North star (primary navigation reference)."""
    id: Optional[str] = None
    name: str
    coordinates: List[float]
    priority: float


class Waypoint(BaseModel):
    """Navigation waypoint."""
    id: Optional[str] = None
    name: str
    coordinates: List[float]
    sequence: int


class ValidationRequest(BaseModel):
    """Request to validate an interpretation."""
    interpretation: str
    source: str


class IntentImpactScore(BaseModel):
    """Score for intent impact analysis."""
    score: float
    factors: Dict[str, float]


class SignalFracture(BaseModel):
    """Signal fracture resolution request."""
    fracture_id: str
    resolution_type: str
    parameters: Dict[str, Any]


class EmergencyProtocol(BaseModel):
    """Emergency protocol execution request."""
    protocol_type: str
    severity_level: float
    actions: List[str]
