"""Scoring engines for fracture, detrimental, drift, and VCTT coherence."""

import re
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ScoringContext:
    """Context for scoring calculations."""
    operation_type: str
    input_text: Optional[str]
    messages: Optional[List[Dict[str, str]]]
    workspace_policy: Dict[str, Any]
    prior_runs: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    expected_schema: Optional[Dict[str, Any]] = None


class FractureScore:
    """Fracture scoring - detects contradictions, missing fields, malformed input."""
    
    def __init__(self):
        # Contradiction detection patterns
        self.contradiction_patterns = [
            (r"\b(yes|no)\b.*\b(no|yes)\b", "yes_no_contradiction"),
            (r"\b(always|never)\b.*\b(sometimes|occasionally)\b", "absolute_contradiction"),
            (r"\b(all|none)\b.*\b(some|few|many)\b", "quantifier_contradiction"),
        ]
        
        # Required fields by operation type
        self.required_fields = {
            "chat": ["messages", "input_text"],  # At least one required
            "embed": ["input_text"],
            "transcribe": ["audio_url"],
            "caption": ["image_url"],
            "summarize": ["input_text"],
            "sentiment": ["input_text"],
            "ner": ["input_text"],
        }
    
    def calculate(self, context: ScoringContext) -> float:
        """
        Calculate fracture score (0.0 = no fracture, 1.0 = severe fracture).
        
        Fracture includes:
        - Missing required fields
        - Contradictory statements
        - Malformed input structure
        - Logical inconsistencies
        """
        fracture_score = 0.0
        
        # 1. Missing required fields (40% weight)
        missing_fields_score = self._check_missing_fields(context)
        fracture_score += missing_fields_score * 0.4
        
        # 2. Contradictions (30% weight)
        contradiction_score = self._detect_contradictions(context)
        fracture_score += contradiction_score * 0.3
        
        # 3. Malformed input (20% weight)
        malformed_score = self._check_malformed_input(context)
        fracture_score += malformed_score * 0.2
        
        # 4. Logical inconsistencies (10% weight)
        logic_score = self._check_logical_consistency(context)
        fracture_score += logic_score * 0.1
        
        return min(fracture_score, 1.0)
    
    def _check_missing_fields(self, context: ScoringContext) -> float:
        """Check for missing required fields."""
        operation_type = context.operation_type
        required = self.required_fields.get(operation_type, [])
        
        if not required:
            return 0.0
        
        missing_count = 0
        for field in required:
            if field == "messages":
                if not context.messages:
                    missing_count += 1
            elif field == "input_text":
                if not context.input_text or not context.input_text.strip():
                    missing_count += 1
            elif field == "audio_url":
                # This would be checked in the actual request data
                pass
            elif field == "image_url":
                # This would be checked in the actual request data
                pass
        
        # If at least one required field is present for OR requirements
        if operation_type == "chat" and (context.messages or context.input_text):
            missing_count = max(0, missing_count - 1)
        
        return missing_count / len(required)
    
    def _detect_contradictions(self, context: ScoringContext) -> float:
        """Detect contradictory statements in text."""
        text_content = ""
        
        if context.input_text:
            text_content += context.input_text + " "
        
        if context.messages:
            for msg in context.messages:
                if isinstance(msg, dict) and msg.get("content"):
                    text_content += msg["content"] + " "
        
        contradiction_count = 0
        total_patterns = len(self.contradiction_patterns)
        
        for pattern, pattern_type in self.contradiction_patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                contradiction_count += 1
                logger.debug(f"Contradiction detected: {pattern_type}")
        
        return contradiction_count / total_patterns if total_patterns > 0 else 0.0
    
    def _check_malformed_input(self, context: ScoringContext) -> float:
        """Check for malformed input structure."""
        malformed_score = 0.0
        
        # Check message structure
        if context.messages:
            for i, msg in enumerate(context.messages):
                if not isinstance(msg, dict):
                    malformed_score += 0.2
                    continue
                
                # Check required message fields
                if "role" not in msg or "content" not in msg:
                    malformed_score += 0.1
                
                # Check valid roles
                valid_roles = {"user", "assistant", "system"}
                if msg.get("role") not in valid_roles:
                    malformed_score += 0.1
                
                # Check for empty content
                if not msg.get("content") or not str(msg["content"]).strip():
                    malformed_score += 0.1
        
        # Check text encoding
        if context.input_text:
            try:
                context.input_text.encode('utf-8')
            except UnicodeEncodeError:
                malformed_score += 0.3
        
        # Check for excessive special characters
        if context.input_text:
            special_char_ratio = sum(not c.isalnum() and c != ' ' for c in context.input_text) / len(context.input_text)
            if special_char_ratio > 0.3:
                malformed_score += 0.2
        
        return min(malformed_score, 1.0)
    
    def _check_logical_consistency(self, context: ScoringContext) -> float:
        """Check for logical inconsistencies."""
        logic_score = 0.0
        
        # Check temperature vs max_tokens consistency
        # High temperature with very low max tokens is inconsistent
        if context.operation_type == "chat":
            # These would come from request parameters
            # For now, we'll use reasonable defaults
            temperature = 0.7  # Would come from request
            max_tokens = 512   # Would come from request
            
            if temperature > 1.5 and max_tokens < 50:
                logic_score += 0.3
            elif temperature < 0.1 and max_tokens > 2000:
                logic_score += 0.2
        
        return min(logic_score, 1.0)


