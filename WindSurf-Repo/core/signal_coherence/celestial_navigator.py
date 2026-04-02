"""Celestial Navigator - Orientation and long-horizon planning module."""
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import math
from core.signal_coherence.signal_field import signal_field, ReferenceStar, IntentVector
from core.signal_coherence.seked_foundation import seked_foundation


class NorthStarLock(BaseModel):
    """Core mission anchor that maintains stable direction."""
    mission: str = Field(..., description="Core mission statement")
    constraints: List[str] = Field(default_factory=list, description="Fundamental constraints")
    identity_commitments: List[str] = Field(default_factory=list, description="Core identity elements")
    locked_at: datetime = Field(default_factory=datetime.utcnow)
    validation_count: int = Field(0)
    drift_score: float = Field(0.0, ge=0.0, le=1.0, description="How much the system has drifted from north")


class WaypointChain(BaseModel):
    """Converts distant goals into achievable steps."""
    goal_id: str = Field(..., description="Goal identifier")
    waypoints: List[Dict[str, Any]] = Field(default_factory=list, description="Sequential waypoints")
    current_waypoint_index: int = Field(0, description="Current position in chain")
    completion_percentage: float = Field(0.0, ge=0.0, le=1.0)
    estimated_completion: Optional[datetime] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class DriftDetection(BaseModel):
    """Monitors deviation from intended trajectory."""
    component: str = Field(..., description="Component being monitored")
    baseline_value: float = Field(..., description="Expected baseline value")
    current_value: float = Field(..., description="Current measured value")
    drift_threshold: float = Field(0.1, description="Threshold for significant drift")
    drift_score: float = Field(0.0, ge=0.0, le=1.0, description="Severity of drift")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    corrective_actions: List[str] = Field(default_factory=list, description="Suggested corrections")


