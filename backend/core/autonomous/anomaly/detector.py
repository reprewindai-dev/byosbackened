"""ML anomaly detection - learns normal patterns, flags anomalies."""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import AIAuditLog, SecurityAuditLog
from core.config import get_settings
import numpy as np
from sklearn.ensemble import IsolationForest
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class AnomalyDetector:
    """
    ML anomaly detection.
    
    Learns normal patterns per workspace.
    Flags anomalies: unusual traffic, cost spikes, quality degradation.
    """

    def __init__(self):
        self.models: Dict[str, any] = {}  # workspace_id -> model
        self.normal_patterns: Dict[str, Dict] = {}  # workspace_id -> {avg_cost, avg_requests_per_hour, etc.}

    def detect_anomalies(
        self,
        workspace_id: str,
        operation_type: str,
        cost: float,
        request_count: int,
        quality_score: float,
    ) -> Dict[str, any]:
        """
        Detect anomalies in current metrics.
        
        Returns anomaly detection result.
        """
        # Get or create normal patterns
        if workspace_id not in self.normal_patterns:
            self._learn_normal_patterns(workspace_id)
        
        if workspace_id not in self.normal_patterns:
            return {
                "anomaly_detected": False,
                "reason": "Not enough data to establish baseline",
            }
        
        patterns = self.normal_patterns[workspace_id]
        
        anomalies = []
        
        # Check cost anomaly (spike > 2x normal)
        avg_cost = patterns.get("avg_cost", 0.001)
        if cost > avg_cost * 2:
            anomalies.append({
                "type": "cost_spike",
                "severity": "high",
                "message": f"Cost spike detected: ${cost:.6f} vs normal ${avg_cost:.6f}",
            })
        
        # Check traffic anomaly (spike > 3x normal)
        avg_requests = patterns.get("avg_requests_per_hour", 10)
        if request_count > avg_requests * 3:
            anomalies.append({
                "type": "traffic_spike",
                "severity": "medium",
                "message": f"Traffic spike: {request_count} requests vs normal {avg_requests}",
            })
        
        # Check quality degradation
        avg_quality = patterns.get("avg_quality", 0.85)
        if quality_score < avg_quality * 0.8:  # 20% degradation
            anomalies.append({
                "type": "quality_degradation",
                "severity": "high",
                "message": f"Quality degradation: {quality_score:.2f} vs normal {avg_quality:.2f}",
            })
        
        if anomalies:
            return {
                "anomaly_detected": True,
                "anomalies": anomalies,
                "severity": max(a["severity"] for a in anomalies),
            }
        
        return {
            "anomaly_detected": False,
        }

    def _learn_normal_patterns(self, workspace_id: str):
        """Learn normal patterns from historical data."""
        db = SessionLocal()
        try:
            # Get last 7 days of data
            cutoff = datetime.utcnow() - timedelta(days=7)
            
            logs = db.query(AIAuditLog).filter(
                AIAuditLog.workspace_id == workspace_id,
                AIAuditLog.created_at >= cutoff,
            ).all()
            
            if len(logs) < 50:  # Need at least 50 samples
                return
            
            # Calculate averages
            costs = [float(log.cost) for log in logs]
            qualities = [
                float(log.actual_quality) if log.actual_quality else 0.85
                for log in logs
            ]
            
            # Aggregate by hour
            hourly_counts: Dict[int, int] = {}
            for log in logs:
                hour = log.created_at.hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            
            self.normal_patterns[workspace_id] = {
                "avg_cost": np.mean(costs),
                "avg_quality": np.mean(qualities),
                "avg_requests_per_hour": np.mean(list(hourly_counts.values())),
                "learned_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Learned normal patterns for workspace {workspace_id}")
            
        finally:
            db.close()


# Global anomaly detector
_anomaly_detector = AnomalyDetector()


def get_anomaly_detector() -> AnomalyDetector:
    """Get global anomaly detector instance."""
    return _anomaly_detector
