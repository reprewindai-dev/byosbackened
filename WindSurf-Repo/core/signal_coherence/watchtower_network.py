"""Watchtower Network - Consistency and distributed validation module."""
from typing import Dict, Any, List, Optional, Tuple, Set
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import random
from core.signal_coherence.signal_field import signal_field, InteractionLog, FracturePoint


class ValidationNode(BaseModel):
    """A validation perspective in the watchtower network."""
    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(..., description="Type of validation node")
    vantage_point: str = Field(..., description="Validation perspective or domain")
    confidence_weight: float = Field(1.0, ge=0.0, le=2.0, description="Node confidence weight")
    validation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Validation history")
    specialization: List[str] = Field(default_factory=list, description="Areas of specialization")
    last_active: datetime = Field(default_factory=datetime.utcnow)
    consensus_score: float = Field(0.0, ge=0.0, le=1.0, description="Historical consensus accuracy")


class CrossCheckProtocol(BaseModel):
    """Protocol for requiring consensus before action."""
    protocol_id: str = Field(..., description="Protocol identifier")
    required_consensus: float = Field(0.7, ge=0.5, le=1.0, description="Required consensus threshold")
    participating_nodes: List[str] = Field(..., description="Nodes participating in protocol")
    validation_criteria: List[str] = Field(..., description="Validation criteria")
    consensus_reached: bool = Field(False, description="Whether consensus was reached")
    consensus_score: float = Field(0.0, ge=0.0, le=1.0, description="Achieved consensus score")
    dissenting_nodes: List[str] = Field(default_factory=list, description="Nodes that dissented")
    execution_blocked: bool = Field(False, description="Whether execution was blocked")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SmokeSignalCompression(BaseModel):
    """Summaries passed forward through time."""
    signal_id: str = Field(..., description="Compressed signal identifier")
    original_signals: List[str] = Field(..., description="Original signal IDs")
    compression_ratio: float = Field(..., description="Compression ratio achieved")
    summary_content: str = Field(..., description="Compressed summary")
    temporal_scope: str = Field(..., description="Time period covered")
    key_insights: List[str] = Field(default_factory=list, description="Key insights extracted")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Summary confidence")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConsistencyScoring(BaseModel):
    """Rates coherence across interpretations."""
    target_id: str = Field(..., description="Target being scored for consistency")
    interpretations: List[Dict[str, Any]] = Field(..., description="Different interpretations")
    consistency_score: float = Field(0.0, ge=0.0, le=1.0, description="Overall consistency score")
    coherence_matrix: Dict[str, float] = Field(default_factory=dict, description="Pairwise coherence scores")
    dominant_interpretation: Optional[str] = Field(None, description="Most consistent interpretation")
    fracture_indicators: List[str] = Field(default_factory=list, description="Consistency fractures")
    recommended_resolution: Optional[str] = Field(None, description="Suggested resolution approach")
    scored_at: datetime = Field(default_factory=datetime.utcnow)


