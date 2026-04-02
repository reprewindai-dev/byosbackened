"""Signal Field - Core persistent data structure for Seked-Based Signal Coherence AGI."""
from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import json
from dataclasses import dataclass, asdict
from collections import defaultdict


class CollapseIndicator(str, Enum):
    """Empire collapse patterns encoded as permanent safeguards."""
    OVEREXPANSION = "overexpansion"
    INTERNAL_CORRUPTION = "internal_corruption"
    RESOURCE_DEPLETION = "resource_depletion"
    LOSS_OF_IDENTITY = "loss_of_identity"
    FAILURE_TO_ADAPT = "failure_to_adapt"
    EXTERNAL_INTERNAL_COMBO = "external_internal_combo"
    NEGLECT_OF_BASE = "neglect_of_base"
    HUBRIS_ARROGANCE = "hubris_arrogance"


class ReferenceStar(BaseModel):
    """Stable truths, constraints, and identity commitments."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Star identifier")
    category: str = Field(..., description="Category (mission, constraint, identity, etc.)")
    value: Any = Field(..., description="The stable truth or commitment")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence in this star")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_validated: datetime = Field(default_factory=datetime.utcnow)
    validation_count: int = Field(0, description="How many times validated")
    source: str = Field(..., description="Source of this reference star")


class IntentVector(BaseModel):
    """Direction and momentum of goals."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Intent identifier")
    direction: str = Field(..., description="What outcome this pushes toward")
    magnitude: float = Field(..., description="How strongly evidence supports direction")
    momentum: float = Field(0.0, description="Current momentum (accelerates/decelerates)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    source_stars: List[str] = Field(default_factory=list, description="Reference stars supporting this")
    fracture_points: List[str] = Field(default_factory=list, description="Related fracture points")


class TrustWeight(BaseModel):
    """Source reliability, recency, and corroboration scores."""
    source_id: str = Field(..., description="Unique source identifier")
    reliability_score: float = Field(0.5, ge=0.0, le=1.0, description="Historical reliability")
    recency_score: float = Field(1.0, ge=0.0, le=1.0, description="How recent the information")
    corroboration_score: float = Field(0.0, ge=0.0, le=1.0, description="How many sources agree")
    total_interactions: int = Field(0, description="Total interactions with this source")
    successful_interactions: int = Field(0, description="Successful interactions")
    last_interaction: Optional[datetime] = Field(None, description="Last interaction timestamp")
    domain_expertise: Dict[str, float] = Field(default_factory=dict, description="Expertise by domain")


class FracturePoint(BaseModel):
    """Locations where narratives, evidence, or goals diverge."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Fracture identifier")
    description: str = Field(..., description="What diverges here")
    narratives: List[str] = Field(default_factory=list, description="Conflicting narratives")
    evidence_strength: Dict[str, float] = Field(default_factory=dict, description="Strength of evidence for each narrative")
    resolution_attempts: List[Dict[str, Any]] = Field(default_factory=list, description="Attempts to resolve")
    fracture_score: float = Field(0.0, ge=0.0, le=1.0, description="Severity of fracture (0-1)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class InteractionLog(BaseModel):
    """Universal data model for logging all interactions."""
    app_id: str = Field(..., description="System identifier")
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique session identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Interaction timestamp")
    input_type: str = Field(..., description="Type of input (prompt/sensor/internal)")
    output_type: str = Field(..., description="Type of output (action/analysis/signal)")
    action_taken: str = Field("", description="Specific action description")
    success: bool = Field(True, description="Whether interaction was successful")
    duration_ms: float = Field(0.0, description="Duration in milliseconds")
    intent_vector: Optional[Dict[str, Any]] = Field(None, description="Intent vector data")
    fracture_score: float = Field(0.0, ge=0.0, le=1.0, description="Fracture score for this interaction")
    detrimental_score: float = Field(0.0, ge=0.0, le=1.0, description="Detrimental impact score")
    collapse_indicators: List[CollapseIndicator] = Field(default_factory=list, description="Active collapse indicators")
    seked_proportion: float = Field(1.0, description="Seked slope ratio (intent:action proportionality)")
    notes: Optional[str] = Field(None, description="Optional context or notes")


@dataclass
class SignalField:
    """Core persistent data structure for Seked-Based Signal Coherence AGI."""

    # Core components
    reference_stars: Dict[str, ReferenceStar] = None
    intent_vectors: Dict[str, IntentVector] = None
    trust_weights: Dict[str, TrustWeight] = None
    fracture_map: Dict[str, FracturePoint] = None

    # Temporal components
    interaction_history: List[InteractionLog] = None
    temporal_chains: Dict[str, List[str]] = None  # Chains of related interactions

    # Seked foundation
    seked_proportions: Dict[str, float] = None
    structural_integrity_score: float = 1.0

    # Empire collapse prevention
    active_collapse_indicators: Set[CollapseIndicator] = None
    collapse_prevention_actions: Dict[CollapseIndicator, List[str]] = None

    def __post_init__(self):
        if self.reference_stars is None:
            self.reference_stars = {}
        if self.intent_vectors is None:
            self.intent_vectors = {}
        if self.trust_weights is None:
            self.trust_weights = {}
        if self.fracture_map is None:
            self.fracture_map = {}
        if self.interaction_history is None:
            self.interaction_history = []
        if self.temporal_chains is None:
            self.temporal_chains = defaultdict(list)
        if self.seked_proportions is None:
            self.seked_proportions = {}
        if self.active_collapse_indicators is None:
            self.active_collapse_indicators = set()
        if self.collapse_prevention_actions is None:
            self.collapse_prevention_actions = defaultdict(list)

    def add_reference_star(self, star: ReferenceStar) -> str:
        """Add a reference star to the signal field."""
        self.reference_stars[star.id] = star
        return star.id

    def get_reference_star(self, star_id: str) -> Optional[ReferenceStar]:
        """Retrieve a reference star."""
        return self.reference_stars.get(star_id)

    def add_intent_vector(self, vector: IntentVector) -> str:
        """Add an intent vector to the signal field."""
        self.intent_vectors[vector.id] = vector
        return vector.id

    def update_trust_weight(self, source_id: str, success: bool, domain: Optional[str] = None) -> None:
        """Update trust weight for a source."""
        if source_id not in self.trust_weights:
            self.trust_weights[source_id] = TrustWeight(source_id=source_id)

        weight = self.trust_weights[source_id]
        weight.total_interactions += 1
        if success:
            weight.successful_interactions += 1

        weight.reliability_score = weight.successful_interactions / weight.total_interactions
        weight.last_interaction = datetime.utcnow()

        # Update recency (decays over time)
        if weight.last_interaction:
            hours_since = (datetime.utcnow() - weight.last_interaction).total_seconds() / 3600
            weight.recency_score = max(0.1, 1.0 - (hours_since / 24))  # Decay over 24 hours

        # Update domain expertise
        if domain:
            if domain not in weight.domain_expertise:
                weight.domain_expertise[domain] = 0.5
            # Simple update: move toward success rate
            weight.domain_expertise[domain] = 0.9 * weight.domain_expertise[domain] + 0.1 * (1.0 if success else 0.0)

    def add_fracture_point(self, fracture: FracturePoint) -> str:
        """Add a fracture point to the signal field."""
        self.fracture_map[fracture.id] = fracture
        return fracture.id

    def log_interaction(self, interaction: InteractionLog) -> None:
        """Log an interaction to the signal field."""
        self.interaction_history.append(interaction)

        # Update trust weights based on interaction
        if interaction.input_type == "external":
            success = interaction.success
            domain = interaction.output_type
            # Extract source from interaction if available
            source = getattr(interaction, 'source', 'unknown')
            self.update_trust_weight(source, success, domain)

        # Check for collapse indicators
        self._check_collapse_indicators(interaction)

        # Maintain temporal chains
        self._update_temporal_chains(interaction)

        # Keep only recent history (last 1000 interactions)
        if len(self.interaction_history) > 1000:
            self.interaction_history = self.interaction_history[-1000:]

    def _check_collapse_indicators(self, interaction: InteractionLog) -> None:
        """Check for empire collapse indicators in interaction."""
        indicators = []

        # Overexpansion: Too many simultaneous goals
        if len(self.intent_vectors) > 10:
            indicators.append(CollapseIndicator.OVEREXPANSION)

        # Internal corruption: Low trust scores across sources
        avg_trust = sum(w.reliability_score for w in self.trust_weights.values()) / max(1, len(self.trust_weights))
        if avg_trust < 0.3:
            indicators.append(CollapseIndicator.INTERNAL_CORRUPTION)

        # Resource depletion: High detrimental scores
        if interaction.detrimental_score > 0.7:
            indicators.append(CollapseIndicator.RESOURCE_DEPLETION)

        # Loss of identity: Low reference star confidence
        avg_star_confidence = sum(s.confidence for s in self.reference_stars.values()) / max(1, len(self.reference_stars))
        if avg_star_confidence < 0.5:
            indicators.append(CollapseIndicator.LOSS_OF_IDENTITY)

        # Failure to adapt: High fracture scores consistently
        recent_fractures = [i.fracture_score for i in self.interaction_history[-10:]]
        if recent_fractures and sum(recent_fractures) / len(recent_fractures) > 0.6:
            indicators.append(CollapseIndicator.FAILURE_TO_ADAPT)

        # Update active indicators
        for indicator in indicators:
            self.active_collapse_indicators.add(indicator)

    def _update_temporal_chains(self, interaction: InteractionLog) -> None:
        """Update temporal chains of related interactions."""
        # Simple implementation: chain by app_id and intent similarity
        chain_key = f"{interaction.app_id}_{interaction.intent_vector.get('direction', 'unknown') if interaction.intent_vector else 'unknown'}"
        self.temporal_chains[chain_key].append(interaction.run_id)

        # Keep only recent chains (last 50 interactions per chain)
        if len(self.temporal_chains[chain_key]) > 50:
            self.temporal_chains[chain_key] = self.temporal_chains[chain_key][-50:]

    def get_structural_integrity(self) -> float:
        """Calculate overall structural integrity of the signal field."""
        factors = []

        # Reference star stability
        if self.reference_stars:
            avg_confidence = sum(s.confidence for s in self.reference_stars.values()) / len(self.reference_stars)
            factors.append(avg_confidence)

        # Intent vector coherence
        if self.intent_vectors:
            avg_magnitude = sum(v.magnitude for v in self.intent_vectors.values()) / len(self.intent_vectors)
            factors.append(avg_magnitude)

        # Trust network health
        if self.trust_weights:
            avg_trust = sum(w.reliability_score * w.recency_score for w in self.trust_weights.values()) / len(self.trust_weights)
            factors.append(avg_trust)

        # Fracture severity (inverse)
        fracture_severity = sum(f.fracture_score for f in self.fracture_map.values()) / max(1, len(self.fracture_map))
        factors.append(1.0 - fracture_severity)

        # Collapse indicator count (inverse)
        collapse_penalty = len(self.active_collapse_indicators) * 0.1
        factors.append(max(0.0, 1.0 - collapse_penalty))

        return sum(factors) / max(1, len(factors))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize signal field to dictionary."""
        return {
            "reference_stars": {k: v.dict() for k, v in self.reference_stars.items()},
            "intent_vectors": {k: v.dict() for k, v in self.intent_vectors.items()},
            "trust_weights": {k: v.dict() for k, v in self.trust_weights.items()},
            "fracture_map": {k: v.dict() for k, v in self.fracture_map.items()},
            "interaction_history": [i.dict() for i in self.interaction_history],
            "temporal_chains": dict(self.temporal_chains),
            "seked_proportions": self.seked_proportions,
            "structural_integrity_score": self.structural_integrity_score,
            "active_collapse_indicators": [i.value for i in self.active_collapse_indicators],
            "collapse_prevention_actions": dict(self.collapse_prevention_actions),
        }


# Global signal field instance
signal_field = SignalField()
