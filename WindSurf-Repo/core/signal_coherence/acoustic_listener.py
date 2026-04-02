"""Acoustic Listener - Continuous sensing and weak signal detection module."""
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from core.signal_coherence.signal_field import signal_field, InteractionLog, FracturePoint


class PatternMemory(BaseModel):
    """Stores and cross-references historical signal patterns."""
    pattern_id: str = Field(..., description="Unique pattern identifier")
    pattern_type: str = Field(..., description="Type of pattern (temporal, behavioral, etc.)")
    pattern_data: Dict[str, Any] = Field(..., description="Pattern characteristics")
    occurrences: List[datetime] = Field(default_factory=list, description="When pattern occurred")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Pattern confidence")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    related_patterns: List[str] = Field(default_factory=list, description="Related pattern IDs")


class AnomalyDetection(BaseModel):
    """Identifies deviations from expected patterns."""
    anomaly_id: str = Field(..., description="Unique anomaly identifier")
    anomaly_type: str = Field(..., description="Type of anomaly detected")
    severity_score: float = Field(0.0, ge=0.0, le=1.0, description="Anomaly severity")
    description: str = Field(..., description="Anomaly description")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    affected_components: List[str] = Field(default_factory=list, description="Components affected")
    recommended_actions: List[str] = Field(default_factory=list, description="Suggested responses")


class SignalAmplification(BaseModel):
    """Boosts weak but persistent signals."""
    signal_id: str = Field(..., description="Signal identifier")
    original_strength: float = Field(..., description="Original signal strength")
    amplified_strength: float = Field(..., description="Amplified signal strength")
    amplification_factor: float = Field(1.0, description="How much signal was amplified")
    persistence_count: int = Field(0, description="How many times signal persisted")
    first_detected: datetime = Field(default_factory=datetime.utcnow)
    last_amplified: datetime = Field(default_factory=datetime.utcnow)
    pattern_matches: List[str] = Field(default_factory=list, description="Patterns this signal matches")


