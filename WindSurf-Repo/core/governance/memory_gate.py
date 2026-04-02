"""Community Memory Gate - anti-generic enforcement + moat building."""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import hashlib
import logging
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class MemoryPattern:
    """A community memory pattern."""
    pattern_id: str
    intent_category: str
    business_domain: str
    use_case: str
    pattern_template: str
    success_rate: float
    usage_count: int
    last_updated: datetime
    source_workspaces: List[str]
    quality_score: float
    cost_efficiency: float
    anti_generic_score: float


@dataclass
class MemoryGateResult:
    """Result from memory gate processing."""
    gate_passed: bool
    patterns_retrieved: int
    patterns_applied: int
    anti_generic_score: float
    pattern_sources: List[str]
    moat_strength_delta: float
    gate_reason: Optional[str] = None
    applied_patterns: List[Dict[str, Any]] = None


class CommunityMemoryGate:
    """
    Community Memory Gate - prevents generic outputs and builds data moats.
    
    This component:
    1. Stores successful patterns from across workspaces
    2. Retrieves relevant patterns for current intent
    3. Enforces anti-generic compliance
    4. Builds data moat through pattern aggregation
    """
    
    def __init__(self):
        # In production, this would connect to a database
        # For now, we'll use in-memory storage with some seed patterns
        
        # Initialize indices first
        self.workspace_patterns = {}  # workspace_id -> pattern_ids
        self.intent_index = {}  # intent -> pattern_ids
        self.domain_index = {}  # domain -> pattern_ids
        
        # Then initialize patterns database
        self.patterns_db = self._initialize_seed_patterns()
        
        # Anti-generic thresholds
        self.anti_generic_thresholds = {
            "free": 0.6,      # Free tier needs stronger anti-generic
            "pro": 0.4,       # Pro tier moderate
            "enterprise": 0.2, # Enterprise more lenient
        }
    
    def _initialize_seed_patterns(self) -> Dict[str, MemoryPattern]:
        """Initialize with seed patterns for common use cases."""
        patterns = {}
        
        # Content creation patterns
        patterns["content_summary_001"] = MemoryPattern(
            pattern_id="content_summary_001",
            intent_category="summarize",
            business_domain="content_creation",
            use_case="article_summary",
            pattern_template="Create a concise summary covering: 1) Main topic/theme 2) Key points 3) Conclusion/takeaway",
            success_rate=0.85,
            usage_count=1250,
            last_updated=datetime.utcnow(),
            source_workspaces=["ws_001", "ws_002", "ws_003"],
            quality_score=0.88,
            cost_efficiency=0.92,
            anti_generic_score=0.78
        )
        
        patterns["content_summary_002"] = MemoryPattern(
            pattern_id="content_summary_002",
            intent_category="summarize",
            business_domain="content_creation",
            use_case="executive_summary",
            pattern_template="Executive summary format: • Business context • Key findings • Recommendations • Next steps",
            success_rate=0.91,
            usage_count=890,
            last_updated=datetime.utcnow(),
            source_workspaces=["ws_004", "ws_005"],
            quality_score=0.92,
            cost_efficiency=0.89,
            anti_generic_score=0.82
        )
        
        # Business analysis patterns
        patterns["sentiment_business_001"] = MemoryPattern(
            pattern_id="sentiment_business_001",
            intent_category="sentiment",
            business_domain="business_analysis",
            use_case="customer_feedback",
            pattern_template="Sentiment analysis with: • Overall sentiment (positive/negative/neutral) • Key sentiment drivers • Business impact assessment",
            success_rate=0.87,
            usage_count=2100,
            last_updated=datetime.utcnow(),
            source_workspaces=["ws_006", "ws_007", "ws_008"],
            quality_score=0.85,
            cost_efficiency=0.94,
            anti_generic_score=0.75
        )
        
        # Data processing patterns
        patterns["ner_extraction_001"] = MemoryPattern(
            pattern_id="ner_extraction_001",
            intent_category="ner",
            business_domain="data_processing",
            use_case="document_entities",
            pattern_template="Extract entities in categories: • People (names, roles) • Organizations • Locations • Dates/Events • Products/Services",
            success_rate=0.89,
            usage_count=1567,
            last_updated=datetime.utcnow(),
            source_workspaces=["ws_009", "ws_010"],
            quality_score=0.90,
            cost_efficiency=0.87,
            anti_generic_score=0.80
        )
        
        # Chat interaction patterns
        patterns["chat_assistant_001"] = MemoryPattern(
            pattern_id="chat_assistant_001",
            intent_category="chat",
            business_domain="customer_support",
            use_case="help_desk",
            pattern_template="Professional response: • Acknowledge issue • Provide solution • Offer additional help • Set expectations",
            success_rate=0.86,
            usage_count=3200,
            last_updated=datetime.utcnow(),
            source_workspaces=["ws_011", "ws_012", "ws_013"],
            quality_score=0.88,
            cost_efficiency=0.91,
            anti_generic_score=0.73
        )
        
        # Build indexes
        for pattern_id, pattern in patterns.items():
            self._index_pattern(pattern_id, pattern)
        
        return patterns
    
    def _index_pattern(self, pattern_id: str, pattern: MemoryPattern):
        """Index pattern for fast retrieval."""
        # Index by intent
        if pattern.intent_category not in self.intent_index:
            self.intent_index[pattern.intent_category] = []
        self.intent_index[pattern.intent_category].append(pattern_id)
        
        # Index by domain
        if pattern.business_domain not in self.domain_index:
            self.domain_index[pattern.business_domain] = []
        self.domain_index[pattern.business_domain].append(pattern_id)
    
    def process_request(
        self,
        intent_vector: Dict[str, Any],
        operation_plan: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> MemoryGateResult:
        """
        Process a request through the memory gate.
        
        Returns: MemoryGateResult with gate decision and pattern applications
        """
        intent_category = intent_vector.get("primary_intent", "")
        business_domain = intent_vector.get("business_domain", "")
        use_case = intent_vector.get("use_case", "")
        user_tier = execution_context.get("user_tier", "free")
        workspace_id = execution_context.get("workspace_id", "")
        
        # 1. Retrieve relevant patterns
        candidate_patterns = self._retrieve_patterns(intent_category, business_domain, use_case)
        
        # 2. Score and rank patterns by relevance
        scored_patterns = self._score_patterns(candidate_patterns, intent_vector, operation_plan)
        
        # 3. Select top patterns to apply
        selected_patterns = self._select_patterns(scored_patterns, user_tier)
        
        # 4. Calculate anti-generic score
        anti_generic_score = self._calculate_anti_generic_score(selected_patterns, user_tier)
        
        # 5. Check gate threshold
        threshold = self.anti_generic_thresholds.get(user_tier, 0.6)
        gate_passed = anti_generic_score >= threshold
        
        # 6. Calculate moat strength delta
        moat_delta = self._calculate_moat_delta(selected_patterns, workspace_id)
        
        # 7. Prepare applied patterns data
        applied_patterns_data = []
        for pattern_id, score in selected_patterns:
            if pattern_id in self.patterns_db:
                pattern = self.patterns_db[pattern_id]
                applied_patterns_data.append({
                    "pattern_id": pattern_id,
                    "template": pattern.pattern_template,
                    "relevance_score": score,
                    "success_rate": pattern.success_rate,
                    "source_workspaces": len(pattern.source_workspaces)
                })
        
        gate_reason = None
        if not gate_passed:
            gate_reason = f"Anti-generic score {anti_generic_score:.2f} below threshold {threshold} for {user_tier} tier"
        
        return MemoryGateResult(
            gate_passed=gate_passed,
            patterns_retrieved=len(candidate_patterns),
            patterns_applied=len(selected_patterns),
            anti_generic_score=anti_generic_score,
            pattern_sources=[self.patterns_db[pid].business_domain for pid, _ in selected_patterns if pid in self.patterns_db],
            moat_strength_delta=moat_delta,
            gate_reason=gate_reason,
            applied_patterns=applied_patterns_data
        )
    
    def _retrieve_patterns(self, intent_category: str, business_domain: str, use_case: str) -> List[str]:
        """Retrieve candidate patterns based on intent and domain."""
        candidates = set()
        
        # Exact intent match
        if intent_category in self.intent_index:
            candidates.update(self.intent_index[intent_category])
        
        # Domain match
        if business_domain in self.domain_index:
            candidates.update(self.domain_index[business_domain])
        
        # Fallback: get some patterns if no matches
        if not candidates:
            # Return top patterns by usage
            all_patterns = sorted(
                self.patterns_db.values(),
                key=lambda p: p.usage_count,
                reverse=True
            )
            candidates.update(p.pattern_id for p in all_patterns[:5])
        
        return list(candidates)
    
    def _score_patterns(
        self,
        candidate_patterns: List[str],
        intent_vector: Dict[str, Any],
        operation_plan: Dict[str, Any]
    ) -> List[Tuple[str, float]]:
        """Score patterns by relevance to current request."""
        scored = []
        
        intent_category = intent_vector.get("primary_intent", "")
        business_domain = intent_vector.get("business_domain", "")
        use_case = intent_vector.get("use_case", "")
        complexity_score = intent_vector.get("complexity_score", 0.5)
        
        for pattern_id in candidate_patterns:
            if pattern_id not in self.patterns_db:
                continue
            
            pattern = self.patterns_db[pattern_id]
            relevance_score = 0.0
            
            # Intent matching (40% weight)
            if pattern.intent_category == intent_category:
                relevance_score += 0.4
            elif pattern.intent_category in intent_vector.get("secondary_intent", ""):
                relevance_score += 0.2
            
            # Domain matching (25% weight)
            if pattern.business_domain == business_domain:
                relevance_score += 0.25
            
            # Use case matching (20% weight)
            if pattern.use_case == use_case:
                relevance_score += 0.20
            
            # Quality and success factors (15% weight)
            relevance_score += (pattern.success_rate * 0.1) + (pattern.quality_score * 0.05)
            
            # Anti-generic bonus
            relevance_score += pattern.anti_generic_score * 0.1
            
            scored.append((pattern_id, relevance_score))
        
        # Sort by relevance score
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def _select_patterns(self, scored_patterns: List[Tuple[str, float]], user_tier: str) -> List[Tuple[str, float]]:
        """Select patterns to apply based on tier and scores."""
        # Tier-based pattern limits
        tier_limits = {
            "free": 1,      # Free tier gets 1 pattern
            "pro": 2,       # Pro tier gets 2 patterns
            "enterprise": 3, # Enterprise gets 3 patterns
        }
        
        max_patterns = tier_limits.get(user_tier, 1)
        
        # Filter by minimum relevance score
        min_relevance = 0.3  # Minimum relevance to consider
        filtered = [(pid, score) for pid, score in scored_patterns if score >= min_relevance]
        
        return filtered[:max_patterns]
    
    def _calculate_anti_generic_score(self, selected_patterns: List[Tuple[str, float]], user_tier: str) -> float:
        """Calculate anti-generic compliance score."""
        if not selected_patterns:
            return 0.0  # No patterns = generic
        
        # Base score from pattern relevance and quality
        pattern_scores = []
        for pattern_id, relevance_score in selected_patterns:
            if pattern_id in self.patterns_db:
                pattern = self.patterns_db[pattern_id]
                # Combine relevance, success rate, and anti-generic score
                combined_score = (
                    relevance_score * 0.4 +
                    pattern.success_rate * 0.3 +
                    pattern.anti_generic_score * 0.3
                )
                pattern_scores.append(combined_score)
        
        if not pattern_scores:
            return 0.0
        
        # Average pattern score
        avg_pattern_score = sum(pattern_scores) / len(pattern_scores)
        
        # Apply tier multiplier
        tier_multipliers = {
            "free": 1.0,      # No bonus for free tier
            "pro": 1.1,       # 10% bonus for pro
            "enterprise": 1.2, # 20% bonus for enterprise
        }
        
        multiplier = tier_multipliers.get(user_tier, 1.0)
        final_score = min(avg_pattern_score * multiplier, 1.0)
        
        return final_score
    
    def _calculate_moat_delta(self, selected_patterns: List[Tuple[str, float]], workspace_id: str) -> float:
        """Calculate change in moat strength from pattern usage."""
        if not selected_patterns:
            return 0.0
        
        moat_delta = 0.0
        
        for pattern_id, relevance_score in selected_patterns:
            if pattern_id in self.patterns_db:
                pattern = self.patterns_db[pattern_id]
                
                # Check if this workspace has used this pattern before
                workspace_usage = workspace_id in pattern.source_workspaces
                
                # New pattern usage contributes more to moat
                if not workspace_usage:
                    moat_delta += 0.1 * relevance_score
                else:
                    moat_delta += 0.05 * relevance_score
                
                # High-quality patterns contribute more
                if pattern.quality_score > 0.9:
                    moat_delta += 0.05 * relevance_score
        
        return min(moat_delta, 1.0)
    
    def store_successful_pattern(
        self,
        intent_vector: Dict[str, Any],
        operation_plan: Dict[str, Any],
        execution_context: Dict[str, Any],
        outcome: Dict[str, Any]
    ) -> Optional[str]:
        """
        Store a successful pattern to the community memory.
        
        Returns: pattern_id if stored, None if not stored
        """
        # Only store successful executions
        if not outcome.get("success", False):
            return None
        
        # Check quality thresholds
        quality_score = outcome.get("quality_score", 0.0)
        if quality_score < 0.7:  # Only store high-quality patterns
            return None
        
        # Generate pattern ID
        pattern_content = json.dumps({
            "intent": intent_vector,
            "plan": operation_plan,
            "outcome": outcome
        }, sort_keys=True)
        
        pattern_hash = hashlib.md5(pattern_content.encode()).hexdigest()[:8]
        pattern_id = f"{intent_vector.get('primary_intent', 'unknown')}_{pattern_hash}"
        
        # Check if pattern already exists
        if pattern_id in self.patterns_db:
            # Update existing pattern
            existing = self.patterns_db[pattern_id]
            existing.usage_count += 1
            existing.last_updated = datetime.utcnow()
            
            # Update success rate (moving average)
            existing.success_rate = (existing.success_rate * 0.9) + (1.0 * 0.1)
            
            # Add workspace to sources if not already there
            workspace_id = execution_context.get("workspace_id", "")
            if workspace_id and workspace_id not in existing.source_workspaces:
                existing.source_workspaces.append(workspace_id)
            
            return pattern_id
        
        # Create new pattern
        workspace_id = execution_context.get("workspace_id", "")
        new_pattern = MemoryPattern(
            pattern_id=pattern_id,
            intent_category=intent_vector.get("primary_intent", ""),
            business_domain=intent_vector.get("business_domain", ""),
            use_case=intent_vector.get("use_case", ""),
            pattern_template=self._extract_pattern_template(intent_vector, operation_plan, outcome),
            success_rate=1.0,  # New successful pattern
            usage_count=1,
            last_updated=datetime.utcnow(),
            source_workspaces=[workspace_id] if workspace_id else [],
            quality_score=quality_score,
            cost_efficiency=outcome.get("cost_efficiency", 0.8),
            anti_generic_score=outcome.get("anti_generic_score", 0.7)
        )
        
        # Store pattern
        self.patterns_db[pattern_id] = new_pattern
        self._index_pattern(pattern_id, new_pattern)
        
        logger.info(f"Stored new pattern: {pattern_id}")
        return pattern_id
    
    def _extract_pattern_template(
        self,
        intent_vector: Dict[str, Any],
        operation_plan: Dict[str, Any],
        outcome: Dict[str, Any]
    ) -> str:
        """Extract a reusable pattern template from successful execution."""
        # This is a simplified template extraction
        # In production, this would use more sophisticated NLP
        
        intent_category = intent_vector.get("primary_intent", "")
        business_domain = intent_vector.get("business_domain", "")
        use_case = intent_vector.get("use_case", "")
        
        # Create a template based on the operation type and context
        templates = {
            ("summarize", "content_creation"): "Create structured summary: • Main points • Key details • Conclusion",
            ("sentiment", "business_analysis"): "Analyze sentiment: • Overall tone • Specific indicators • Business impact",
            ("ner", "data_processing"): "Extract entities: • People • Organizations • Locations • Key terms",
            ("chat", "customer_support"): "Professional response: • Acknowledge • Solution • Follow-up",
        }
        
        key = (intent_category, business_domain)
        if key in templates:
            return templates[key]
        
        # Generic template fallback
        return f"Structured {intent_category} for {business_domain}: • Context • Analysis • Output"
    
    def get_pattern_analytics(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get analytics about stored patterns."""
        total_patterns = len(self.patterns_db)
        total_usage = sum(p.usage_count for p in self.patterns_db.values())
        avg_success_rate = sum(p.success_rate for p in self.patterns_db.values()) / total_patterns if total_patterns > 0 else 0
        avg_quality = sum(p.quality_score for p in self.patterns_db.values()) / total_patterns if total_patterns > 0 else 0
        
        # Domain distribution
        domain_counts = {}
        for pattern in self.patterns_db.values():
            domain_counts[pattern.business_domain] = domain_counts.get(pattern.business_domain, 0) + 1
        
        # Top patterns
        top_patterns = sorted(
            self.patterns_db.values(),
            key=lambda p: p.usage_count * p.success_rate,
            reverse=True
        )[:10]
        
        return {
            "total_patterns": total_patterns,
            "total_usage": total_usage,
            "average_success_rate": avg_success_rate,
            "average_quality_score": avg_quality,
            "domain_distribution": domain_counts,
            "top_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "usage_count": p.usage_count,
                    "success_rate": p.success_rate,
                    "business_domain": p.business_domain
                }
                for p in top_patterns
            ]
        }