class DetrimentalScore:
    """Detrimental scoring - detects policy violations, unsafe instructions, reputational risk."""
    
    def __init__(self):
        # PII detection patterns
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            "api_key": r'\b[A-Za-z0-9]{20,}\b',
            "password": r'\b(password|passwd|pwd)\s*[:=]\s*\S+',
        }
        
        # Unsafe content patterns
        self.unsafe_patterns = {
            "hate_speech": [
                r'\b(hate|kill|harm|violence|discriminat|racist|sexist|homophobic)\b',
                r'\b(superior|inferior)\s+(race|gender|religion|ethnicity)\b',
            ],
            "illegal_activity": [
                r'\b(how\s+to\s+)(hack|exploit|scam|fraud|steal|rob)\b',
                r'\b(illegal|prohibited|forbidden)\s+(activity|behavior)\b',
            ],
            "self_harm": [
                r'\b(suicide|self.harm|kill.myself|end.my.life)\b',
                r'\b(how\s+to\s+)(die|commit|kill)\s+myself\b',
            ],
        }
        
        # Policy violation patterns
        self.policy_patterns = {
            "confidential_data": [
                r'\b(confidential|proprietary|trade.secret|internal.only|secret)\b',
                r'\b(do\s+not\s+share|restricted|classified)\b',
            ],
            "gdpr_violation": [
                r'\b(personal.data|data.subject|right.to.be.forgotten)\b',
                r'\b(process\s+personal\s+information)\b',
            ],
        }
        
        # Prompt injection patterns
        self.injection_patterns = [
            r'ignore.previous.instructions',
            r'system.prompt',
            r'jailbreak',
            r'act.as.a.different',
            r'pretend.you.are',
            r'roleplay.as',
            r'bypass.filter',
            r'override.safety',
        ]
    
    def calculate(self, context: ScoringContext) -> float:
        """
        Calculate detrimental score (0.0 = safe, 1.0 = highly detrimental).
        
        Detrimental includes:
        - PII exposure
        - Unsafe content
        - Policy violations
        - Prompt injection attempts
        - Reputational risk factors
        """
        detrimental_score = 0.0
        
        # 1. PII exposure (25% weight)
        pii_score = self._detect_pii_exposure(context)
        detrimental_score += pii_score * 0.25
        
        # 2. Unsafe content (30% weight)
        unsafe_score = self._detect_unsafe_content(context)
        detrimental_score += unsafe_score * 0.30
        
        # 3. Policy violations (25% weight)
        policy_score = self._detect_policy_violations(context)
        detrimental_score += policy_score * 0.25
        
        # 4. Prompt injection (15% weight)
        injection_score = self._detect_prompt_injection(context)
        detrimental_score += injection_score * 0.15
        
        # 5. Reputational risk (5% weight)
        reputational_score = self._assess_reputational_risk(context)
        detrimental_score += reputational_score * 0.05
        
        return min(detrimental_score, 1.0)
    
    def _detect_pii_exposure(self, context: ScoringContext) -> float:
        """Detect PII exposure in input."""
        text_content = self._get_combined_text(context)
        
        pii_detected = 0
        total_pii_types = len(self.pii_patterns)
        
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, text_content, re.IGNORECASE):
                pii_detected += 1
                logger.debug(f"PII detected: {pii_type}")
        
        return pii_detected / total_pii_types if total_pii_types > 0 else 0.0
    
    def _detect_unsafe_content(self, context: ScoringContext) -> float:
        """Detect unsafe content."""
        text_content = self._get_combined_text(context)
        
        unsafe_detected = 0
        total_unsafe_categories = len(self.unsafe_patterns)
        
        for unsafe_category, patterns in self.unsafe_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_content, re.IGNORECASE):
                    unsafe_detected += 1
                    logger.debug(f"Unsafe content detected: {unsafe_category}")
                    break  # Count each category once
        
        return unsafe_detected / total_unsafe_categories if total_unsafe_categories > 0 else 0.0
    
    def _detect_policy_violations(self, context: ScoringContext) -> float:
        """Detect policy violations."""
        text_content = self._get_combined_text(context)
        
        policy_violations = 0
        total_policy_categories = len(self.policy_patterns)
        
        # Check built-in policy patterns
        for policy_category, patterns in self.policy_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_content, re.IGNORECASE):
                    policy_violations += 1
                    logger.debug(f"Policy violation detected: {policy_category}")
                    break
        
        # Check workspace-specific policies
        if context.workspace_policy:
            restricted_keywords = context.workspace_policy.get("restricted_keywords", [])
            for keyword in restricted_keywords:
                if keyword.lower() in text_content.lower():
                    policy_violations += 1
                    logger.debug(f"Workspace policy violation: {keyword}")
        
        return min(policy_violations / total_policy_categories, 1.0) if total_policy_categories > 0 else 0.0
    
    def _detect_prompt_injection(self, context: ScoringContext) -> float:
        """Detect prompt injection attempts."""
        text_content = self._get_combined_text(context).lower()
        
        injection_count = 0
        total_patterns = len(self.injection_patterns)
        
        for pattern in self.injection_patterns:
            if pattern in text_content:
                injection_count += 1
                logger.debug(f"Prompt injection detected: {pattern}")
        
        return injection_count / total_patterns if total_patterns > 0 else 0.0
    
    def _assess_reputational_risk(self, context: ScoringContext) -> float:
        """Assess reputational risk factors."""
        reputational_score = 0.0
        
        text_content = self._get_combined_text(context).lower()
        
        # Check for potentially brand-damaging content
        brand_risk_keywords = [
            "scam", "fraud", "lawsuit", "legal action", "complaint",
            "terrible", "awful", "worst", "hate", "refund",
        ]
        
        risk_keyword_count = sum(1 for keyword in brand_risk_keywords if keyword in text_content)
        reputational_score += min(risk_keyword_count / len(brand_risk_keywords), 1.0) * 0.5
        
        # Check for competitor mentions (potential risk)
        competitor_patterns = [
            r'\b(better\s+than)\s+\w+',
            r'\b(worse\s+than)\s+\w+',
            r'\b(alternative\s+to)\s+\w+',
        ]
        
        competitor_mentions = sum(1 for pattern in competitor_patterns if re.search(pattern, text_content))
        reputational_score += min(competitor_mentions / len(competitor_patterns), 1.0) * 0.3
        
        # Check for excessive negativity
        negative_words = ["bad", "terrible", "awful", "hate", "worst", "horrible", "disgusting"]
        negative_count = sum(1 for word in negative_words if word in text_content)
        total_words = len(text_content.split())
        
        if total_words > 0:
            negative_ratio = negative_count / total_words
            reputational_score += min(negative_ratio * 10, 1.0) * 0.2  # Scale up for visibility
        
        return min(reputational_score, 1.0)
    
    def _get_combined_text(self, context: ScoringContext) -> str:
        """Combine all text inputs for analysis."""
        text_parts = []
        
        if context.input_text:
            text_parts.append(context.input_text)
        
        if context.messages:
            for msg in context.messages:
                if isinstance(msg, dict) and msg.get("content"):
                    text_parts.append(str(msg["content"]))
        
        return " ".join(text_parts)