class NoiseFilter(BaseModel):
    """Separates meaningful patterns from background noise."""
    filter_name: str = Field(..., description="Filter identifier")
    filter_type: str = Field(..., description="Type of filtering applied")
    noise_threshold: float = Field(0.1, description="Threshold for noise classification")
    filtered_signals: int = Field(0, description="Number of signals filtered")
    passed_signals: int = Field(0, description="Number of signals that passed")
    accuracy_score: float = Field(0.0, ge=0.0, le=1.0, description="Filter accuracy")
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class AcousticListener:
    """Acoustic Listener module for continuous sensing and weak signal detection."""

    def __init__(self):
        self.pattern_memory: Dict[str, PatternMemory] = {}
        self.anomaly_buffer: List[AnomalyDetection] = []
        self.signal_amplifications: Dict[str, SignalAmplification] = {}
        self.noise_filters: Dict[str, NoiseFilter] = {}
        self.signal_history: List[Dict[str, Any]] = []
        self.listening_sensitivity = 0.05  # Detect signals as weak as 5%

        # Initialize default noise filters
        self._initialize_noise_filters()

    def _initialize_noise_filters(self) -> None:
        """Initialize default noise filtering mechanisms."""

        filters = [
            {
                "name": "temporal_noise_filter",
                "type": "temporal",
                "threshold": 0.1,
                "description": "Filters out random temporal noise"
            },
            {
                "name": "behavioral_noise_filter",
                "type": "behavioral",
                "threshold": 0.15,
                "description": "Filters out random behavioral variations"
            },
            {
                "name": "intensity_noise_filter",
                "type": "intensity",
                "threshold": 0.08,
                "description": "Filters out low-intensity random signals"
            },
            {
                "name": "frequency_noise_filter",
                "type": "frequency",
                "threshold": 0.12,
                "description": "Filters out signals that don't persist over time"
            }
        ]

        for filter_config in filters:
            noise_filter = NoiseFilter(
                filter_name=filter_config["name"],
                filter_type=filter_config["type"],
                noise_threshold=filter_config["threshold"]
            )
            self.noise_filters[filter_config["name"]] = noise_filter

    def listen_for_signals(self) -> List[Dict[str, Any]]:
        """Continuously listen for and process incoming signals."""

        detected_signals = []

        # Analyze recent interactions for patterns
        recent_interactions = signal_field.interaction_history[-50:]  # Last 50 interactions

        # Detect weak signals
        weak_signals = self._detect_weak_signals(recent_interactions)
        detected_signals.extend(weak_signals)

        # Identify patterns
        patterns = self._identify_patterns(recent_interactions)
        detected_signals.extend(patterns)

        # Detect anomalies
        anomalies = self._detect_anomalies(recent_interactions)
        detected_signals.extend(anomalies)

        # Filter noise
        filtered_signals = self._apply_noise_filters(detected_signals)

        # Amplify persistent weak signals
        amplified_signals = self._amplify_persistent_signals(filtered_signals)

        # Store signal history
        for signal in amplified_signals:
            signal["detected_at"] = datetime.utcnow().isoformat()
            self.signal_history.append(signal)

        # Keep only recent signal history
        if len(self.signal_history) > 1000:
            self.signal_history = self.signal_history[-1000:]

        return amplified_signals

    def _detect_weak_signals(self, interactions: List[InteractionLog]) -> List[Dict[str, Any]]:
        """Detect weak but potentially important signals."""

        weak_signals = []

        if len(interactions) < 3:
            return weak_signals

        # Analyze interaction patterns for weak signals
        success_rates = []
        duration_trends = []
        fracture_trends = []

        for interaction in interactions[-20:]:  # Last 20 interactions
            success_rates.append(1.0 if interaction.success else 0.0)
            duration_trends.append(interaction.duration_ms)
            fracture_trends.append(interaction.fracture_score)

        # Detect gradual changes (weak signals)
        if len(success_rates) >= 5:
            # Check for declining success rate
            recent_success = statistics.mean(success_rates[-3:])
            overall_success = statistics.mean(success_rates)

            if recent_success < overall_success * 0.8 and recent_success < self.listening_sensitivity:
                weak_signals.append({
                    "type": "weak_signal",
                    "signal_type": "performance_decline",
                    "strength": 1.0 - recent_success,
                    "description": f"Gradual decline in success rate from {overall_success:.2f} to {recent_success:.2f}",
                    "components_affected": ["system_performance"],
                    "recommended_actions": ["Investigate recent changes", "Review system health"]
                })

        # Detect increasing fracture scores
        if len(fracture_trends) >= 5:
            recent_fracture = statistics.mean(fracture_trends[-3:])
            overall_fracture = statistics.mean(fracture_trends)

            if recent_fracture > overall_fracture * 1.5 and recent_fracture > 0.3:
                weak_signals.append({
                    "type": "weak_signal",
                    "signal_type": "increasing_fracture",
                    "strength": recent_fracture,
                    "description": f"Increasing fracture score from {overall_fracture:.2f} to {recent_fracture:.2f}",
                    "components_affected": ["system_coherence"],
                    "recommended_actions": ["Address fracture points", "Review consistency"]
                })

        return weak_signals

    def _identify_patterns(self, interactions: List[InteractionLog]) -> List[Dict[str, Any]]:
        """Identify recurring patterns in interactions."""

        patterns = []

        if len(interactions) < 10:
            return patterns

        # Analyze temporal patterns
        hourly_pattern = self._analyze_temporal_pattern(interactions, "hour")
        if hourly_pattern:
            patterns.append(hourly_pattern)

        # Analyze success pattern
        success_pattern = self._analyze_success_pattern(interactions)
        if success_pattern:
            patterns.append(success_pattern)

        # Analyze interaction type patterns
        type_pattern = self._analyze_interaction_type_pattern(interactions)
        if type_pattern:
            patterns.append(type_pattern)

        return patterns

    def _analyze_temporal_pattern(self, interactions: List[InteractionLog], time_unit: str) -> Optional[Dict[str, Any]]:
        """Analyze patterns in interaction timing."""

        if len(interactions) < 5:
            return None

        # Group interactions by time unit
        time_groups = defaultdict(list)

        for interaction in interactions:
            if time_unit == "hour":
                time_key = interaction.timestamp.hour
            elif time_unit == "weekday":
                time_key = interaction.timestamp.weekday()
            else:
                time_key = interaction.timestamp.hour

            time_groups[time_key].append(interaction)

        # Find peak hours/days
        peak_times = sorted(time_groups.keys(), key=lambda k: len(time_groups[k]), reverse=True)

        if peak_times and len(time_groups[peak_times[0]]) > len(interactions) * 0.3:
            peak_time = peak_times[0]
            peak_count = len(time_groups[peak_time])
            total_count = len(interactions)

            return {
                "type": "pattern",
                "pattern_type": f"temporal_{time_unit}",
                "description": f"Peak activity at {time_unit} {peak_time} ({peak_count}/{total_count} interactions)",
                "strength": peak_count / total_count,
                "components_affected": ["system_usage"],
                "pattern_data": {
                    "peak_time": peak_time,
                    "peak_count": peak_count,
                    "total_count": total_count
                }
            }

        return None

    def _analyze_success_pattern(self, interactions: List[InteractionLog]) -> Optional[Dict[str, Any]]:
        """Analyze patterns in success rates."""

        if len(interactions) < 10:
            return None

        success_rate = sum(1 for i in interactions if i.success) / len(interactions)

        # Check for concerning patterns
        recent_interactions = interactions[-10:]
        recent_success_rate = sum(1 for i in recent_interactions if i.success) / len(recent_interactions)

        if recent_success_rate < success_rate * 0.7:
            return {
                "type": "pattern",
                "pattern_type": "success_decline",
                "description": f"Success rate dropped from {success_rate:.2f} to {recent_success_rate:.2f}",
                "strength": success_rate - recent_success_rate,
                "components_affected": ["system_reliability"],
                "pattern_data": {
                    "overall_success_rate": success_rate,
                    "recent_success_rate": recent_success_rate
                }
            }

        return None

    def _analyze_interaction_type_pattern(self, interactions: List[InteractionLog]) -> Optional[Dict[str, Any]]:
        """Analyze patterns in interaction types."""

        type_counts = defaultdict(int)
        for interaction in interactions:
            type_counts[interaction.input_type] += 1

        total_interactions = len(interactions)
        dominant_type = max(type_counts.keys(), key=lambda k: type_counts[k])

        if type_counts[dominant_type] > total_interactions * 0.6:
            return {
                "type": "pattern",
                "pattern_type": "interaction_dominance",
                "description": f"Dominant interaction type: {dominant_type} ({type_counts[dominant_type]}/{total_interactions})",
                "strength": type_counts[dominant_type] / total_interactions,
                "components_affected": ["system_usage"],
                "pattern_data": dict(type_counts)
            }

        return None

    def _detect_anomalies(self, interactions: List[InteractionLog]) -> List[Dict[str, Any]]:
        """Detect anomalous behavior in interactions."""

        anomalies = []

        if len(interactions) < 5:
            return anomalies

        # Statistical analysis
        durations = [i.duration_ms for i in interactions]
        fracture_scores = [i.fracture_score for i in interactions]

        if len(durations) >= 5:
            mean_duration = statistics.mean(durations)
            stdev_duration = statistics.stdev(durations) if len(durations) > 1 else 0

            # Check for anomalous durations
            for i, interaction in enumerate(interactions[-10:]):  # Check last 10
                if stdev_duration > 0:
                    z_score = abs(interaction.duration_ms - mean_duration) / stdev_duration
                    if z_score > 3.0:  # 3 standard deviations
                        anomaly = AnomalyDetection(
                            anomaly_id=f"anomaly_duration_{datetime.utcnow().isoformat()}",
                            anomaly_type="duration_anomaly",
                            severity_score=min(1.0, z_score / 5.0),
                            description=f"Anomalous duration: {interaction.duration_ms}ms (z-score: {z_score:.2f})",
                            affected_components=["performance"],
                            recommended_actions=["Investigate performance issue", "Check system resources"]
                        )
                        self.anomaly_buffer.append(anomaly)
                        anomalies.append({
                            "type": "anomaly",
                            "anomaly_type": "duration_anomaly",
                            "severity": anomaly.severity_score,
                            "description": anomaly.description,
                            "components_affected": anomaly.affected_components,
                            "recommended_actions": anomaly.recommended_actions
                        })

        return anomalies

    def _apply_noise_filters(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply noise filters to separate meaningful signals from noise."""

        filtered_signals = []

        for signal in signals:
            passed_filters = 0
            total_filters = 0

            for filter_name, noise_filter in self.noise_filters.items():
                total_filters += 1

                # Apply filter logic based on type
                if noise_filter.filter_type == "temporal":
                    # Check if signal persists over time
                    if self._passes_temporal_filter(signal, noise_filter):
                        passed_filters += 1
                        noise_filter.passed_signals += 1
                    else:
                        noise_filter.filtered_signals += 1

                elif noise_filter.filter_type == "behavioral":
                    # Check behavioral consistency
                    if self._passes_behavioral_filter(signal, noise_filter):
                        passed_filters += 1
                        noise_filter.passed_signals += 1
                    else:
                        noise_filter.filtered_signals += 1

                elif noise_filter.filter_type == "intensity":
                    # Check signal strength
                    signal_strength = signal.get("strength", 0.0)
                    if signal_strength >= noise_filter.noise_threshold:
                        passed_filters += 1
                        noise_filter.passed_signals += 1
                    else:
                        noise_filter.filtered_signals += 1

                elif noise_filter.filter_type == "frequency":
                    # Check persistence/frequency
                    if self._passes_frequency_filter(signal, noise_filter):
                        passed_filters += 1
                        noise_filter.passed_signals += 1
                    else:
                        noise_filter.filtered_signals += 1

            # Signal passes if it passes majority of filters
            if passed_filters >= total_filters * 0.6:  # 60% threshold
                filtered_signals.append(signal)

        # Update filter accuracy
        for noise_filter in self.noise_filters.values():
            total_processed = noise_filter.filtered_signals + noise_filter.passed_signals
            if total_processed > 0:
                # Accuracy = passed signals that were actually meaningful (simplified)
                noise_filter.accuracy_score = noise_filter.passed_signals / total_processed

        return filtered_signals

    def _passes_temporal_filter(self, signal: Dict[str, Any], noise_filter: NoiseFilter) -> bool:
        """Check if signal passes temporal noise filter."""
        # Simplified: check if signal has been seen recently
        signal_type = signal.get("signal_type", "")
        recent_signals = [s for s in self.signal_history[-20:] if s.get("signal_type") == signal_type]
        return len(recent_signals) >= 2  # Must appear at least twice recently

    def _passes_behavioral_filter(self, signal: Dict[str, Any], noise_filter: NoiseFilter) -> bool:
        """Check if signal passes behavioral noise filter."""
        # Simplified: check if signal is consistent with known patterns
        signal_type = signal.get("signal_type", "")
        matching_patterns = [p for p in self.pattern_memory.values() if signal_type in p.pattern_type]
        return len(matching_patterns) > 0

    def _passes_frequency_filter(self, signal: Dict[str, Any], noise_filter: NoiseFilter) -> bool:
        """Check if signal passes frequency noise filter."""
        # Simplified: check persistence count
        signal_id = signal.get("signal_id", "")
        if signal_id in self.signal_amplifications:
            persistence = self.signal_amplifications[signal_id].persistence_count
            return persistence >= 3  # Must persist at least 3 times
        return False

    def _amplify_persistent_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Amplify weak but persistent signals."""

        amplified_signals = []

        for signal in signals:
            signal_id = signal.get("signal_id", f"signal_{datetime.utcnow().isoformat()}")
            original_strength = signal.get("strength", 0.0)

            # Check if this signal has been seen before
            if signal_id in self.signal_amplifications:
                amplification = self.signal_amplifications[signal_id]
                amplification.persistence_count += 1
                amplification.last_amplified = datetime.utcnow()

                # Amplify based on persistence
                amplification_factor = 1.0 + (amplification.persistence_count * 0.2)
                amplified_strength = min(1.0, original_strength * amplification_factor)

                amplification.amplified_strength = amplified_strength
                amplification.amplification_factor = amplification_factor

                # Mark signal as amplified
                signal["amplified"] = True
                signal["amplification_factor"] = amplification_factor
                signal["persistence_count"] = amplification.persistence_count

            else:
                # New signal - create amplification record
                amplification = SignalAmplification(
                    signal_id=signal_id,
                    original_strength=original_strength,
                    amplified_strength=original_strength,  # No amplification yet
                    amplification_factor=1.0,
                    persistence_count=1
                )
                self.signal_amplifications[signal_id] = amplification

            amplified_signals.append(signal)

        return amplified_signals

    def get_listening_status(self) -> Dict[str, Any]:
        """Get comprehensive acoustic listening status."""

        recent_signals = self.signal_history[-20:] if self.signal_history else []

        status = {
            "active_patterns": len(self.pattern_memory),
            "recent_anomalies": len(self.anomaly_buffer),
            "amplified_signals": len(self.signal_amplifications),
            "active_filters": len(self.noise_filters),
            "total_signals_processed": len(self.signal_history),
            "listening_sensitivity": self.listening_sensitivity,
            "signal_detection_health": self._calculate_detection_health()
        }

        # Recent activity summary
        if recent_signals:
            signal_types = defaultdict(int)
            for signal in recent_signals:
                signal_types[signal.get("type", "unknown")] += 1

            status["recent_activity"] = {
                "total_signals": len(recent_signals),
                "signal_types": dict(signal_types),
                "avg_strength": sum(s.get("strength", 0) for s in recent_signals) / len(recent_signals),
                "amplified_count": sum(1 for s in recent_signals if s.get("amplified", False))
            }

        return status

    def _calculate_detection_health(self) -> float:
        """Calculate overall signal detection health."""

        health_factors = []

        # Pattern recognition health
        if self.pattern_memory:
            avg_confidence = sum(p.confidence_score for p in self.pattern_memory.values()) / len(self.pattern_memory)
            health_factors.append(avg_confidence)
        else:
            health_factors.append(0.3)  # Some baseline health

        # Filter accuracy health
        if self.noise_filters:
            avg_accuracy = sum(f.accuracy_score for f in self.noise_filters.values()) / len(self.noise_filters)
            health_factors.append(avg_accuracy)
        else:
            health_factors.append(0.5)

        # Signal amplification health
        if self.signal_amplifications:
            amplified_count = sum(1 for a in self.signal_amplifications.values() if a.amplification_factor > 1.5)
            amplification_rate = amplified_count / len(self.signal_amplifications)
            health_factors.append(amplification_rate)
        else:
            health_factors.append(0.4)

        return sum(health_factors) / len(health_factors) if health_factors else 0.0


# Global acoustic listener instance
acoustic_listener = AcousticListener()