class TrajectoryProjection(BaseModel):
    """Models future states based on current vectors."""
    scenario_name: str = Field(..., description="Projection scenario identifier")
    current_state: Dict[str, Any] = Field(default_factory=dict)
    projected_states: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    time_horizon_days: int = Field(30, description="Projection time horizon")
    key_assumptions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CelestialNavigator:
    """Celestial Navigator module for orientation and long-horizon planning."""

    def __init__(self):
        self.north_star: Optional[NorthStarLock] = None
        self.waypoint_chains: Dict[str, WaypointChain] = {}
        self.drift_detectors: Dict[str, DriftDetection] = {}
        self.trajectory_projections: Dict[str, TrajectoryProjection] = {}
        self.navigation_history: List[Dict[str, Any]] = []

    def establish_north_star(
        self,
        mission: str,
        constraints: List[str] = None,
        identity_commitments: List[str] = None
    ) -> NorthStarLock:
        """Establish the core north star for navigation."""

        if constraints is None:
            constraints = []
        if identity_commitments is None:
            identity_commitments = []

        north_star = NorthStarLock(
            mission=mission,
            constraints=constraints,
            identity_commitments=identity_commitments
        )

        self.north_star = north_star

        # Create reference stars from north star elements
        self._create_reference_stars_from_north_star(north_star)

        return north_star

    def _create_reference_stars_from_north_star(self, north_star: NorthStarLock) -> None:
        """Create reference stars from north star components."""

        # Mission star
        mission_star = ReferenceStar(
            name="north_star_mission",
            category="mission",
            value=north_star.mission,
            source="celestial_navigator"
        )
        signal_field.add_reference_star(mission_star)

        # Constraint stars
        for i, constraint in enumerate(north_star.constraints):
            constraint_star = ReferenceStar(
                name=f"north_star_constraint_{i}",
                category="constraint",
                value=constraint,
                source="celestial_navigator"
            )
            signal_field.add_reference_star(constraint_star)

        # Identity stars
        for i, identity in enumerate(north_star.identity_commitments):
            identity_star = ReferenceStar(
                name=f"north_star_identity_{i}",
                category="identity",
                value=identity,
                source="celestial_navigator"
            )
            signal_field.add_reference_star(identity_star)

    def create_waypoint_chain(
        self,
        goal: str,
        estimated_completion_days: int = 30
    ) -> WaypointChain:
        """Create a waypoint chain to break down a goal into achievable steps."""

        goal_id = f"goal_{datetime.utcnow().isoformat()}_{hash(goal) % 1000}"

        # Generate waypoints using AI-powered decomposition
        waypoints = self._decompose_goal_into_waypoints(goal, estimated_completion_days)

        chain = WaypointChain(
            goal_id=goal_id,
            waypoints=waypoints,
            estimated_completion=datetime.utcnow() + timedelta(days=estimated_completion_days)
        )

        self.waypoint_chains[goal_id] = chain

        # Create intent vector for this goal
        intent_vector = IntentVector(
            name=f"waypoint_chain_{goal_id}",
            direction=goal,
            magnitude=1.0,  # Full commitment to goal
            source_stars=["north_star_mission"]  # Link to mission
        )
        signal_field.add_intent_vector(intent_vector)

        return chain

    def _decompose_goal_into_waypoints(self, goal: str, total_days: int) -> List[Dict[str, Any]]:
        """Decompose a goal into sequential waypoints."""

        # Simple decomposition logic (in real implementation, this would use AI)
        waypoints = []

        # Break goal into phases
        phases = ["research", "planning", "execution", "validation", "completion"]

        days_per_phase = max(1, total_days // len(phases))

        for i, phase in enumerate(phases):
            waypoint = {
                "id": f"wp_{i}",
                "name": f"{phase.capitalize()} Phase",
                "description": f"Complete {phase} phase of: {goal}",
                "estimated_days": days_per_phase,
                "dependencies": [f"wp_{i-1}"] if i > 0 else [],
                "success_criteria": [f"{phase} phase deliverables completed"],
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            waypoints.append(waypoint)

        return waypoints

    def update_waypoint_progress(self, goal_id: str, waypoint_index: int, status: str) -> None:
        """Update progress on a waypoint chain."""

        if goal_id not in self.waypoint_chains:
            return

        chain = self.waypoint_chains[goal_id]

        # Update waypoint status
        if 0 <= waypoint_index < len(chain.waypoints):
            chain.waypoints[waypoint_index]["status"] = status
            chain.waypoints[waypoint_index]["updated_at"] = datetime.utcnow().isoformat()

        # Update current position
        if status == "completed" and waypoint_index >= chain.current_waypoint_index:
            chain.current_waypoint_index = waypoint_index + 1

        # Calculate completion percentage
        completed_waypoints = sum(1 for wp in chain.waypoints if wp["status"] == "completed")
        chain.completion_percentage = completed_waypoints / len(chain.waypoints)

        chain.last_updated = datetime.utcnow()

    def detect_drift(self) -> List[DriftDetection]:
        """Detect drift from intended trajectories."""

        drift_detections = []

        # Check mission alignment
        if self.north_star:
            mission_alignment = self._calculate_mission_alignment()
            if mission_alignment < 0.8:
                drift_detection = DriftDetection(
                    component="mission_alignment",
                    baseline_value=1.0,
                    current_value=mission_alignment,
                    drift_threshold=0.2,
                    drift_score=1.0 - mission_alignment,
                    corrective_actions=[
                        "Realign actions with core mission",
                        "Validate recent decisions against north star",
                        "Review and update constraints if needed"
                    ]
                )
                drift_detections.append(drift_detection)
                self.drift_detectors["mission_alignment"] = drift_detection

        # Check waypoint chain progress
        for goal_id, chain in self.waypoint_chains.items():
            expected_progress = self._calculate_expected_progress(chain)
            actual_progress = chain.completion_percentage

            if abs(actual_progress - expected_progress) > 0.2:
                drift_detection = DriftDetection(
                    component=f"waypoint_chain_{goal_id}",
                    baseline_value=expected_progress,
                    current_value=actual_progress,
                    drift_threshold=0.2,
                    drift_score=abs(actual_progress - expected_progress),
                    corrective_actions=[
                        "Review waypoint dependencies",
                        "Adjust timeline expectations",
                        "Reassess goal achievability"
                    ]
                )
                drift_detections.append(drift_detection)
                self.drift_detectors[f"waypoint_chain_{goal_id}"] = drift_detection

        # Update north star drift score
        if self.north_star and drift_detections:
            avg_drift = sum(d.drift_score for d in drift_detections) / len(drift_detections)
            self.north_star.drift_score = min(1.0, avg_drift)

        return drift_detections

    def _calculate_mission_alignment(self) -> float:
        """Calculate alignment with core mission."""

        if not self.north_star:
            return 1.0

        # Check recent actions against mission
        recent_actions = signal_field.interaction_history[-20:]
        if not recent_actions:
            return 1.0

        alignment_scores = []
        mission_keywords = self.north_star.mission.lower().split()

        for action in recent_actions:
            action_text = action.action_taken.lower()
            matches = sum(1 for keyword in mission_keywords if keyword in action_text)
            alignment_score = matches / len(mission_keywords) if mission_keywords else 0
            alignment_scores.append(alignment_score)

        return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 1.0

    def _calculate_expected_progress(self, chain: WaypointChain) -> float:
        """Calculate expected progress for a waypoint chain."""

        days_elapsed = (datetime.utcnow() - chain.created_at).days
        total_days = (chain.estimated_completion - chain.created_at).days

        if total_days <= 0:
            return 1.0

        return min(1.0, days_elapsed / total_days)

    def project_trajectory(self, scenario_name: str, time_horizon_days: int = 30) -> TrajectoryProjection:
        """Project future states based on current vectors."""

        current_state = {
            "active_intents": len(signal_field.intent_vectors),
            "reference_stars": len(signal_field.reference_stars),
            "fracture_points": len(signal_field.fracture_map),
            "trust_sources": len(signal_field.trust_weights),
            "structural_integrity": signal_field.get_structural_integrity(),
            "active_collapse_indicators": len(signal_field.active_collapse_indicators)
        }

        projected_states = []
        confidence_score = 0.8  # Base confidence

        for day in range(1, time_horizon_days + 1, 7):  # Weekly projections
            projected_state = self._project_state_at_day(current_state, day)
            projected_states.append({
                "day": day,
                "state": projected_state,
                "confidence": confidence_score * (1 - day/time_horizon_days)  # Confidence decreases over time
            })

        projection = TrajectoryProjection(
            scenario_name=scenario_name,
            current_state=current_state,
            projected_states=projected_states,
            confidence_score=confidence_score,
            time_horizon_days=time_horizon_days,
            key_assumptions=[
                "Current trend continuation",
                "No major external disruptions",
                "Consistent resource availability"
            ]
        )

        self.trajectory_projections[scenario_name] = projection
        return projection

    def _project_state_at_day(self, current_state: Dict[str, Any], days_ahead: int) -> Dict[str, Any]:
        """Project system state at a specific day in the future."""

        # Simple linear projection (in real implementation, this would be more sophisticated)
        growth_rate = 0.02  # 2% daily growth
        decay_rate = 0.01   # 1% daily decay for negative factors

        projected_state = {}
        for key, value in current_state.items():
            if isinstance(value, (int, float)):
                if key in ["active_intents", "reference_stars", "trust_sources"]:
                    # Positive factors grow
                    projected_state[key] = value * (1 + growth_rate) ** days_ahead
                elif key in ["fracture_points", "active_collapse_indicators"]:
                    # Negative factors decay
                    projected_state[key] = value * (1 - decay_rate) ** days_ahead
                elif key in ["structural_integrity"]:
                    # Stability factor - slight improvement over time
                    projected_state[key] = min(1.0, value + (0.01 * days_ahead))
                else:
                    projected_state[key] = value
            else:
                projected_state[key] = value

        return projected_state

    def get_navigation_status(self) -> Dict[str, Any]:
        """Get comprehensive navigation status."""

        drift_detections = self.detect_drift()

        status = {
            "north_star_locked": self.north_star is not None,
            "north_star_drift": self.north_star.drift_score if self.north_star else 0.0,
            "active_waypoint_chains": len(self.waypoint_chains),
            "drift_detections": len(drift_detections),
            "trajectory_projections": len(self.trajectory_projections),
            "overall_navigation_health": self._calculate_navigation_health()
        }

        if self.north_star:
            status["north_star_summary"] = {
                "mission": self.north_star.mission[:100] + "..." if len(self.north_star.mission) > 100 else self.north_star.mission,
                "constraints_count": len(self.north_star.constraints),
                "identity_commitments_count": len(self.north_star.identity_commitments),
                "locked_days_ago": (datetime.utcnow() - self.north_star.locked_at).days
            }

        return status

    def _calculate_navigation_health(self) -> float:
        """Calculate overall navigation health score."""

        health_factors = []

        # North star stability
        if self.north_star:
            health_factors.append(1.0 - self.north_star.drift_score)
        else:
            health_factors.append(0.0)  # No north star = poor health

        # Waypoint chain progress
        if self.waypoint_chains:
            avg_progress = sum(chain.completion_percentage for chain in self.waypoint_chains.values()) / len(self.waypoint_chains)
            health_factors.append(avg_progress)
        else:
            health_factors.append(0.5)  # Neutral if no chains

        # Drift detection severity (inverse)
        drift_severity = sum(d.drift_score for d in self.drift_detectors.values()) / max(1, len(self.drift_detectors))
        health_factors.append(1.0 - drift_severity)

        return sum(health_factors) / len(health_factors) if health_factors else 0.0


# Global celestial navigator instance
celestial_navigator = CelestialNavigator()
