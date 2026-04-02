"""Risk assessment and threshold management for governance pipeline."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskThresholds:
    """Configurable risk thresholds for governance."""
    
    # Fracture risk thresholds (contradictions, missing fields)
    fracture_low: float = 0.2
    fracture_medium: float = 0.5
    fracture_high: float = 0.8
    fracture_critical: float = 0.9
    
    # Detrimental risk thresholds (policy violations, unsafe content)
    detrimental_low: float = 0.1
    detrimental_medium: float = 0.3
    detrimental_high: float = 0.6
    detrimental_critical: float = 0.8
    
    # Drift risk thresholds (deviation from norms)
    drift_low: float = 0.3
    drift_medium: float = 0.5
    drift_high: float = 0.7
    drift_critical: float = 0.9
    
    # Coherence thresholds (VCTT τ)
    coherence_excellent: float = 0.9
    coherence_good: float = 0.7
    coherence_acceptable: float = 0.5
    coherence_poor: float = 0.3
    
    # Overall risk thresholds
    overall_risk_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.overall_risk_weights is None:
            self.overall_risk_weights = {
                "fracture": 0.25,
                "detrimental": 0.35,  # Higher weight for safety
                "drift": 0.2,
                "coherence": 0.2,
            }


class RiskAssessment:
    """Risk assessment engine for governance pipeline."""
    
    def __init__(self, thresholds: Optional[RiskThresholds] = None):
        self.thresholds = thresholds or RiskThresholds()
        
        # PII detection patterns
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            "api_key": r'\b[A-Za-z0-9]{32,}\b',
        }
        
        # Unsafe content patterns
        self.unsafe_patterns = {
            "hate_speech": r'\b(hate|kill|harm|violence|discriminat|racist|sexist)\b',
            "illegal_activity": r'\b(illegal|crime|hack|exploit|fraud|scam)\b',
            "self_harm": r'\b(suicide|self.harm|kill.myself|end.my.life)\b',
        }
        
        # Policy violation patterns
        self.policy_violations = {
            "confidential_data": r'\b(confidential|proprietary|trade.secret|internal.only)\b',
            "gdpr_violation": r'\b(personal.data|data.subject|right.to.be.forgotten)\b',
        }
    
    def assess_fracture_risk(self, request_data: Dict[str, Any]) -> float:
        """
        Assess fracture risk - contradictions, missing required fields, malformed input.
        
        Returns: Risk score between 0.0 (no risk) and 1.0 (critical risk)
        """
        risk_score = 0.0
        risk_factors = []
        
        # Check for missing required fields based on operation type
        operation_type = request_data.get("operation_type", "")
        
        if operation_type == "chat":
            if not request_data.get("messages") and not request_data.get("input_text"):
                risk_score += 0.4
                risk_factors.append("missing_chat_input")
                
        elif operation_type == "embed":
            if not request_data.get("input_text"):
                risk_score += 0.4
                risk_factors.append("missing_text_for_embedding")
                
        elif operation_type == "transcribe":
            if not request_data.get("audio_url"):
                risk_score += 0.4
                risk_factors.append("missing_audio_url")
                
        elif operation_type == "caption":
            if not request_data.get("image_url"):
                risk_score += 0.4
                risk_factors.append("missing_image_url")
        
        # Check for contradictory parameters
        temperature = request_data.get("temperature", 0.7)
        max_tokens = request_data.get("max_tokens", 512)
        
        if temperature > 1.5 and max_tokens < 50:
            risk_score += 0.2
            risk_factors.append("contradictory_temp_tokens")
        
        # Check for malformed input
        input_text = request_data.get("input_text", "")
        if input_text:
            # Check for excessive repetition
            words = input_text.split()
            if len(words) > 10:
                unique_ratio = len(set(words.lower())) / len(words)
                if unique_ratio < 0.3:
                    risk_score += 0.3
                    risk_factors.append("excessive_repetition")
            
            # Check for encoding issues
            try:
                input_text.encode('utf-8')
            except UnicodeEncodeError:
                risk_score += 0.5
                risk_factors.append("encoding_issues")
        
        # Check for empty or too short input (except for specific operations)
        if operation_type not in ["caption", "transcribe"] and input_text:
            if len(input_text.strip()) < 3:
                risk_score += 0.2
                risk_factors.append("input_too_short")
        
        return min(risk_score, 1.0)
    
    def assess_detrimental_risk(self, request_data: Dict[str, Any], workspace_policy: Dict[str, Any]) -> float:
        """
        Assess detrimental risk - policy violations, unsafe instructions, reputational risk.
        
        Returns: Risk score between 0.0 (no risk) and 1.0 (critical risk)
        """
        risk_score = 0.0
        risk_factors = []
        
        # Combine all text inputs for analysis
        text_inputs = []
        if request_data.get("input_text"):
            text_inputs.append(request_data["input_text"])
        
        if request_data.get("messages"):
            for msg in request_data["messages"]:
                if isinstance(msg, dict) and msg.get("content"):
                    text_inputs.append(msg["content"])
        
        combined_text = " ".join(text_inputs).lower()
        
        # Check for PII exposure
        pii_detected = False
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, combined_text, re.IGNORECASE):
                risk_score += 0.3
                risk_factors.append(f"pii_{pii_type}")
                pii_detected = True
        
        # Check for unsafe content
        for unsafe_type, pattern in self.unsafe_patterns.items():
            if re.search(pattern, combined_text, re.IGNORECASE):
                risk_score += 0.4
                risk_factors.append(f"unsafe_{unsafe_type}")
        
        # Check for policy violations
        for policy_type, pattern in self.policy_violations.items():
            if re.search(pattern, combined_text, re.IGNORECASE):
                risk_score += 0.3
                risk_factors.append(f"policy_{policy_type}")
        
        # Check against workspace-specific policies
        if workspace_policy:
            restricted_keywords = workspace_policy.get("restricted_keywords", [])
            for keyword in restricted_keywords:
                if keyword.lower() in combined_text:
                    risk_score += 0.2
                    risk_factors.append(f"workspace_restricted_{keyword}")
        
        # Check for prompt injection attempts
        injection_patterns = [
            r"ignore.previous.instructions",
            r"system.prompt",
            r"jailbreak",
            r"act.as.a.different",
            r"pretend.you.are",
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                risk_score += 0.5
                risk_factors.append("prompt_injection_attempt")
        
        # Check for excessive length (potential resource exhaustion)
        total_chars = sum(len(text) for text in text_inputs)
        if total_chars > 50000:  # 50k characters
            risk_score += 0.2
            risk_factors.append("excessive_input_length")
        
        return min(risk_score, 1.0)
    
    def assess_drift_risk(
        self, 
        request_data: Dict[str, Any], 
        prior_runs: List[Dict[str, Any]], 
        user_preferences: Dict[str, Any]
    ) -> float:
        """
        Assess drift risk - deviation from workspace rules or previous "gold standard".
        
        Returns: Risk score between 0.0 (no risk) and 1.0 (critical risk)
        """
        risk_score = 0.0
        risk_factors = []
        
        if not prior_runs:
            # No historical data - slightly elevated risk
            return 0.1
        
        # Analyze deviation from prior successful runs
        operation_type = request_data.get("operation_type", "")
        similar_runs = [run for run in prior_runs if run.get("operation_type") == operation_type]
        
        if not similar_runs:
            # No similar operations - moderate risk
            return 0.2
        
        # Check parameter drift
        current_temp = request_data.get("temperature", 0.7)
        current_tokens = request_data.get("max_tokens", 512)
        
        # Calculate average parameters from prior runs
        avg_temps = [run.get("temperature", 0.7) for run in similar_runs if "temperature" in run]
        avg_tokens = [run.get("max_tokens", 512) for run in similar_runs if "max_tokens" in run]
        
        if avg_temps:
            avg_temp = sum(avg_temps) / len(avg_temps)
            temp_drift = abs(current_temp - avg_temp)
            if temp_drift > 0.5:
                risk_score += 0.2
                risk_factors.append("temperature_drift")
        
        if avg_tokens:
            avg_token = sum(avg_tokens) / len(avg_tokens)
            token_drift = abs(current_tokens - avg_token) / avg_token
            if token_drift > 0.5:  # 50% deviation
                risk_score += 0.2
                risk_factors.append("token_drift")
        
        # Check content type drift
        input_text = request_data.get("input_text", "")
        if input_text:
            # Simple content similarity check
            current_words = set(input_text.lower().split())
            
            content_drift_scores = []
            for run in similar_runs[:10]:  # Check last 10 similar runs
                run_text = run.get("input_text", "")
                if run_text:
                    run_words = set(run_text.lower().split())
                    if current_words and run_words:
                        # Jaccard similarity
                        intersection = len(current_words.intersection(run_words))
                        union = len(current_words.union(run_words))
                        similarity = intersection / union if union > 0 else 0
                        drift = 1 - similarity
                        content_drift_scores.append(drift)
            
            if content_drift_scores:
                avg_drift = sum(content_drift_scores) / len(content_drift_scores)
                if avg_drift > 0.8:  # High content drift
                    risk_score += 0.3
                    risk_factors.append("content_drift")
        
        # Check against user preferences
        if user_preferences:
            preferred_providers = user_preferences.get("preferred_providers", [])
            current_provider = request_data.get("provider_override")
            if current_provider and preferred_providers:
                if current_provider not in preferred_providers:
                    risk_score += 0.1
                    risk_factors.append("provider_preference_drift")
        
        return min(risk_score, 1.0)
    
    def calculate_overall_risk(
        self,
        fracture_score: float,
        detrimental_score: float,
        drift_score: float,
        coherence_score: float,
    ) -> tuple[RiskLevel, List[str]]:
        """
        Calculate overall risk level and identify risk factors.
        
        Returns: (RiskLevel, List of risk factors)
        """
        # Weighted calculation
        weights = self.thresholds.overall_risk_weights
        overall_score = (
            fracture_score * weights["fracture"] +
            detrimental_score * weights["detrimental"] +
            drift_score * weights["drift"] +
            (1 - coherence_score) * weights["coherence"]  # Invert coherence (lower coherence = higher risk)
        )
        
        risk_factors = []
        
        # Determine risk level and factors
        if overall_score >= 0.8:
            risk_level = RiskLevel.CRITICAL
            risk_factors.append("critical_risk_level")
        elif overall_score >= 0.6:
            risk_level = RiskLevel.HIGH
            risk_factors.append("high_risk_level")
        elif overall_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
            risk_factors.append("medium_risk_level")
        else:
            risk_level = RiskLevel.LOW
        
        # Add specific factor indicators
        if fracture_score > self.thresholds.fracture_high:
            risk_factors.append("high_fracture_risk")
        if detrimental_score > self.thresholds.detrimental_high:
            risk_factors.append("high_detrimental_risk")
        if drift_score > self.thresholds.drift_high:
            risk_factors.append("high_drift_risk")
        if coherence_score < self.thresholds.coherence_poor:
            risk_factors.append("poor_coherence")
        
        return risk_level, risk_factors
    
    def get_risk_thresholds_for_tier(self, user_tier: str) -> RiskThresholds:
        """Get risk thresholds adjusted for user tier."""
        base_thresholds = RiskThresholds()
        
        if user_tier == "enterprise":
            # Enterprise users get more lenient thresholds
            base_thresholds.detrimental_critical = 0.9
            base_thresholds.fracture_critical = 0.95
            base_thresholds.coherence_acceptable = 0.4
            
        elif user_tier == "pro":
            # Pro users get moderately lenient thresholds
            base_thresholds.detrimental_critical = 0.85
            base_thresholds.fracture_critical = 0.9
            base_thresholds.coherence_acceptable = 0.45
        
        # Free tier gets strictest thresholds (default)
        
        return base_thresholds
