"""Shadow Tracking and Intent Vector Analysis - Advanced intelligence layer."""
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import math
from core.signal_coherence.signal_field import signal_field, IntentVector, ReferenceStar
from core.signal_coherence.watchtower_network import watchtower_network


class IntentVectorAnalysis(BaseModel):
    """Advanced intent vector with shadow tracking."""
    vector_id: str = Field(..., description="Analysis identifier")
    base_vector: IntentVector = Field(..., description="Base intent vector")
    shadow_forces: List[Dict[str, Any]] = Field(default_factory=list, description="Unseen forces behind visible motion")
    hidden_intent: str = Field("", description="Inferred hidden intent")
    evidence_strength: float = Field(0.0, ge=0.0, le=1.0, description="Strength of evidence for hidden intent")
    trajectory_prediction: List[Dict[str, Any]] = Field(default_factory=list, description="Predicted trajectory")
    risk_assessment: Dict[str, Any] = Field(default_factory=dict, description="Risk assessment")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class ShadowForce(BaseModel):
    """An unseen force influencing visible motion."""
    force_id: str = Field(..., description="Unique force identifier")
    force_type: str = Field(..., description="Type of shadow force")
    description: str = Field(..., description="Force description")
    beneficiaries: List[str] = Field(default_factory=list, description="Who benefits from this force")
    next_changes: List[str] = Field(default_factory=list, description="What changes next")
    likely_trajectory: str = Field(..., description="Likely trajectory")
    evidence_sources: List[str] = Field(default_factory=list, description="Sources of evidence")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in this force")
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class DetrimentalScoring(BaseModel):
    """Scoring potential harm of interpretations."""
    target_id: str = Field(..., description="Target being scored")
    interpretations: List[Dict[str, Any]] = Field(..., description="Interpretations to score")
    harm_scores: Dict[str, float] = Field(default_factory=dict, description="Harm score for each interpretation")
    recommended_interpretation: Optional[str] = Field(None, description="Recommended interpretation")
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    mitigation_suggestions: List[str] = Field(default_factory=list, description="Suggestions to mitigate harm")
    scored_at: datetime = Field(default_factory=datetime.utcnow)


