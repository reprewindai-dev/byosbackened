"""Latency monitoring per region - continuously measures latency."""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from core.edge.region_manager import RegionManager
from core.config import get_settings
import asyncio
import httpx
import logging
import statistics

logger = logging.getLogger(__name__)
settings = get_settings()
region_manager = RegionManager()


class LatencyMonitor:
    """
    Monitor latency to each region continuously.
    
    Measures latency to each region and maintains statistics.
    Used for intelligent edge routing decisions.
    """

    def __init__(self):
        # region -> list of recent latencies (ms)
        self.latency_history: Dict[str, List[float]] = {
            region: [] for region in region_manager.REGIONS.keys()
        }
        # region -> {avg, p50, p95, p99, last_check}
        self.latency_stats: Dict[str, Dict] = {
            region: {
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "last_check": None,
            }
            for region in region_manager.REGIONS.keys()
        }
        self.max_history_size = 1000  # Keep last 1000 measurements

    async def measure_latency(
        self,
        region: str,
        endpoint: Optional[str] = None,
    ) -> Optional[float]:
        """
        Measure latency to region.
        
        Returns latency in milliseconds, or None if measurement failed.
        """
        if region not in region_manager.REGIONS:
            logger.warning(f"Unknown region: {region}")
            return None
        
        # Default endpoint (can be overridden)
        if not endpoint:
            # Use health check endpoint
            endpoint = f"https://{region}.api.example.com/health"  # Placeholder
        
        try:
            start_time = datetime.utcnow()
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(endpoint)
                end_time = datetime.utcnow()
                
                if response.status_code == 200:
                    latency_ms = (end_time - start_time).total_seconds() * 1000
                    self._record_latency(region, latency_ms)
                    return latency_ms
                else:
                    logger.warning(f"Health check failed for {region}: {response.status_code}")
                    return None
                        
        except httpx.TimeoutException:
            logger.warning(f"Latency measurement timeout for {region}")
            return None
        except Exception as e:
            logger.error(f"Failed to measure latency for {region}: {e}")
            return None

    def _record_latency(self, region: str, latency_ms: float):
        """Record latency measurement and update statistics."""
        if region not in self.latency_history:
            self.latency_history[region] = []
        
        history = self.latency_history[region]
        history.append(latency_ms)
        
        # Keep only recent measurements
        if len(history) > self.max_history_size:
            history.pop(0)
        
        # Update statistics
        if len(history) >= 10:  # Need at least 10 samples for percentiles
            self.latency_stats[region] = {
                "avg": statistics.mean(history),
                "p50": statistics.median(history),
                "p95": self._percentile(history, 95),
                "p99": self._percentile(history, 99),
                "last_check": datetime.utcnow(),
            }
        else:
            # Use simple average if not enough samples
            self.latency_stats[region] = {
                "avg": statistics.mean(history) if history else 0.0,
                "p50": statistics.median(history) if history else 0.0,
                "p95": statistics.mean(history) if history else 0.0,
                "p99": statistics.mean(history) if history else 0.0,
                "last_check": datetime.utcnow(),
            }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def get_latency_stats(self, region: str) -> Optional[Dict]:
        """Get latency statistics for region."""
        return self.latency_stats.get(region)

    def get_all_latency_stats(self) -> Dict[str, Dict]:
        """Get latency statistics for all regions."""
        return self.latency_stats.copy()

    def get_best_region(self, user_region: Optional[str] = None) -> str:
        """
        Get best region based on latency.
        
        If user_region provided, prefers that region if latency is acceptable.
        Otherwise, returns region with lowest latency.
        """
        if not self.latency_stats:
            return "us-east"  # Default
        
        # If user region specified and latency is acceptable (< 200ms), use it
        if user_region and user_region in self.latency_stats:
            stats = self.latency_stats[user_region]
            if stats["avg"] < 200.0:
                return user_region
        
        # Find region with lowest average latency
        best_region = min(
            self.latency_stats.keys(),
            key=lambda r: self.latency_stats[r]["avg"] if self.latency_stats[r]["avg"] > 0 else float('inf')
        )
        
        return best_region

    async def monitor_all_regions(self):
        """Monitor all regions periodically (runs in background)."""
        while True:
            try:
                for region in region_manager.get_regions():
                    await self.measure_latency(region)
                
                # Wait 60 seconds before next check
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error in latency monitoring: {e}")
                await asyncio.sleep(60)


# Global latency monitor
_latency_monitor = LatencyMonitor()


def get_latency_monitor() -> LatencyMonitor:
    """Get global latency monitor instance."""
    return _latency_monitor
