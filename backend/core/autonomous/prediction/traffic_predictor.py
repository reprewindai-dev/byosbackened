"""Traffic pattern prediction - learn patterns per workspace."""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import AIAuditLog
from core.config import get_settings
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class TrafficPredictor:
    """
    Predict traffic patterns per workspace.
    
    Learns daily, weekly, seasonal patterns.
    After months, we know YOUR traffic rhythms.
    """

    def __init__(self):
        self.models: Dict[str, any] = {}  # workspace_id -> model

    def predict_traffic(
        self,
        workspace_id: str,
        hours_ahead: int = 24,
    ) -> Dict[str, any]:
        """
        Predict traffic for next N hours.
        
        Returns predicted request count per hour.
        """
        # Get or create model
        if workspace_id not in self.models:
            # Try to load from history
            self._train_from_history(workspace_id)
        
        if workspace_id not in self.models:
            # Not enough data yet
            return {
                "predicted": False,
                "reason": "Not enough historical data",
            }
        
        model = self.models[workspace_id]
        
        # Predict for next N hours
        predictions = []
        now = datetime.utcnow()
        
        for i in range(hours_ahead):
            hour = (now + timedelta(hours=i)).hour
            day_of_week = (now + timedelta(hours=i)).weekday()
            
            # Features: hour of day, day of week
            features = [[hour, day_of_week]]
            predicted_count = model.predict(features)[0]
            
            predictions.append({
                "hour": (now + timedelta(hours=i)).isoformat(),
                "predicted_requests": max(0, int(predicted_count)),
            })
        
        return {
            "predicted": True,
            "predictions": predictions,
            "peak_hour": max(predictions, key=lambda x: x["predicted_requests"])["hour"],
        }

    def _train_from_history(self, workspace_id: str):
        """Train model from historical traffic data."""
        db = SessionLocal()
        try:
            # Get last 30 days of traffic
            cutoff = datetime.utcnow() - timedelta(days=30)
            
            logs = db.query(AIAuditLog).filter(
                AIAuditLog.workspace_id == workspace_id,
                AIAuditLog.created_at >= cutoff,
            ).all()
            
            if len(logs) < 100:  # Need at least 100 samples
                logger.debug(f"Not enough traffic data for {workspace_id}: {len(logs)} samples")
                return
            
            # Aggregate by hour
            hourly_counts: Dict[int, int] = {}  # hour -> count
            
            for log in logs:
                hour = log.created_at.hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            
            # Prepare features and targets
            X = []
            y = []
            
            for log in logs:
                hour = log.created_at.hour
                day_of_week = log.created_at.weekday()
                X.append([hour, day_of_week])
                y.append(1)  # Count this as 1 request
            
            if len(X) < 50:
                return
            
            # Train model
            model = GradientBoostingRegressor(n_estimators=50, max_depth=3, random_state=42)
            model.fit(X, y)
            
            self.models[workspace_id] = model
            
            logger.info(f"Trained traffic predictor for workspace {workspace_id}")
            
        finally:
            db.close()

    def predict_spike(
        self,
        workspace_id: str,
        hours_ahead: int = 2,
    ) -> Optional[Dict[str, any]]:
        """
        Predict if traffic will spike in next N hours.
        
        Returns spike prediction if detected.
        """
        prediction = self.predict_traffic(workspace_id, hours_ahead=hours_ahead)
        
        if not prediction.get("predicted"):
            return None
        
        predictions = prediction["predictions"]
        
        # Calculate average
        avg_requests = sum(p["predicted_requests"] for p in predictions) / len(predictions)
        
        # Find spikes (2x average)
        spikes = [
            p for p in predictions
            if p["predicted_requests"] > avg_requests * 2
        ]
        
        if spikes:
            spike = max(spikes, key=lambda x: x["predicted_requests"])
            return {
                "will_spike": True,
                "spike_time": spike["hour"],
                "predicted_requests": spike["predicted_requests"],
                "normal_avg": int(avg_requests),
                "spike_multiplier": spike["predicted_requests"] / avg_requests if avg_requests > 0 else 1.0,
            }
        
        return None


# Global traffic predictor
_traffic_predictor = TrafficPredictor()


def get_traffic_predictor() -> TrafficPredictor:
    """Get global traffic predictor instance."""
    return _traffic_predictor