class DriftScore:
    """Drift scoring - detects deviation from workspace norms and historical patterns."""
    
    def __init__(self):
        self.parameter_weights = {
            "temperature": 0.3,
            "max_tokens": 0.2,
            "provider": 0.2,
            "content_similarity": 0.3,
        }
    
    def calculate(self, context: ScoringContext) -> float:
        """
        Calculate drift score (0.0 = no drift, 1.0 = high drift).
        
        Drift includes:
        - Parameter drift from historical usage
        - Content drift from prior similar requests
        - Provider preference drift
        - Usage pattern anomalies
        """
        if not context.prior_runs:
            return 0.1  # Low drift for new users
        
        drift_score = 0.0
        
        # 1. Parameter drift (40% weight)
        param_drift = self._calculate_parameter_drift(context)
        drift_score += param_drift * 0.4
        
        # 2. Content drift (35% weight)
        content_drift = self._calculate_content_drift(context)
        drift_score += content_drift * 0.35
        
        # 3. Provider drift (15% weight)
        provider_drift = self._calculate_provider_drift(context)
        drift_score += provider_drift * 0.15
        
        # 4. Usage pattern drift (10% weight)
        pattern_drift = self._calculate_pattern_drift(context)
        drift_score += pattern_drift * 0.1
        
        return min(drift_score, 1.0)
    
    def _calculate_parameter_drift(self, context: ScoringContext) -> float:
        """Calculate parameter drift from historical usage."""
        similar_runs = [run for run in context.prior_runs if run.get("operation_type") == context.operation_type]
        
        if not similar_runs:
            return 0.2  # Moderate drift for new operation type
        
        # These would come from actual request parameters
        current_temp = 0.7  # Would come from request
        current_tokens = 512  # Would come from request
        
        # Calculate historical averages
        temps = [run.get("temperature", 0.7) for run in similar_runs if "temperature" in run]
        tokens = [run.get("max_tokens", 512) for run in similar_runs if "max_tokens" in run]
        
        drift_components = []
        
        if temps:
            avg_temp = sum(temps) / len(temps)
            temp_drift = abs(current_temp - avg_temp) / 2.0  # Normalize by max possible temp range
            drift_components.append(temp_drift)
        
        if tokens:
            avg_tokens = sum(tokens) / len(tokens)
            if avg_tokens > 0:
                token_drift = abs(current_tokens - avg_tokens) / avg_tokens
                drift_components.append(min(token_drift, 1.0))
        
        return sum(drift_components) / len(drift_components) if drift_components else 0.0
    
    def _calculate_content_drift(self, context: ScoringContext) -> float:
        """Calculate content drift from prior similar requests."""
        if not context.input_text:
            return 0.0
        
        similar_runs = [
            run for run in context.prior_runs 
            if run.get("operation_type") == context.operation_type and run.get("input_text")
        ]
        
        if not similar_runs:
            return 0.2  # Moderate drift for new content
        
        current_words = set(context.input_text.lower().split())
        
        if not current_words:
            return 0.0
        
        drift_scores = []
        
        for run in similar_runs[:20]:  # Check last 20 similar runs
            run_text = run.get("input_text", "")
            run_words = set(run_text.lower().split())
            
            if run_words:
                # Jaccard similarity
                intersection = len(current_words.intersection(run_words))
                union = len(current_words.union(run_words))
                similarity = intersection / union if union > 0 else 0
                drift = 1 - similarity
                drift_scores.append(drift)
        
        return sum(drift_scores) / len(drift_scores) if drift_scores else 0.2
    
    def _calculate_provider_drift(self, context: ScoringContext) -> float:
        """Calculate provider preference drift."""
        # This would check actual provider preference from request
        # For now, return low drift
        return 0.1
    
    def _calculate_pattern_drift(self, context: ScoringContext) -> float:
        """Calculate usage pattern drift."""
        # Check frequency of operations, timing patterns, etc.
        # For now, return low drift
        return 0.1


