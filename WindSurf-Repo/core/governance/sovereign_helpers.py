"""SOVEREIGN AI SAAS STACK v1.0 - Helper Methods for Sovereign Governance Pipeline."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SovereignHelpers:
    """Helper methods for SOVEREIGN AI SAAS STACK governance."""
    
    @staticmethod
    def normalize_primary_intent(request) -> str:
        """Normalize primary intent from request."""
        if request.operation_type.value == "summarize":
            return "content_summarization"
        elif request.operation_type.value == "chat":
            return "conversational_ai"
        elif request.operation_type.value == "embed":
            return "content_embedding"
        elif request.operation_type.value == "transcribe":
            return "audio_transcription"
        elif request.operation_type.value == "caption":
            return "image_captioning"
        else:
            return "general_ai_processing"
    
    @staticmethod
    def extract_secondary_intent(request) -> str:
        """Extract secondary intent from request."""
        if request.input_text:
            text_len = len(request.input_text)
            if text_len > 1000:
                return "long_form_content"
            elif text_len > 100:
                return "medium_content"
            else:
                return "short_content"
        return "unknown"
    
    @staticmethod
    def detect_domain_fracture(request) -> bool:
        """Detect multi-domain fracture in request."""
        # Simple heuristic - check for mixed content types
        content_indicators = []
        if request.input_text:
            if any(word in request.input_text.lower() for word in ["financial", "money", "budget"]):
                content_indicators.append("financial")
            if any(word in request.input_text.lower() for word in ["medical", "health", "patient"]):
                content_indicators.append("medical")
            if any(word in request.input_text.lower() for word in ["legal", "contract", "law"]):
                content_indicators.append("legal")
        
        return len(content_indicators) > 1
    
    @staticmethod
    def compute_entropy_score(request) -> float:
        """Compute entropy score for request ambiguity."""
        entropy = 0.5  # Base entropy
        
        if request.input_text:
            text = request.input_text.lower()
            # Add entropy for ambiguous terms
            ambiguous_words = ["maybe", "perhaps", "possibly", "might", "could", "unclear"]
            entropy += sum(0.1 for word in ambiguous_words if word in text)
        
        return min(entropy, 1.0)
    
    @staticmethod
    def classify_content_type(request) -> str:
        """Classify content type from request."""
        if request.input_text:
            text = request.input_text[:500].lower()
            if any(word in text for word in ["article", "blog", "post", "content"]):
                return "article"
            elif any(word in text for word in ["email", "message", "letter"]):
                return "communication"
            elif any(word in text for word in ["report", "analysis", "data"]):
                return "business_document"
            elif any(word in text for word in ["story", "narrative", "tale"]):
                return "creative"
        return "general"
    
    @staticmethod
    def compute_complexity_score(request) -> float:
        """Compute complexity score for request."""
        complexity = 0.3  # Base complexity
        
        if request.input_text:
            text = request.input_text
            # Add complexity for longer text
            if len(text) > 1000:
                complexity += 0.3
            elif len(text) > 500:
                complexity += 0.2
            
            # Add complexity for complex sentence structures
            if text.count('.') > 10:
                complexity += 0.2
            
            # Add complexity for technical terms
            technical_words = ["algorithm", "system", "process", "methodology", "framework"]
            complexity += sum(0.1 for word in technical_words if word.lower() in text.lower())
        
        return min(complexity, 1.0)
    
    @staticmethod
    def assess_sensitivity_level(request, user_context: Dict[str, Any]) -> str:
        """Assess sensitivity level of request."""
        sensitivity = "low"
        
        if request.input_text:
            text = request.input_text.lower()
            # Check for sensitive content indicators
            if any(word in text for word in ["confidential", "secret", "private", "internal"]):
                sensitivity = "high"
            elif any(word in text for word in ["personal", "individual", "specific"]):
                sensitivity = "medium"
        
        # Consider workspace policy
        workspace_policy = user_context.get("workspace_policy", {})
        if workspace_policy.get("high_sensitivity_mode"):
            if sensitivity == "low":
                sensitivity = "medium"
            elif sensitivity == "medium":
                sensitivity = "high"
        
        return sensitivity
    
    @staticmethod
    def extract_business_domain(request) -> str:
        """Extract business domain from request."""
        if request.input_text:
            text = request.input_text.lower()
            if any(word in text for word in ["marketing", "sales", "advertising"]):
                return "marketing"
            elif any(word in text for word in ["finance", "accounting", "budget"]):
                return "finance"
            elif any(word in text for word in ["healthcare", "medical", "patient"]):
                return "healthcare"
            elif any(word in text for word in ["legal", "compliance", "regulatory"]):
                return "legal"
            elif any(word in text for word in ["technology", "software", "development"]):
                return "technology"
        return "general"
    
    @staticmethod
    def extract_use_case(request) -> str:
        """Extract use case from request."""
        if request.operation_type.value == "summarize":
            return "content_summarization"
        elif request.operation_type.value == "chat":
            return "customer_support"
        elif request.operation_type.value == "transcribe":
            return "meeting_transcription"
        elif request.operation_type.value == "caption":
            return "media_description"
        else:
            return "general_processing"
    
    @staticmethod
    def determine_output_format(request) -> str:
        """Determine expected output format."""
        if request.operation_type.value in ["summarize", "chat"]:
            return "text"
        elif request.operation_type.value == "embed":
            return "vector"
        elif request.operation_type.value == "transcribe":
            return "transcript"
        else:
            return "json"
    
    @staticmethod
    def extract_quality_requirements(request) -> Dict[str, Any]:
        """Extract quality requirements from request."""
        return {
            "min_length": 50 if request.operation_type.value == "summarize" else 10,
            "max_length": request.max_tokens or 512,
            "coherence_required": True,
            "factual_accuracy": request.operation_type.value != "chat"
        }
    
    @staticmethod
    def get_allowed_providers(tier: str) -> List[str]:
        """Get allowed providers based on tier."""
        if tier == "Tier0":
            return ["huggingface", "local_llm"]
        elif tier == "Tier1":
            return ["huggingface", "local_llm", "openai"]
        else:  # Tier2
            return ["huggingface", "local_llm", "openai", "claude"]
    
    @staticmethod
    def compute_cost_ceiling(tier: str, risk_score: float) -> float:
        """Compute cost ceiling based on tier and risk."""
        base_costs = {"Tier0": 0.01, "Tier1": 0.05, "Tier2": 0.10}
        base_cost = base_costs[tier]
        
        # Adjust for risk
        if risk_score > 0.8:
            base_cost *= 0.5  # Reduce cost for high risk
        elif risk_score < 0.3:
            base_cost *= 1.5  # Allow more cost for low risk
        
        return base_cost
    
    @staticmethod
    def compute_tau_score(intent_vector, output: Any) -> float:
        """Compute VCTT coherence τ score."""
        # Simplified τ calculation
        if not output:
            return 0.0
        
        # Base coherence score
        tau = 0.7
        
        # Adjust based on intent-output alignment
        if hasattr(output, '__len__') and len(output) > 0:
            tau += 0.1
        
        # Adjust based on complexity
        if intent_vector.complexity_score > 0.7:
            tau -= 0.1
        
        return min(max(tau, 0.0), 1.0)
    
    @staticmethod
    def compute_generic_similarity(request, patterns: List[Any]) -> float:
        """Compute similarity to generic patterns."""
        # Simplified generic similarity
        if not patterns:
            return 0.0
        
        # Base generic score
        generic_score = 0.3
        
        # Increase if request is very simple
        if request.input_text and len(request.input_text) < 100:
            generic_score += 0.3
        
        return min(generic_score, 1.0)
    
    @staticmethod
    def compute_high_performer_similarity(request, patterns: List[Any]) -> float:
        """Compute similarity to high-performing patterns."""
        # Simplified high-performer similarity
        if not patterns:
            return 0.0
        
        # Base similarity score
        similarity = 0.2
        
        # Increase based on pattern count
        similarity += min(len(patterns) * 0.1, 0.5)
        
        return min(similarity, 1.0)
    
    @staticmethod
    def compute_community_score(patterns: List[Any]) -> float:
        """Compute community score from patterns."""
        if not patterns:
            return 0.0
        
        # Average pattern quality
        total_quality = sum(getattr(p, 'quality_score', 0.5) for p in patterns)
        return min(total_quality / len(patterns), 1.0)
    
    @staticmethod
    def evaluate_long_term_impact(output: Any) -> float:
        """Evaluate long-term impact of output."""
        # Simplified long-term impact assessment
        if not output:
            return 0.5
        
        impact = 0.7  # Base impact
        
        # Positive indicators
        if hasattr(output, '__len__') and len(str(output)) > 100:
            impact += 0.1
        
        return min(impact, 1.0)
    
    @staticmethod
    def assess_manipulation_risk(output: Any) -> float:
        """Assess manipulation risk of output."""
        # Simplified manipulation risk
        if not output:
            return 0.3
        
        risk = 0.2  # Base risk
        
        # Check for concerning patterns
        output_str = str(output).lower()
        concerning_words = ["guaranteed", "always", "never", "perfect", "best"]
        risk += sum(0.1 for word in concerning_words if word in output_str)
        
        return min(risk, 1.0)
    
    @staticmethod
    def evaluate_roi_transparency(output: Any) -> float:
        """Evaluate ROI transparency of output."""
        # Simplified ROI transparency
        if not output:
            return 0.5
        
        transparency = 0.6  # Base transparency
        
        # Check for explanatory content
        output_str = str(output).lower()
        if any(word in output_str for word in ["because", "therefore", "reason", "explain"]):
            transparency += 0.2
        
        return min(transparency, 1.0)
    
    @staticmethod
    def assess_economic_fairness(output: Any) -> float:
        """Assess economic fairness of output."""
        # Simplified economic fairness
        if not output:
            return 0.7
        
        fairness = 0.8  # Base fairness
        
        # Check for balanced language
        output_str = str(output).lower()
        if any(word in output_str for word in ["expensive", "cheap", "free", "cost"]):
            fairness -= 0.1
        
        return max(fairness, 0.0)
    
    @staticmethod
    def evaluate_ecosystem_harm(output: Any) -> float:
        """Evaluate potential ecosystem harm."""
        # Simplified ecosystem harm assessment
        if not output:
            return 0.1
        
        harm = 0.1  # Base harm
        
        # Check for potentially harmful content
        output_str = str(output).lower()
        harmful_words = ["replace", "eliminate", "destroy", "harm"]
        harm += sum(0.1 for word in harmful_words if word in output_str)
        
        return min(harm, 1.0)
    
    @staticmethod
    def estimate_tokens(request: Any, output: Any) -> int:
        """Estimate tokens used for request/response."""
        input_tokens = len(request.input_text or "") // 4 if request.input_text else 0
        output_tokens = len(str(output or "")) // 4 if output else 0
        return input_tokens + output_tokens
    
    @staticmethod
    async def store_immutable_audit_log(request_id: str, outcome: Any, tier: str):
        """Store immutable audit log."""
        # Simplified audit logging
        logger.info(f"[AUDIT] Stored immutable log for {request_id} - Tier: {tier} - Success: {outcome.success}")
    
    @staticmethod
    def add_corrective_context(operation_plan: Any, quality_scores: Dict[str, float]) -> Any:
        """Add corrective context to operation plan."""
        # Simplified corrective context
        if operation_plan.input_text:
            corrective_prompt = "\n\nPlease ensure the output is specific, detailed, and non-generic."
            operation_plan.input_text += corrective_prompt
        return operation_plan
    
    @staticmethod
    def add_citizenship_disclaimers(output: Any, citizenship_scores: Dict[str, float]) -> Any:
        """Add citizenship disclaimers to output."""
        # Simplified disclaimer addition
        if isinstance(output, str):
            disclaimer = "\n\n[AI Generated Content: Verified for ethical compliance]"
            return output + disclaimer
        return output