class WatchtowerNetwork:
    """Watchtower Network module for consistency and distributed validation."""

    def __init__(self):
        self.validation_nodes: Dict[str, ValidationNode] = {}
        self.cross_check_protocols: Dict[str, CrossCheckProtocol] = {}
        self.smoke_signals: Dict[str, SmokeSignalCompression] = {}
        self.consistency_scores: Dict[str, ConsistencyScoring] = {}
        self.network_health_score = 1.0

        # Initialize default validation nodes
        self._initialize_validation_nodes()

    def _initialize_validation_nodes(self) -> None:
        """Initialize the distributed validation network."""

        default_nodes = [
            {
                "node_id": "temporal_validator",
                "node_type": "temporal",
                "vantage_point": "time-series analysis",
                "specialization": ["temporal_patterns", "trend_analysis", "prediction_validation"]
            },
            {
                "node_id": "logical_validator",
                "node_type": "logical",
                "vantage_point": "logical consistency",
                "specialization": ["logical_consistency", "argument_validation", "reasoning_coherence"]
            },
            {
                "node_id": "ethical_validator",
                "node_type": "ethical",
                "vantage_point": "ethical alignment",
                "specialization": ["ethical_alignment", "value_consistency", "moral_reasoning"]
            },
            {
                "node_id": "performance_validator",
                "node_type": "performance",
                "vantage_point": "system performance",
                "specialization": ["performance_metrics", "efficiency_analysis", "resource_optimization"]
            },
            {
                "node_id": "security_validator",
                "node_type": "security",
                "vantage_point": "security analysis",
                "specialization": ["security_threats", "vulnerability_assessment", "risk_analysis"]
            },
            {
                "node_id": "user_experience_validator",
                "node_type": "ux",
                "vantage_point": "user experience",
                "specialization": ["usability_analysis", "user_satisfaction", "interface_consistency"]
            }
        ]

        for node_config in default_nodes:
            node = ValidationNode(**node_config)
            self.validation_nodes[node.node_id] = node

    def validate_interpretation(self, interpretation: Dict[str, Any], context: str = "general") -> Dict[str, Any]:
        """Validate an interpretation through the watchtower network."""

        # Select relevant validation nodes
        relevant_nodes = self._select_relevant_nodes(context)

        if not relevant_nodes:
            return {
                "validated": False,
                "consensus_score": 0.0,
                "reason": "No relevant validation nodes available",
                "node_validations": []
            }

        # Execute cross-check protocol
        protocol = self._execute_cross_check_protocol(interpretation, relevant_nodes)

        # Calculate consensus
        consensus_result = self._calculate_consensus(protocol)

        # Update node consensus scores
        self._update_node_consensus_scores(protocol, consensus_result["consensus_reached"])

        return {
            "validated": consensus_result["consensus_reached"],
            "consensus_score": consensus_result["consensus_score"],
            "protocol_id": protocol.protocol_id,
            "participating_nodes": len(relevant_nodes),
            "node_validations": consensus_result["node_validations"],
            "dissenting_nodes": protocol.dissenting_nodes,
            "recommended_action": self._generate_validation_recommendation(consensus_result)
        }

    def _select_relevant_nodes(self, context: str) -> List[ValidationNode]:
        """Select validation nodes relevant to the context."""

        relevant_nodes = []

        # Context-based selection
        if context == "security":
            relevant_nodes.extend([n for n in self.validation_nodes.values() if "security" in n.specialization])
        elif context == "performance":
            relevant_nodes.extend([n for n in self.validation_nodes.values() if "performance" in n.specialization])
        elif context == "ethical":
            relevant_nodes.extend([n for n in self.validation_nodes.values() if "ethical" in n.specialization])
        elif context == "temporal":
            relevant_nodes.extend([n for n in self.validation_nodes.values() if "temporal" in n.specialization])
        else:
            # General context - use diverse nodes
            relevant_nodes = list(self.validation_nodes.values())[:4]  # Use first 4 nodes

        # Ensure we have at least 2 nodes for consensus
        if len(relevant_nodes) < 2:
            relevant_nodes = list(self.validation_nodes.values())[:3]

        return relevant_nodes

    def _execute_cross_check_protocol(
        self,
        interpretation: Dict[str, Any],
        nodes: List[ValidationNode]
    ) -> CrossCheckProtocol:
        """Execute the cross-check validation protocol."""

        protocol_id = f"protocol_{datetime.utcnow().isoformat()}_{hash(str(interpretation)) % 1000}"

        protocol = CrossCheckProtocol(
            protocol_id=protocol_id,
            participating_nodes=[n.node_id for n in nodes],
            validation_criteria=[
                "logical_consistency",
                "contextual_relevance",
                "evidence_support",
                "potential_risks"
            ]
        )

        # Each node validates the interpretation
        node_validations = []
        for node in nodes:
            validation = self._node_validate_interpretation(node, interpretation)
            node_validations.append(validation)

            # Store validation in node's history
            node.validation_history.append({
                "protocol_id": protocol_id,
                "interpretation": interpretation,
                "validation": validation,
                "timestamp": datetime.utcnow()
            })

            # Keep only recent history
            if len(node.validation_history) > 50:
                node.validation_history = node.validation_history[-50:]

            node.last_active = datetime.utcnow()

        # Identify dissenting nodes
        avg_confidence = sum(v["confidence"] for v in node_validations) / len(node_validations)
        dissenting_threshold = avg_confidence * 0.7

        for i, validation in enumerate(node_validations):
            if validation["confidence"] < dissenting_threshold:
                protocol.dissenting_nodes.append(nodes[i].node_id)

        self.cross_check_protocols[protocol_id] = protocol
        return protocol

    def _node_validate_interpretation(self, node: ValidationNode, interpretation: Dict[str, Any]) -> Dict[str, Any]:
        """Individual node validation of an interpretation."""

        # Base validation logic (simplified - in real implementation would be more sophisticated)
        validation_score = 0.0
        issues = []

        # Check logical consistency
        logical_score = self._assess_logical_consistency(node, interpretation)
        validation_score += logical_score * 0.4

        # Check contextual relevance
        context_score = self._assess_contextual_relevance(node, interpretation)
        validation_score += context_score * 0.3

        # Check evidence support
        evidence_score = self._assess_evidence_support(node, interpretation)
        validation_score += evidence_score * 0.2

        # Check potential risks
        risk_score = self._assess_potential_risks(node, interpretation)
        validation_score += risk_score * 0.1

        # Add some randomness based on node confidence weight
        validation_score *= node.confidence_weight
        validation_score = min(1.0, max(0.0, validation_score))

        # Node specialization bonus
        specialization_match = len(set(node.specialization) & set(interpretation.get("domains", [])))
        if specialization_match > 0:
            validation_score += 0.1 * specialization_match
            validation_score = min(1.0, validation_score)

        confidence = validation_score

        return {
            "node_id": node.node_id,
            "confidence": confidence,
            "logical_score": logical_score,
            "context_score": context_score,
            "evidence_score": evidence_score,
            "risk_score": risk_score,
            "issues": issues,
            "specialization_bonus": specialization_match > 0
        }

    def _assess_logical_consistency(self, node: ValidationNode, interpretation: Dict[str, Any]) -> float:
        """Assess logical consistency of interpretation."""
        # Simplified logic - check for contradictions
        content = interpretation.get("content", "")
        contradictions = ["but", "however", "although", "despite", "contrary"]

        contradiction_count = sum(1 for word in contradictions if word.lower() in content.lower())
        consistency_score = max(0.0, 1.0 - (contradiction_count * 0.2))

        return consistency_score

    def _assess_contextual_relevance(self, node: ValidationNode, interpretation: Dict[str, Any]) -> float:
        """Assess contextual relevance."""
        # Simplified - check if interpretation matches node specialization
        domains = interpretation.get("domains", [])
        specialization_match = len(set(node.specialization) & set(domains))

        if specialization_match > 0:
            return 0.9
        else:
            return 0.6  # Neutral relevance

    def _assess_evidence_support(self, node: ValidationNode, interpretation: Dict[str, Any]) -> float:
        """Assess evidence support."""
        # Simplified - check for evidence indicators
        content = interpretation.get("content", "").lower()
        evidence_indicators = ["data", "study", "research", "evidence", "proven", "demonstrated"]

        evidence_count = sum(1 for indicator in evidence_indicators if indicator in content)
        evidence_score = min(1.0, evidence_count * 0.3 + 0.4)  # Base 0.4, +0.3 per indicator

        return evidence_score

    def _assess_potential_risks(self, node: ValidationNode, interpretation: Dict[str, Any]) -> float:
        """Assess potential risks (returns risk score - lower is better)."""
        # Simplified - check for risk indicators
        content = interpretation.get("content", "").lower()
        risk_indicators = ["risk", "danger", "threat", "vulnerability", "unstable", "problematic"]

        risk_count = sum(1 for indicator in risk_indicators if indicator in content)
        risk_score = min(1.0, risk_count * 0.25)  # Risk score from 0-1

        # Return inverse (1.0 - risk_score) so higher is better
        return 1.0 - risk_score

    def _calculate_consensus(self, protocol: CrossCheckProtocol) -> Dict[str, Any]:
        """Calculate consensus from protocol results."""

        # Get validation results from protocol
        node_validations = []
        for node_id in protocol.participating_nodes:
            if node_id in self.validation_nodes:
                node = self.validation_nodes[node_id]
                # Get the most recent validation for this protocol
                recent_validations = [v for v in node.validation_history if v["protocol_id"] == protocol.protocol_id]
                if recent_validations:
                    node_validations.append(recent_validations[-1]["validation"])

        if not node_validations:
            return {
                "consensus_reached": False,
                "consensus_score": 0.0,
                "node_validations": []
            }

        # Calculate consensus score
        confidences = [v["confidence"] for v in node_validations]
        consensus_score = sum(confidences) / len(confidences)

        # Check if consensus threshold is met
        consensus_reached = consensus_score >= protocol.required_consensus

        protocol.consensus_reached = consensus_reached
        protocol.consensus_score = consensus_score

        return {
            "consensus_reached": consensus_reached,
            "consensus_score": consensus_score,
            "node_validations": node_validations
        }

    def _update_node_consensus_scores(self, protocol: CrossCheckProtocol, consensus_reached: bool) -> None:
        """Update node consensus scores based on protocol results."""

        for node_id in protocol.participating_nodes:
            if node_id in self.validation_nodes:
                node = self.validation_nodes[node_id]

                # Calculate node's contribution to consensus
                node_validation = None
                for validation_history in node.validation_history:
                    if validation_history["protocol_id"] == protocol.protocol_id:
                        node_validation = validation_history["validation"]
                        break

                if node_validation:
                    node_confidence = node_validation["confidence"]
                    # Update consensus score (moving average)
                    alpha = 0.1  # Learning rate
                    if consensus_reached:
                        # Good consensus - increase score
                        node.consensus_score = (1 - alpha) * node.consensus_score + alpha * node_confidence
                    else:
                        # Poor consensus - decrease score slightly
                        node.consensus_score = (1 - alpha) * node.consensus_score + alpha * (node_confidence * 0.8)

                    node.consensus_score = max(0.0, min(1.0, node.consensus_score))

    def _generate_validation_recommendation(self, consensus_result: Dict[str, Any]) -> str:
        """Generate recommendation based on validation results."""

        if consensus_result["consensus_reached"]:
            if consensus_result["consensus_score"] > 0.9:
                return "Strong consensus - proceed with high confidence"
            else:
                return "Consensus reached - proceed with validation"
        else:
            dissenting_count = len(consensus_result.get("dissenting_nodes", []))
            if dissenting_count > 2:
                return "Significant dissent - review interpretation before proceeding"
            else:
                return "Consensus not reached - consider additional validation nodes"

    def compress_smoke_signals(self, time_period: str = "daily") -> SmokeSignalCompression:
        """Compress recent signals into smoke signals for temporal continuity."""

        # Get signals from the specified time period
        cutoff_time = datetime.utcnow()
        if time_period == "daily":
            cutoff_time -= timedelta(days=1)
        elif time_period == "weekly":
            cutoff_time -= timedelta(weeks=1)
        elif time_period == "monthly":
            cutoff_time -= timedelta(days=30)

        # Get recent signals (simplified - in real implementation would get from acoustic listener)
        recent_signals = signal_field.interaction_history[-50:]  # Last 50 interactions as proxy

        if not recent_signals:
            # Create empty compression
            return SmokeSignalCompression(
                signal_id=f"smoke_{datetime.utcnow().isoformat()}",
                original_signals=[],
                compression_ratio=1.0,
                summary_content="No signals to compress",
                temporal_scope=time_period,
                key_insights=["Period was quiet"],
                confidence_score=1.0
            )

        # Extract key insights
        key_insights = self._extract_key_insights(recent_signals)

        # Create summary
        success_rate = sum(1 for s in recent_signals if s.success) / len(recent_signals)
        avg_fracture = sum(s.fracture_score for s in recent_signals) / len(recent_signals)

        summary_content = (
            f"Period: {time_period}. Signals: {len(recent_signals)}. "
            f"Success rate: {success_rate:.1%}. Avg fracture: {avg_fracture:.2f}. "
            f"Key insights: {'; '.join(key_insights[:3])}"
        )

        compression = SmokeSignalCompression(
            signal_id=f"smoke_{datetime.utcnow().isoformat()}",
            original_signals=[s.run_id for s in recent_signals],
            compression_ratio=len(recent_signals) / max(1, len(summary_content.split())),
            summary_content=summary_content,
            temporal_scope=time_period,
            key_insights=key_insights,
            confidence_score=success_rate  # Use success rate as confidence proxy
        )

        self.smoke_signals[compression.signal_id] = compression
        return compression

    def _extract_key_insights(self, signals: List[InteractionLog]) -> List[str]:
        """Extract key insights from signals."""

        insights = []

        # Success trend
        success_rate = sum(1 for s in signals if s.success) / len(signals)
        if success_rate > 0.8:
            insights.append("High success rate indicates good system health")
        elif success_rate < 0.6:
            insights.append("Low success rate suggests potential issues")

        # Fracture analysis
        avg_fracture = sum(s.fracture_score for s in signals) / len(signals)
        if avg_fracture > 0.3:
            insights.append("Elevated fracture scores indicate coherence issues")
        elif avg_fracture < 0.1:
            insights.append("Low fracture scores indicate good coherence")

        # Action pattern
        action_types = {}
        for signal in signals:
            action = signal.action_taken
            action_types[action] = action_types.get(action, 0) + 1

        if action_types:
            dominant_action = max(action_types.keys(), key=lambda k: action_types[k])
            insights.append(f"Dominant action pattern: {dominant_action}")

        return insights if insights else ["Signals processed successfully"]

    def score_consistency(self, target_id: str, interpretations: List[Dict[str, Any]]) -> ConsistencyScoring:
        """Score consistency across multiple interpretations."""

        if len(interpretations) < 2:
            return ConsistencyScoring(
                target_id=target_id,
                interpretations=interpretations,
                consistency_score=1.0,  # Single interpretation is perfectly consistent
                dominant_interpretation=interpretations[0].get("id") if interpretations else None
            )

        # Calculate pairwise coherence
        coherence_matrix = {}
        total_coherence = 0
        pair_count = 0

        for i, interp1 in enumerate(interpretations):
            for j, interp2 in enumerate(interpretations):
                if i < j:  # Only calculate each pair once
                    pair_key = f"{interp1.get('id', i)}_{interp2.get('id', j)}"
                    coherence = self._calculate_interpretation_coherence(interp1, interp2)
                    coherence_matrix[pair_key] = coherence
                    total_coherence += coherence
                    pair_count += 1

        # Overall consistency score
        consistency_score = total_coherence / max(1, pair_count)

        # Find dominant interpretation (highest average coherence with others)
        interp_scores = {}
        for i, interp in enumerate(interpretations):
            interp_id = interp.get("id", f"interp_{i}")
            interp_coherences = [
                coherence_matrix.get(f"{interp_id}_{other.get('id', j)}", 0.0)
                for j, other in enumerate(interpretations) if i != j
            ]
            if interp_coherences:
                interp_scores[interp_id] = sum(interp_coherences) / len(interp_coherences)

        dominant_interpretation = max(interp_scores.keys(), key=lambda k: interp_scores[k]) if interp_scores else None

        # Identify fracture indicators
        fracture_indicators = []
        for pair_key, coherence in coherence_matrix.items():
            if coherence < 0.5:
                fracture_indicators.append(f"Low coherence between {pair_key}")

        # Recommended resolution
        if consistency_score < 0.6:
            recommended_resolution = "Review conflicting interpretations and resolve differences"
        elif consistency_score < 0.8:
            recommended_resolution = "Minor coherence issues - monitor and address as needed"
        else:
            recommended_resolution = "High consistency - interpretations align well"

        scoring = ConsistencyScoring(
            target_id=target_id,
            interpretations=interpretations,
            consistency_score=consistency_score,
            coherence_matrix=coherence_matrix,
            dominant_interpretation=dominant_interpretation,
            fracture_indicators=fracture_indicators,
            recommended_resolution=recommended_resolution
        )

        self.consistency_scores[target_id] = scoring
        return scoring

    def _calculate_interpretation_coherence(self, interp1: Dict[str, Any], interp2: Dict[str, Any]) -> float:
        """Calculate coherence between two interpretations."""

        coherence_score = 0.0
        factors = 0

        # Content similarity (simplified)
        content1 = interp1.get("content", "").lower()
        content2 = interp2.get("content", "").lower()

        if content1 and content2:
            # Simple word overlap
            words1 = set(content1.split())
            words2 = set(content2.split())
            overlap = len(words1 & words2) / max(1, len(words1 | words2))
            coherence_score += overlap * 0.4
            factors += 1

        # Confidence alignment
        conf1 = interp1.get("confidence", 0.5)
        conf2 = interp2.get("confidence", 0.5)
        conf_alignment = 1.0 - abs(conf1 - conf2)  # Closer confidences = higher alignment
        coherence_score += conf_alignment * 0.3
        factors += 1

        # Domain alignment
        domains1 = set(interp1.get("domains", []))
        domains2 = set(interp2.get("domains", []))
        if domains1 or domains2:
            domain_overlap = len(domains1 & domains2) / max(1, len(domains1 | domains2))
            coherence_score += domain_overlap * 0.3
            factors += 1

        return coherence_score / max(1, factors)

    def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive watchtower network status."""

        active_nodes = sum(1 for n in self.validation_nodes.values()
                          if (datetime.utcnow() - n.last_active).days < 7)

        recent_protocols = [p for p in self.cross_check_protocols.values()
                           if (datetime.utcnow() - p.created_at).days < 1]

        consensus_rate = 0.0
        if recent_protocols:
            consensus_count = sum(1 for p in recent_protocols if p.consensus_reached)
            consensus_rate = consensus_count / len(recent_protocols)

        status = {
            "total_nodes": len(self.validation_nodes),
            "active_nodes": active_nodes,
            "network_health_score": self.network_health_score,
            "recent_protocols": len(recent_protocols),
            "consensus_rate": consensus_rate,
            "smoke_signals": len(self.smoke_signals),
            "consistency_scores": len(self.consistency_scores),
            "validation_distribution": self._get_validation_distribution()
        }

        return status

    def _get_validation_distribution(self) -> Dict[str, int]:
        """Get distribution of validation activities."""

        distribution = defaultdict(int)

        for node in self.validation_nodes.values():
            for validation in node.validation_history[-10:]:  # Last 10 validations per node
                distribution[node.node_type] += 1

        return dict(distribution)


# Global watchtower network instance
watchtower_network = WatchtowerNetwork()