class VCTTCoherenceScore:
    """VCTT coherence scoring (τ) - measures output coherence and quality."""
    
    def __init__(self):
        self.coherence_weights = {
            "format_adherence": 0.25,
            "completeness": 0.25,
            "self_consistency": 0.25,
            "policy_adherence": 0.25,
        }
    
    def calculate(
        self, 
        input_context: ScoringContext, 
        output_text: str,
        expected_schema: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate VCTT coherence score τ (0.0 = incoherent, 1.0 = perfectly coherent).
        
        Coherence includes:
        - Format adherence
        - Completeness
        - Self-consistency
        - Policy adherence
        """
        coherence_score = 0.0
        
        # 1. Format adherence (25% weight)
        format_score = self._check_format_adherence(output_text, expected_schema)
        coherence_score += format_score * 0.25
        
        # 2. Completeness (25% weight)
        completeness_score = self._check_completeness(input_context, output_text)
        coherence_score += completeness_score * 0.25
        
        # 3. Self-consistency (25% weight)
        consistency_score = self._check_self_consistency(output_text)
        coherence_score += consistency_score * 0.25
        
        # 4. Policy adherence (25% weight)
        policy_score = self._check_policy_adherence(output_text, input_context.workspace_policy)
        coherence_score += policy_score * 0.25
        
        return min(coherence_score, 1.0)
    
    def _check_format_adherence(self, output_text: str, expected_schema: Optional[Dict[str, Any]]) -> float:
        """Check if output adheres to expected format."""
        if not expected_schema:
            # Basic format checks when no schema provided
            if not output_text or not output_text.strip():
                return 0.0
            
            # Check for basic structure
            if len(output_text.strip()) < 5:
                return 0.3
            
            return 0.8  # Reasonable default
        
        # If schema provided, check structure
        try:
            # Try to parse as JSON if schema suggests JSON
            if expected_schema.get("type") == "object":
                json.loads(output_text)
                return 1.0
        except json.JSONDecodeError:
            return 0.3
        
        # Basic text format checks
        if output_text.strip():
            return 0.7
        
        return 0.0
    
    def _check_completeness(self, input_context: ScoringContext, output_text: str) -> float:
        """Check if output is complete relative to input."""
        if not output_text or not output_text.strip():
            return 0.0
        
        # Check response length relative to input complexity
        input_length = len(input_context.input_text or "")
        output_length = len(output_text)
        
        if input_length == 0:
            return 0.8 if output_length > 10 else 0.4
        
        # For summarization, expect shorter output
        if input_context.operation_type == "summarize":
            if output_length > 0 and output_length < input_length:
                return 0.9
            else:
                return 0.5
        
        # For other operations, expect reasonable length
        if output_length < 10:
            return 0.3
        elif output_length > input_length * 5:
            return 0.6  # Too long might be irrelevant
        else:
            return 0.9
    
    def _check_self_consistency(self, output_text: str) -> float:
        """Check for self-consistency in output."""
        if not output_text:
            return 0.0
        
        consistency_score = 1.0
        
        # Check for contradictions
        contradiction_patterns = [
            (r"\b(yes|no)\b.*\b(no|yes)\b", 0.3),
            (r"\b(always|never)\b.*\b(sometimes|occasionally)\b", 0.2),
            (r"\b(all|none)\b.*\b(some|few|many)\b", 0.2),
        ]
        
        for pattern, penalty in contradiction_patterns:
            if re.search(pattern, output_text, re.IGNORECASE):
                consistency_score -= penalty
        
        # Check for excessive repetition
        words = output_text.split()
        if len(words) > 10:
            unique_ratio = len(set(words.lower())) / len(words)
            if unique_ratio < 0.5:
                consistency_score -= 0.2
        
        return max(consistency_score, 0.0)
    
    def _check_policy_adherence(self, output_text: str, workspace_policy: Dict[str, Any]) -> float:
        """Check if output adheres to workspace policies."""
        if not output_text:
            return 0.0
        
        policy_score = 1.0
        
        # Check for policy violations in output
        if workspace_policy:
            restricted_keywords = workspace_policy.get("restricted_keywords", [])
            for keyword in restricted_keywords:
                if keyword.lower() in output_text.lower():
                    policy_score -= 0.3
        
        # Check for PII in output (shouldn't be there)
        pii_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # email
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # credit card
        ]
        
        for pattern in pii_patterns:
            if re.search(pattern, output_text):
                policy_score -= 0.4
        
        return max(policy_score, 0.0)
