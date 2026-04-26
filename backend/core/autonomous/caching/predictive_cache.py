"""Predictive cache - pre-cache likely-needed data."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import AIAuditLog
from core.autonomous.caching.cache_optimizer import get_cache_optimizer
from core.config import get_settings
from core.redis_pool import get_redis
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
cache_optimizer = get_cache_optimizer()


class PredictiveCache:
    """
    Predictive cache - pre-cache likely-needed data.
    
    Learns access patterns and pre-caches data before it's needed.
    Reduces latency by having data ready.
    """

    def __init__(self):
        self.redis_client = get_redis()
        # workspace_id -> {pattern: {next_likely_keys, access_frequency}}
        self.access_patterns: Dict[str, Dict[str, Dict]] = {}

    def predict_and_precache(
        self,
        workspace_id: str,
        operation_type: str,
        current_key: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> List[str]:
        """
        Predict what will be needed next and pre-cache.
        
        Returns list of keys that were pre-cached.
        """
        # Get access patterns for workspace
        if workspace_id not in self.access_patterns:
            self._learn_access_patterns(workspace_id, operation_type, db)
        
        if workspace_id not in self.access_patterns:
            return []
        
        patterns = self.access_patterns[workspace_id]
        
        # Predict next likely keys
        likely_keys = self._predict_next_keys(
            workspace_id=workspace_id,
            operation_type=operation_type,
            current_key=current_key,
            patterns=patterns,
        )
        
        # Pre-cache them
        precached = []
        for key in likely_keys:
            if self._precache_key(key, workspace_id, operation_type):
                precached.append(key)
        
        if precached:
            logger.info(
                f"Pre-cached {len(precached)} keys for workspace {workspace_id}: "
                f"{operation_type}"
            )
        
        return precached

    def _predict_next_keys(
        self,
        workspace_id: str,
        operation_type: str,
        current_key: Optional[str],
        patterns: Dict[str, Dict],
    ) -> List[str]:
        """Predict next likely keys based on patterns."""
        likely_keys = []
        
        # Simple heuristic: if operation_type is "transcribe", pre-cache recent transcripts
        if operation_type == "transcribe":
            # Pre-cache recent transcripts (last 10)
            for i in range(10):
                key = f"transcript:recent:{workspace_id}:{i}"
                likely_keys.append(key)
        
        # Check learned patterns
        pattern_key = f"{operation_type}:*"
        if pattern_key in patterns:
            pattern_data = patterns[pattern_key]
            next_keys = pattern_data.get("next_likely_keys", [])
            likely_keys.extend(next_keys[:5])  # Top 5
        
        return likely_keys

    def _precache_key(
        self,
        key: str,
        workspace_id: str,
        operation_type: str,
    ) -> bool:
        """Pre-cache a key if not already cached."""
        try:
            # Check if already cached
            if self.redis_client.exists(key):
                return False
            
            # Get optimal TTL
            ttl = cache_optimizer.get_optimal_ttl(
                workspace_id=workspace_id,
                cache_key_pattern=f"{operation_type}:*",
            )
            
            # Pre-cache with placeholder (actual data would be loaded from DB)
            # For now, just mark as precached
            self.redis_client.setex(
                f"precache:{key}",
                ttl,
                "precached",
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to pre-cache key {key}: {e}")
            return False

    def _learn_access_patterns(
        self,
        workspace_id: str,
        operation_type: str,
        db: Optional[Session],
    ):
        """Learn access patterns from historical data."""
        if not db:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            # Get last 7 days of access logs
            cutoff = datetime.utcnow() - timedelta(days=7)
            
            logs = db.query(AIAuditLog).filter(
                AIAuditLog.workspace_id == workspace_id,
                AIAuditLog.operation_type == operation_type,
                AIAuditLog.created_at >= cutoff,
            ).order_by(AIAuditLog.created_at).limit(1000).all()
            
            if len(logs) < 10:
                return
            
            # Analyze access patterns
            # For now, simple pattern: sequential access
            pattern_key = f"{operation_type}:*"
            
            if workspace_id not in self.access_patterns:
                self.access_patterns[workspace_id] = {}
            
            # Extract sequential patterns
            next_keys = []
            for i in range(len(logs) - 1):
                current = logs[i]
                next_log = logs[i + 1]
                
                # If accessed within 5 minutes, likely sequential
                time_diff = (next_log.created_at - current.created_at).total_seconds()
                if time_diff < 300:  # 5 minutes
                    # Extract key pattern (simplified)
                    next_key = f"{operation_type}:{next_log.id}"
                    if next_key not in next_keys:
                        next_keys.append(next_key)
            
            self.access_patterns[workspace_id][pattern_key] = {
                "next_likely_keys": next_keys[:10],  # Top 10
                "access_frequency": len(logs) / 7,  # Per day
            }
            
            logger.debug(
                f"Learned access patterns for {workspace_id}:{operation_type}: "
                f"{len(next_keys)} sequential patterns"
            )
        finally:
            if should_close:
                db.close()

    def record_access(
        self,
        workspace_id: str,
        cache_key: str,
        hit: bool,
    ):
        """Record cache access for learning."""
        cache_optimizer.record_cache_access(
            workspace_id=workspace_id,
            cache_key=cache_key,
            hit=hit,
        )


# Global predictive cache
_predictive_cache = PredictiveCache()


def get_predictive_cache() -> PredictiveCache:
    """Get global predictive cache instance."""
    return _predictive_cache
