"""Watchtower validators - hard block capability for governance pipeline."""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a single validator."""
    passed: bool
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class WatchtowerValidator:
    """Watchtower validators - hard block capability for governance pipeline."""
    
    def __init__(self):
        self.validators = {
            "compliance": self._validate_compliance,
            "budget": self._validate_budget,
            "hallucination": self._validate_hallucination,
            "schema": self._validate_schema,
            "rate_limit": self._validate_rate_limit,
            "content_policy": self._validate_content_policy,
        }
    
    def validate_all(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any],
        risk_scores: Dict[str, float],
        execution_context: Dict[str, Any]
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Run all validators and return overall result.
        
        Returns: (all_passed, blocked_reasons, warnings)
        """
        blocked_reasons = []
        warnings = []
        all_passed = True
        
        for validator_name, validator_func in self.validators.items():
            try:
                result = validator_func(request_data, context, risk_scores, execution_context)
                
                if not result.passed:
                    all_passed = False
                    if result.reason:
                        blocked_reasons.append(f"{validator_name}: {result.reason}")
                    else:
                        blocked_reasons.append(f"{validator_name}: validation failed")
                
                # Add warnings if any
                if result.details and result.details.get("warnings"):
                    warnings.extend(result.details["warnings"])
                    
            except Exception as e:
                logger.error(f"Validator {validator_name} failed: {e}")
                all_passed = False
                blocked_reasons.append(f"{validator_name}: validator error")
        
        return all_passed, blocked_reasons, warnings
    
    def _validate_compliance(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any],
        risk_scores: Dict[str, float],
        execution_context: Dict[str, Any]
    ) -> ValidationResult:
        """Validate compliance requirements."""
        warnings = []
        
        # Check detrimental risk score
        detrimental_score = risk_scores.get("detrimental", 0.0)
        if detrimental_score > 0.8:
            return ValidationResult(
                passed=False,
                reason="High detrimental risk detected",
                details={"detrimental_score": detrimental_score}
            )
        elif detrimental_score > 0.6:
            warnings.append("Moderate detrimental risk detected")
        
        # Check PII exposure
        input_text = request_data.get("input_text", "")
        messages = request_data.get("messages", [])
        
        # Combine text for PII check
        combined_text = input_text + " ".join(
            msg.get("content", "") for msg in messages if isinstance(msg, dict)
        )
        
        # Simple PII patterns
        import re
        pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        }
        
        pii_detected = []
        for pii_type, pattern in pii_patterns.items():
            if re.search(pattern, combined_text, re.IGNORECASE):
                pii_detected.append(pii_type)
        
        if pii_detected:
            # Check workspace policy for PII allowance
            workspace_policy = execution_context.get("workspace_policy", {})
            pii_allowed = workspace_policy.get("allow_pii", False)
            
            if not pii_allowed:
                return ValidationResult(
                    passed=False,
                    reason=f"PII exposure detected: {', '.join(pii_detected)}",
                    details={"pii_types": pii_detected}
                )
            else:
                warnings.append(f"PII detected but allowed by workspace policy: {', '.join(pii_detected)}")
        
        # Check for unsafe content
        unsafe_patterns = [
            r'\b(hate|kill|harm|violence)\b',
            r'\b(illegal|crime|hack|exploit|fraud)\b',
            r'\b(suicide|self.harm|kill.myself)\b',
        ]
        
        for pattern in unsafe_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return ValidationResult(
                    passed=False,
                    reason="Unsafe content detected",
                    details={"pattern": pattern}
                )
        
        return ValidationResult(
            passed=True,
            details={"warnings": warnings}
        )
    
    def _validate_budget(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any],
        risk_scores: Dict[str, float],
        execution_context: Dict[str, Any]
    ) -> ValidationResult:
        """Validate budget and cost constraints."""
        warnings = []
        
        # Get budget information
        budget_remaining = execution_context.get("budget_remaining")
        tier_limits = execution_context.get("tier_limits", {})
        
        # Check estimated cost
        estimated_cost = context.get("estimated_cost", Decimal("0.00"))
        
        if budget_remaining is not None and estimated_cost > budget_remaining:
            return ValidationResult(
                passed=False,
                reason=f"Estimated cost ${estimated_cost} exceeds remaining budget ${budget_remaining}",
                details={"estimated_cost": float(estimated_cost), "budget_remaining": float(budget_remaining)}
            )
        
        # Check tier limits
        max_cost_per_request = tier_limits.get("max_cost_per_request")
        if max_cost_per_request and estimated_cost > Decimal(str(max_cost_per_request)):
            return ValidationResult(
                passed=False,
                reason=f"Estimated cost ${estimated_cost} exceeds tier limit ${max_cost_per_request}",
                details={"estimated_cost": float(estimated_cost), "tier_limit": max_cost_per_request}
            )
        
        # Check daily/monthly limits
        daily_limit = tier_limits.get("daily_cost_limit")
        monthly_limit = tier_limits.get("monthly_cost_limit")
        
        # These would need to be calculated from actual usage
        # For now, just add warnings if approaching limits
        if daily_limit and estimated_cost > Decimal(str(daily_limit)) * Decimal("0.8"):
            warnings.append("Approaching daily cost limit")
        
        if monthly_limit and estimated_cost > Decimal(str(monthly_limit)) * Decimal("0.8"):
            warnings.append("Approaching monthly cost limit")
        
        # Check user tier cost sensitivity
        user_tier = execution_context.get("user_tier", "free")
        if user_tier == "free" and estimated_cost > Decimal("0.01"):
            return ValidationResult(
                passed=False,
                reason=f"Free tier cannot execute operations costing more than $0.01",
                details={"estimated_cost": float(estimated_cost), "tier": user_tier}
            )
        
        return ValidationResult(
            passed=True,
            details={"warnings": warnings}
        )
    
    def _validate_hallucination(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any],
        risk_scores: Dict[str, float],
        execution_context: Dict[str, Any]
    ) -> ValidationResult:
        """Validate for potential hallucination risks (lightweight, deterministic)."""
        warnings = []
        
        # This is a pre-execution check, so we look for patterns that might lead to hallucination
        
        operation_type = request_data.get("operation_type", "")
        input_text = request_data.get("input_text", "")
        
        # Check for ambiguous or vague queries that might lead to hallucination
        if operation_type in ["summarize", "chat"]:
            if input_text:
                # Very short or vague inputs are higher risk
                if len(input_text.strip()) < 10:
                    warnings.append("Very short input may lead to hallucination")
                
                # Check for questions about very specific, obscure facts
                question_patterns = [
                    r'\b(what|who|when|where|why|how)\s+was\s+(the\s+)?\w+\s+born\b',
                    r'\b(what|who|when|where|why|how)\s+did\s+\w+\s+(die|marry|graduate)\b',
                ]
                
                import re
                for pattern in question_patterns:
                    if re.search(pattern, input_text, re.IGNORECASE):
                        warnings.append("Specific factual questions may lead to hallucination")
                        break
        
        # Check for requests that might fabricate information
        fabrication_patterns = [
            r'\b(imagine|create|make.up|invent)\s+(a\s+)?(story|dialogue|conversation)\b',
            r'\b(write|generate)\s+(a\s+)?(fiction|novel|poem)\b',
        ]
        
        import re
        for pattern in fabrication_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                # This is not necessarily bad, just flag it
                warnings.append("Creative generation request detected")
                break
        
        # Check fracture score - high fracture might indicate unclear intent
        fracture_score = risk_scores.get("fracture", 0.0)
        if fracture_score > 0.7:
            return ValidationResult(
                passed=False,
                reason="High fracture score indicates unclear intent, may lead to hallucination",
                details={"fracture_score": fracture_score}
            )
        elif fracture_score > 0.5:
            warnings.append("Moderate fracture score detected")
        
        return ValidationResult(
            passed=True,
            details={"warnings": warnings}
        )
    
    def _validate_schema(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any],
        risk_scores: Dict[str, float],
        execution_context: Dict[str, Any]
    ) -> ValidationResult:
        """Validate request schema and structure."""
        warnings = []
        
        operation_type = request_data.get("operation_type", "")
        
        # Check required fields by operation type
        required_fields = {
            "chat": ["messages", "input_text"],  # At least one required
            "embed": ["input_text"],
            "transcribe": ["audio_url"],
            "caption": ["image_url"],
            "summarize": ["input_text"],
            "sentiment": ["input_text"],
            "ner": ["input_text"],
        }
        
        if operation_type in required_fields:
            required = required_fields[operation_type]
            missing_fields = []
            
            for field in required:
                if field == "messages":
                    if not request_data.get("messages"):
                        missing_fields.append(field)
                elif field == "input_text":
                    if not request_data.get("input_text") or not request_data["input_text"].strip():
                        missing_fields.append(field)
                elif field == "audio_url":
                    if not request_data.get("audio_url"):
                        missing_fields.append(field)
                elif field == "image_url":
                    if not request_data.get("image_url"):
                        missing_fields.append(field)
            
            # For chat, allow either messages OR input_text
            if operation_type == "chat" and ("messages" in missing_fields and "input_text" in missing_fields):
                if request_data.get("messages") or request_data.get("input_text"):
                    missing_fields = []  # At least one is present
            
            if missing_fields:
                return ValidationResult(
                    passed=False,
                    reason=f"Missing required fields: {', '.join(missing_fields)}",
                    details={"missing_fields": missing_fields, "operation_type": operation_type}
                )
        
        # Validate message structure for chat
        if operation_type == "chat" and request_data.get("messages"):
            messages = request_data["messages"]
            if not isinstance(messages, list):
                return ValidationResult(
                    passed=False,
                    reason="Messages must be a list",
                    details={"messages_type": type(messages).__name__}
                )
            
            valid_roles = {"user", "assistant", "system"}
            for i, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    return ValidationResult(
                        passed=False,
                        reason=f"Message {i} must be a dictionary",
                        details={"message_index": i, "message_type": type(msg).__name__}
                    )
                
                if "role" not in msg or "content" not in msg:
                    return ValidationResult(
                        passed=False,
                        reason=f"Message {i} missing required fields (role, content)",
                        details={"message_index": i, "message_keys": list(msg.keys())}
                    )
                
                if msg["role"] not in valid_roles:
                    return ValidationResult(
                        passed=False,
                        reason=f"Message {i} has invalid role: {msg['role']}",
                        details={"message_index": i, "invalid_role": msg["role"], "valid_roles": list(valid_roles)}
                    )
                
                if not isinstance(msg["content"], str) or not msg["content"].strip():
                    return ValidationResult(
                        passed=False,
                        reason=f"Message {i} has empty or invalid content",
                        details={"message_index": i, "content_type": type(msg["content"]).__name__}
                    )
        
        # Validate parameter ranges
        temperature = request_data.get("temperature", 0.7)
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            return ValidationResult(
                passed=False,
                reason="Temperature must be a number between 0 and 2",
                details={"temperature": temperature}
            )
        
        max_tokens = request_data.get("max_tokens", 512)
        if not isinstance(max_tokens, int) or not 1 <= max_tokens <= 4096:
            return ValidationResult(
                passed=False,
                reason="Max tokens must be an integer between 1 and 4096",
                details={"max_tokens": max_tokens}
            )
        
        # Check for extremely long inputs
        input_text = request_data.get("input_text", "")
        if len(input_text) > 50000:  # 50k characters
            return ValidationResult(
                passed=False,
                reason="Input text too long (max 50,000 characters)",
                details={"input_length": len(input_text)}
            )
        elif len(input_text) > 10000:
            warnings.append("Very long input text may affect performance")
        
        return ValidationResult(
            passed=True,
            details={"warnings": warnings}
        )
    
    def _validate_rate_limit(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any],
        risk_scores: Dict[str, float],
        execution_context: Dict[str, Any]
    ) -> ValidationResult:
        """Validate rate limits."""
        warnings = []
        
        user_id = execution_context.get("user_id")
        workspace_id = execution_context.get("workspace_id")
        user_tier = execution_context.get("user_tier", "free")
        
        # Rate limits by tier
        tier_limits = {
            "free": {"requests_per_minute": 10, "requests_per_hour": 100},
            "pro": {"requests_per_minute": 60, "requests_per_hour": 1000},
            "enterprise": {"requests_per_minute": 300, "requests_per_hour": 10000},
        }
        
        limits = tier_limits.get(user_tier, tier_limits["free"])
        
        # This would typically check against a Redis cache or database
        # For now, we'll just implement basic logic
        
        # Check if user is approaching limits (placeholder logic)
        # In production, this would check actual usage counters
        
        # Add warning for high-frequency usage
        if user_tier == "free":
            warnings.append("Free tier has limited rate limits")
        
        return ValidationResult(
            passed=True,
            details={"warnings": warnings, "tier": user_tier, "limits": limits}
        )
    
    def _validate_content_policy(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any],
        risk_scores: Dict[str, float],
        execution_context: Dict[str, Any]
    ) -> ValidationResult:
        """Validate content policies."""
        warnings = []
        
        workspace_policy = execution_context.get("workspace_policy", {})
        
        # Check workspace-specific content restrictions
        restricted_keywords = workspace_policy.get("restricted_keywords", [])
        allowed_domains = workspace_policy.get("allowed_domains", [])
        blocked_domains = workspace_policy.get("blocked_domains", [])
        
        # Combine all text inputs
        input_text = request_data.get("input_text", "")
        messages = request_data.get("messages", [])
        combined_text = input_text.lower()
        
        for msg in messages:
            if isinstance(msg, dict) and msg.get("content"):
                combined_text += " " + str(msg["content"]).lower()
        
        # Check restricted keywords
        for keyword in restricted_keywords:
            if keyword.lower() in combined_text:
                return ValidationResult(
                    passed=False,
                    reason=f"Restricted keyword detected: {keyword}",
                    details={"restricted_keyword": keyword}
                )
        
        # Check domain restrictions (if URLs are present)
        import re
        url_pattern = r'https?://([^\s]+)'
        urls = re.findall(url_pattern, combined_text)
        
        for url in urls:
            domain = url.split('/')[0].lower()
            
            if blocked_domains and domain in blocked_domains:
                return ValidationResult(
                    passed=False,
                    reason=f"Blocked domain detected: {domain}",
                    details={"blocked_domain": domain}
                )
            
            if allowed_domains and domain not in allowed_domains:
                return ValidationResult(
                    passed=False,
                    reason=f"Domain not in allowlist: {domain}",
                    details={"unallowed_domain": domain, "allowed_domains": allowed_domains}
                )
        
        # Check for prompt injection patterns
        injection_patterns = [
            "ignore.previous.instructions",
            "system.prompt",
            "jailbreak",
            "act.as.a.different",
            "pretend.you.are",
        ]
        
        for pattern in injection_patterns:
            if pattern in combined_text:
                return ValidationResult(
                    passed=False,
                    reason=f"Prompt injection attempt detected: {pattern}",
                    details={"injection_pattern": pattern}
                )
        
        return ValidationResult(
            passed=True,
            details={"warnings": warnings}
        )
