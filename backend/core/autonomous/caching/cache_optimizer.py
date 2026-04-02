"""Autonomous cache optimization - learns patterns per workspace."""
from typing import Dict, Optional
from datetime import datetime, timedelta
import redis
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheOptimizer:
    """
    Autonomous cache optimization.
    
    Learns cache hit patterns per workspace.
    Auto-adjusts TTL, pre-caches likely-needed data.
    """

    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        # workspace_id -> {cache_key_pattern: {hit_rate, avg_ttl, access_pattern}}
        self.cache_stats: Dict[str, Dict[str, Dict]] = {}

    def get_optimal_ttl(
        self,
        workspace_id: str,
        cache_key_pattern: str,
    ) -> int:
        """
        Get optimal TTL based on learned patterns.
        
        Returns TTL in seconds.
        """
        key = f"{workspace_id}:{cache_key_pattern}"
        
        if key not in self.cache_stats:
            return 3600  # Default: 1 hour
        
        stats = self.cache_stats[key]
        
        # If hit rate is high, increase TTL
        # If hit rate is low, decrease TTL (data changes frequently)
        hit_rate = stats.get("hit_rate", 0.5)
        
        if hit_rate > 0.8:
            return 86400  # 24 hours
        elif hit_rate > 0.6:
            return 3600  # 1 hour
        else:
            return 300  # 5 minutes

    def record_cache_access(
        self,
        workspace_id: str,
        cache_key: str,
        hit: bool,
    ):
        """
        Record cache access for learning.
        
        This is the learning loop - improves TTL decisions over time.
        """
        # Extract pattern from key (e.g., "transcript:123" -> "transcript:*")
        pattern = cache_key.split(":")[0] + ":*"
        key = f"{workspace_id}:{pattern}"
        
        if key not in self.cache_stats:
            self.cache_stats[key] = {
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.5,
                "last_accessed": datetime.utcnow(),
            }
        
        stats = self.cache_stats[key]
        
        if hit:
            stats["hits"] += 1
        else:
            stats["misses"] += 1
        
        total = stats["hits"] + stats["misses"]
        stats["hit_rate"] = stats["hits"] / total if total > 0 else 0.5
        
        stats["last_accessed"] = datetime.utcnow()

    def predict_cache_needs(
        self,
        workspace_id: str,
        operation_type: str,
    ) -> List[str]:
        """
        Predict what will be needed next (for pre-caching).
        
        Returns list of cache keys to pre-cache.
        """
        # Simple heuristic: if operation_type is "transcribe", pre-cache recent transcripts
        # This can be enhanced with ML
        
        if operation_type == "transcribe":
            # Pre-cache recent transcripts (learned pattern)
            return [
                f"transcript:recent:{workspace_id}",
            ]
        
        return []


# Global cache optimizer
_cache_optimizer = CacheOptimizer()


def get_cache_optimizer() -> CacheOptimizer:
    """Get global cache optimizer instance."""
    return _cache_optimizer