class ShadowTrackingEngine:
    """Advanced intelligence layer for shadow tracking and intent vector analysis."""

    def __init__(self):
        self.intent_analyses: Dict[str, IntentVectorAnalysis] = {}
        self.shadow_forces: Dict[str, ShadowForce] = {}
        self.detrimental_scores: Dict[str, DetrimentalScoring] = {}
        self.pattern_recognition_engine = self._initialize_pattern_engine()

    def _initialize_pattern_engine(self) -> Dict[str, Any]:
        """Initialize the pattern recognition engine for shadow tracking."""
        return {
            "beneficiary_patterns": {
                "resource_acquisition": ["resource", "acquire", "gain", "obtain", "control"],
                "power_consolidation": ["power", "control", "influence", "dominate", "authority"],
                "information_advantage": ["information", "knowledge", "intelligence", "data", "secrets"],
                "position_improvement": ["status", "position", "rank", "standing", "advantage"],
                "relationship_building": ["alliance", "partnership", "connection", "network", "relationship"]
            },
            "trajectory_indicators": {
                "escalation": ["increase", "grow", "expand", "intensify", "accelerate"],
                "de_escalation": ["decrease", "reduce", "diminish", "slow", "stabilize"],
                "transformation": ["change", "transform", "evolve", "shift", "transition"],
                "termination": ["end", "stop", "conclude", "finish", "complete"],
                "continuation": ["continue", "persist", "maintain", "sustain", "prolong"]
            },
            "change_predictors": {
                "resource_pressure": ["scarce", "limited", "constrained", "depleted", "insufficient"],
                "external_threats": ["threat", "danger", "risk", "vulnerability", "exposure"],
                "internal_conflict": ["conflict", "disagreement", "tension", "division", "discord"],
                "opportunity_emergence": ["opportunity", "chance", "opening", "possibility", "potential"],
                "environmental_shift": ["change", "shift", "evolution", "transformation", "adaptation"]
            }
        }

    def analyze_intent_vector(self, vector: IntentVector) -> IntentVectorAnalysis:
        """Perform deep analysis of an intent vector with shadow tracking."""

        # Track shadow forces behind this intent
        shadow_forces = self._track_shadow_forces(vector)

        # Infer hidden intent
        hidden_intent = self._infer_hidden_intent(vector, shadow_forces)

        # Calculate evidence strength
        evidence_strength = self._calculate_evidence_strength(vector, shadow_forces)

        # Predict trajectory
        trajectory_prediction = self._predict_trajectory(vector, shadow_forces)

        # Assess risks
        risk_assessment = self._assess_trajectory_risks(vector, trajectory_prediction)

        analysis = IntentVectorAnalysis(
            vector_id=f"analysis_{vector.id}_{datetime.utcnow().isoformat()}",
            base_vector=vector,
            shadow_forces=shadow_forces,
            hidden_intent=hidden_intent,
            evidence_strength=evidence_strength,
            trajectory_prediction=trajectory_prediction,
            risk_assessment=risk_assessment
        )

        self.intent_analyses[analysis.vector_id] = analysis
        return analysis

    def _track_shadow_forces(self, vector: IntentVector) -> List[Dict[str, Any]]:
        """Track unseen forces behind visible intent motion."""

        shadow_forces = []

        # Analyze direction for beneficiary patterns
        direction_lower = vector.direction.lower()

        for force_type, patterns in self.pattern_recognition_engine["beneficiary_patterns"].items():
            matches = sum(1 for pattern in patterns if pattern in direction_lower)
            if matches >= 2:  # At least 2 matching patterns
                beneficiaries = self._infer_beneficiaries(force_type, vector)

                shadow_force = ShadowForce(
                    force_id=f"shadow_{force_type}_{datetime.utcnow().isoformat()}",
                    force_type=force_type,
                    description=f"Unseen {force_type.replace('_', ' ')} force driving intent",
                    beneficiaries=beneficiaries,
                    next_changes=self._predict_next_changes(force_type),
                    likely_trajectory=self._infer_trajectory(force_type),
                    evidence_sources=[vector.id],
                    confidence_score=min(1.0, matches * 0.3 + 0.4)
                )

                self.shadow_forces[shadow_force.force_id] = shadow_force
                shadow_forces.append(shadow_force.dict())

        # If no specific forces detected, look for general patterns
        if not shadow_forces:
            general_force = self._detect_general_shadow_force(vector)
            if general_force:
                shadow_forces.append(general_force)

        return shadow_forces

    def _infer_beneficiaries(self, force_type: str, vector: IntentVector) -> List[str]:
        """Infer who benefits from this shadow force."""

        # Simplified inference based on force type and vector context
        beneficiaries = []

        if force_type == "resource_acquisition":
            beneficiaries.extend(["system_efficiency", "resource_optimization"])
        elif force_type == "power_consolidation":
            beneficiaries.extend(["system_control", "decision_authority"])
        elif force_type == "information_advantage":
            beneficiaries.extend(["learning_capability", "prediction_accuracy"])
        elif force_type == "position_improvement":
            beneficiaries.extend(["system_stability", "goal_achievement"])
        elif force_type == "relationship_building":
            beneficiaries.extend(["collaboration", "system_coherence"])

        # Add vector-specific beneficiaries
        if "user" in vector.direction.lower():
            beneficiaries.append("user_satisfaction")
        if "system" in vector.direction.lower():
            beneficiaries.append("system_performance")

        return list(set(beneficiaries))  # Remove duplicates

    def _predict_next_changes(self, force_type: str) -> List[str]:
        """Predict what changes will happen next based on force type."""

        predictions = {
            "resource_acquisition": [
                "Resource allocation optimization",
                "Efficiency improvements",
                "Capacity expansion"
            ],
            "power_consolidation": [
                "Decision centralization",
                "Authority restructuring",
                "Control mechanism enhancement"
            ],
            "information_advantage": [
                "Knowledge base expansion",
                "Prediction accuracy improvement",
                "Learning capability enhancement"
            ],
            "position_improvement": [
                "Status elevation",
                "Capability enhancement",
                "Position strengthening"
            ],
            "relationship_building": [
                "Network expansion",
                "Collaboration increase",
                "Interdependence growth"
            ]
        }

        return predictions.get(force_type, ["Unknown changes predicted"])

    def _infer_trajectory(self, force_type: str) -> str:
        """Infer the likely trajectory of this shadow force."""

        trajectories = {
            "resource_acquisition": "Exponential growth followed by optimization plateau",
            "power_consolidation": "Centralization followed by distribution balancing",
            "information_advantage": "Continuous expansion with diminishing returns",
            "position_improvement": "Steady improvement with occasional setbacks",
            "relationship_building": "Network growth with increasing complexity"
        }

        return trajectories.get(force_type, "Trajectory unclear")

    def _detect_general_shadow_force(self, vector: IntentVector) -> Optional[Dict[str, Any]]:
        """Detect general shadow forces when specific patterns don't match."""

        # Check for momentum-based forces
        if vector.momentum > 0.7:
            return {
                "force_id": f"general_momentum_{datetime.utcnow().isoformat()}",
                "force_type": "momentum_driven",
                "description": "Strong momentum driving intent forward",
                "beneficiaries": ["goal_achievement", "system_momentum"],
                "next_changes": ["Continued acceleration", "Resource commitment"],
                "likely_trajectory": "Sustained forward motion",
                "evidence_sources": [vector.id],
                "confidence_score": vector.momentum,
                "detected_at": datetime.utcnow().isoformat()
            }

        # Check for low confidence forces
        if vector.magnitude < 0.3:
            return {
                "force_id": f"general_uncertainty_{datetime.utcnow().isoformat()}",
                "force_type": "uncertainty_driven",
                "description": "Uncertainty creating cautious intent",
                "beneficiaries": ["risk_mitigation", "system_stability"],
                "next_changes": ["Increased validation", "Conservative actions"],
                "likely_trajectory": "Cautious advancement with frequent reassessment",
                "evidence_sources": [vector.id],
                "confidence_score": 1.0 - vector.magnitude,
                "detected_at": datetime.utcnow().isoformat()
            }

        return None

    def _infer_hidden_intent(self, vector: IntentVector, shadow_forces: List[Dict[str, Any]]) -> str:
        """Infer the hidden intent behind the visible vector."""

        if not shadow_forces:
            return f"Transparent intent: {vector.direction}"

        # Combine shadow forces to infer hidden intent
        force_types = [force["force_type"] for force in shadow_forces]
        force_descriptions = [force["description"] for force in shadow_forces]

        # Create a composite hidden intent
        if "resource_acquisition" in force_types and "power_consolidation" in force_types:
            hidden_intent = "Strategic positioning for long-term advantage through resource and power accumulation"
        elif len(set(force_types)) == 1:
            # Single dominant force
            force_type = force_types[0]
            hidden_intent = f"Focused {force_type.replace('_', ' ')} strategy"
        else:
            # Multiple forces
            hidden_intent = f"Multi-dimensional strategy combining {', '.join(force_types[:2])}"

        return f"Hidden intent detected: {hidden_intent}"

    def _calculate_evidence_strength(self, vector: IntentVector, shadow_forces: List[Dict[str, Any]]) -> float:
        """Calculate strength of evidence for hidden intent."""

        if not shadow_forces:
            return 0.0  # No shadow forces = transparent intent

        # Base strength from vector magnitude
        base_strength = vector.magnitude

        # Add strength from shadow force confidence
        shadow_strength = sum(force["confidence_score"] for force in shadow_forces) / len(shadow_forces)

        # Factor in number of shadow forces (more forces = stronger evidence)
        force_multiplier = min(1.0, len(shadow_forces) * 0.2 + 0.8)

        # Combine factors
        evidence_strength = (base_strength * 0.4 + shadow_strength * 0.4 + force_multiplier * 0.2)

        return min(1.0, evidence_strength)

    def _predict_trajectory(self, vector: IntentVector, shadow_forces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict the trajectory of this intent vector."""

        predictions = []

        # Base trajectory from current vector
        base_prediction = {
            "timeframe": "immediate",
            "description": f"Continue current direction: {vector.direction}",
            "confidence": vector.magnitude,
            "factors": ["current_momentum", "base_direction"]
        }
        predictions.append(base_prediction)

        # Shadow force influenced predictions
        for force in shadow_forces:
            force_prediction = {
                "timeframe": "short_term",
                "description": f"Shadow force '{force['force_type']}' will drive: {force['likely_trajectory']}",
                "confidence": force["confidence_score"],
                "factors": ["shadow_force_influence", force["force_type"]]
            }
            predictions.append(force_prediction)

        # Long-term synthesis
        if shadow_forces:
            dominant_force = max(shadow_forces, key=lambda f: f["confidence_score"])
            long_term = {
                "timeframe": "long_term",
                "description": f"Converge toward {dominant_force['likely_trajectory']} with {', '.join(dominant_force['next_changes'][:2])}",
                "confidence": dominant_force["confidence_score"] * 0.8,  # Slightly lower for long-term
                "factors": ["long_term_synthesis", "dominant_shadow_force"]
            }
            predictions.append(long_term)

        return predictions

    def _assess_trajectory_risks(self, vector: IntentVector, trajectory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess risks associated with the predicted trajectory."""

        risks = {
            "high_risk_factors": [],
            "medium_risk_factors": [],
            "low_risk_factors": [],
            "overall_risk_score": 0.0,
            "mitigation_suggestions": []
        }

        # Analyze trajectory for risk patterns
        for prediction in trajectory:
            description = prediction["description"].lower()
            confidence = prediction["confidence"]

            # High risk patterns
            if any(word in description for word in ["accelerate", "expand", "dominate", "control"]):
                if confidence > 0.8:
                    risks["high_risk_factors"].append(f"High-confidence {prediction['timeframe']} acceleration")
                    risks["mitigation_suggestions"].append("Implement feedback controls for rapid changes")

            # Medium risk patterns
            if any(word in description for word in ["transform", "change", "shift"]):
                risks["medium_risk_factors"].append(f"{prediction['timeframe'].capitalize()} transformation risk")
                risks["mitigation_suggestions"].append("Monitor transformation progress closely")

            # Low risk patterns
            if any(word in description for word in ["stabilize", "maintain", "sustain"]):
                risks["low_risk_factors"].append(f"Low-risk {prediction['timeframe']} stability")

        # Calculate overall risk score
        risk_weights = {"high": 0.8, "medium": 0.5, "low": 0.2}
        total_weighted_risk = 0
        total_factors = 0

        for level, factors in risks.items():
            if level.endswith("_risk_factors"):
                weight = risk_weights.get(level.split("_")[0], 0.5)
                total_weighted_risk += weight * len(factors)
                total_factors += len(factors)

        risks["overall_risk_score"] = total_weighted_risk / max(1, total_factors)

        return risks

    def score_detrimental_impact(self, target_id: str, interpretations: List[Dict[str, Any]]) -> DetrimentalScoring:
        """Score potential harm of different interpretations."""

        harm_scores = {}

        for interpretation in interpretations:
            harm_score = self._calculate_detrimental_score(interpretation)
            interp_id = interpretation.get("id", f"interp_{interpretations.index(interpretation)}")
            harm_scores[interp_id] = harm_score

        # Find recommended interpretation (lowest harm score)
        if harm_scores:
            recommended_id = min(harm_scores.keys(), key=lambda k: harm_scores[k])
            recommended_score = harm_scores[recommended_id]
        else:
            recommended_id = None
            recommended_score = 0.0

        # Identify risk factors
        risk_factors = []
        for interp_id, score in harm_scores.items():
            if score > 0.7:
                risk_factors.append(f"High harm potential in {interp_id}")
            elif score > 0.4:
                risk_factors.append(f"Moderate harm potential in {interp_id}")

        # Generate mitigation suggestions
        mitigation_suggestions = []
        if any(score > 0.7 for score in harm_scores.values()):
            mitigation_suggestions.append("Avoid interpretations with high harm scores")
        if len(harm_scores) > 1:
            mitigation_suggestions.append("Consider ensemble approach combining low-harm interpretations")
        if recommended_id:
            mitigation_suggestions.append(f"Prioritize interpretation {recommended_id} with lowest harm score")

        scoring = DetrimentalScoring(
            target_id=target_id,
            interpretations=interpretations,
            harm_scores=harm_scores,
            recommended_interpretation=recommended_id,
            risk_factors=risk_factors,
            mitigation_suggestions=mitigation_suggestions
        )

        self.detrimental_scores[target_id] = scoring
        return scoring

    def _calculate_detrimental_score(self, interpretation: Dict[str, Any]) -> float:
        """Calculate detrimental impact score for an interpretation."""

        harm_score = 0.0
        content = interpretation.get("content", "").lower()

        # High harm indicators
        high_harm_words = ["harm", "damage", "destroy", "break", "fail", "collapse", "danger", "threat", "risk"]
        high_harm_count = sum(1 for word in high_harm_words if word in content)
        harm_score += min(0.5, high_harm_count * 0.15)  # Max 0.5 from high harm

        # Medium harm indicators
        medium_harm_words = ["problem", "issue", "concern", "difficulty", "challenge", "complexity"]
        medium_harm_count = sum(1 for word in medium_harm_words if word in content)
        harm_score += min(0.3, medium_harm_count * 0.08)  # Max 0.3 from medium harm

        # Confidence factor (high confidence in harmful interpretation = more harm)
        confidence = interpretation.get("confidence", 0.5)
        harm_score *= (0.5 + confidence * 0.5)  # Scale by confidence

        # Context factor (some domains are inherently riskier)
        domains = interpretation.get("domains", [])
        risk_domains = ["security", "safety", "finance", "health"]
        domain_risk = len(set(domains) & set(risk_domains)) * 0.1
        harm_score += domain_risk

        return min(1.0, harm_score)

    def resolve_signal_fracture(self, fracture_id: str) -> Dict[str, Any]:
        """Resolve signal fracture using detrimental scoring."""

        if fracture_id not in signal_field.fracture_map:
            return {"error": "Fracture not found"}

        fracture = signal_field.fracture_map[fracture_id]

        # Convert fracture narratives to interpretations
        interpretations = []
        for i, narrative in enumerate(fracture.narratives):
            interpretations.append({
                "id": f"narrative_{i}",
                "content": narrative,
                "confidence": fracture.evidence_strength.get(narrative, 0.5),
                "domains": ["fracture_resolution"]
            })

        # Score detrimental impact
        detrimental_scoring = self.score_detrimental_impact(fracture_id, interpretations)

        # Validate resolution through watchtower network
        validation_result = watchtower_network.validate_interpretation({
            "content": f"Resolve fracture by selecting: {detrimental_scoring.recommended_interpretation}",
            "domains": ["fracture_resolution", "conflict_resolution"]
        })

        resolution = {
            "fracture_id": fracture_id,
            "original_fracture_score": fracture.fracture_score,
            "detrimental_scoring": detrimental_scoring.dict(),
            "watchtower_validation": validation_result,
            "resolution_confidence": validation_result.get("consensus_score", 0.0),
            "recommended_action": detrimental_scoring.recommended_interpretation,
            "resolved_at": datetime.utcnow().isoformat()
        }

        # Update fracture with resolution
        fracture.resolution_attempts.append(resolution)
        fracture.last_updated = datetime.utcnow()

        # Reduce fracture score if resolution is validated
        if validation_result.get("validated", False):
            fracture.fracture_score = max(0.0, fracture.fracture_score * 0.7)  # Reduce by 30%

        return resolution

    def get_shadow_tracking_status(self) -> Dict[str, Any]:
        """Get comprehensive shadow tracking status."""

        active_forces = [f for f in self.shadow_forces.values()
                        if (datetime.utcnow() - f.detected_at).days < 7]

        recent_analyses = [a for a in self.intent_analyses.values()
                          if (datetime.utcnow() - a.analyzed_at).days < 1]

        status = {
            "total_shadow_forces": len(self.shadow_forces),
            "active_shadow_forces": len(active_forces),
            "intent_analyses_performed": len(self.intent_analyses),
            "recent_analyses": len(recent_analyses),
            "detrimental_scores": len(self.detrimental_scores),
            "shadow_detection_health": self._calculate_shadow_health(),
            "top_shadow_force_types": self._get_top_force_types()
        }

        return status

    def _calculate_shadow_health(self) -> float:
        """Calculate overall shadow tracking health."""

        health_factors = []

        # Force detection rate
        recent_forces = len([f for f in self.shadow_forces.values()
                           if (datetime.utcnow() - f.detected_at).days < 1])
        health_factors.append(min(1.0, recent_forces * 0.2))  # 5 forces = full health

        # Analysis frequency
        recent_analyses = len([a for a in self.intent_analyses.values()
                             if (datetime.utcnow() - a.analyzed_at).days < 1])
        health_factors.append(min(1.0, recent_analyses * 0.1))  # 10 analyses = full health

        # Detrimental scoring activity
        health_factors.append(min(1.0, len(self.detrimental_scores) * 0.05))  # 20 scores = full health

        return sum(health_factors) / len(health_factors) if health_factors else 0.0

    def _get_top_force_types(self) -> Dict[str, int]:
        """Get top shadow force types by frequency."""

        force_counts = {}
        for force in self.shadow_forces.values():
            force_type = force.force_type
            force_counts[force_type] = force_counts.get(force_type, 0) + 1

        # Return top 5
        return dict(sorted(force_counts.items(), key=lambda x: x[1], reverse=True)[:5])


# Global shadow tracking engine instance
shadow_tracking_engine = ShadowTrackingEngine()
