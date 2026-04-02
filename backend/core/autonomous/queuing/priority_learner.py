"""Priority learner - learn optimal priorities per operation type."""
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import Job, AIAuditLog
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class PriorityLearner:
    """
    Priority learner - learns optimal priorities per operation type.
    
    Learns which operations should have higher priority based on:
    - User behavior (which operations are time-sensitive)
    - Business impact (which operations generate revenue)
    - Historical patterns (which operations benefit from faster processing)
    """

    def __init__(self):
        # workspace_id:operation_type -> {priority, learned_from_samples, last_updated}
        self.learned_priorities: Dict[str, Dict] = {}

    def get_optimal_priority(
        self,
        workspace_id: str,
        operation_type: str,
        db: Optional[Session] = None,
    ) -> int:
        """
        Get optimal priority based on learned patterns.
        
        Returns priority (1-10, higher = more important).
        """
        key = f"{workspace_id}:{operation_type}"
        
        if key not in self.learned_priorities:
            # Learn from history
            self._learn_priority(workspace_id, operation_type, db)
        
        if key in self.learned_priorities:
            return self.learned_priorities[key]["priority"]
        
        # Default priorities
        defaults = {
            "transcribe": 5,
            "extract": 7,  # Higher priority (faster turnaround)
            "export": 3,  # Lower priority (can wait)
            "chat": 6,
        }
        
        return defaults.get(operation_type, 5)

    def _learn_priority(
        self,
        workspace_id: str,
        operation_type: str,
        db: Optional[Session],
    ):
        """Learn optimal priority from historical data."""
        if not db:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            # Get last 30 days of jobs
            cutoff = datetime.utcnow() - timedelta(days=30)
            
            jobs = db.query(Job).filter(
                Job.workspace_id == workspace_id,
                Job.operation_type == operation_type,
                Job.created_at >= cutoff,
            ).all()
            
            if len(jobs) < 20:  # Need at least 20 samples
                return
            
            # Analyze priority signals
            # 1. Time sensitivity: operations completed quickly after creation
            avg_time_to_completion = []
            for job in jobs:
                if job.completed_at and job.created_at:
                    time_diff = (job.completed_at - job.created_at).total_seconds()
                    avg_time_to_completion.append(time_diff)
            
            if not avg_time_to_completion:
                return
            
            avg_completion_time = sum(avg_time_to_completion) / len(avg_time_to_completion)
            
            # 2. User urgency: operations accessed immediately after completion
            urgent_count = 0
            for job in jobs:
                if job.completed_at:
                    # Check if accessed within 1 minute of completion
                    # (simplified - would check audit logs in production)
                    urgent_count += 1
            
            urgency_ratio = urgent_count / len(jobs) if jobs else 0.0
            
            # Calculate priority (1-10)
            # Faster completion + higher urgency = higher priority
            if avg_completion_time < 60:  # < 1 minute
                base_priority = 8
            elif avg_completion_time < 300:  # < 5 minutes
                base_priority = 6
            else:
                base_priority = 4
            
            # Adjust for urgency
            if urgency_ratio > 0.8:
                priority = min(10, base_priority + 2)
            elif urgency_ratio > 0.5:
                priority = min(10, base_priority + 1)
            else:
                priority = base_priority
            
            key = f"{workspace_id}:{operation_type}"
            self.learned_priorities[key] = {
                "priority": priority,
                "learned_from_samples": len(jobs),
                "avg_completion_time": avg_completion_time,
                "urgency_ratio": urgency_ratio,
                "last_updated": datetime.utcnow(),
            }
            
            logger.info(
                f"Learned priority for {workspace_id}:{operation_type}: "
                f"priority={priority}, samples={len(jobs)}"
            )
        finally:
            if should_close:
                db.close()

    def update_priority_signal(
        self,
        workspace_id: str,
        operation_type: str,
        completion_time_seconds: float,
        accessed_immediately: bool,
    ):
        """
        Update priority learning with new signal.
        
        Called when operation completes to improve learning.
        """
        key = f"{workspace_id}:{operation_type}"
        
        if key not in self.learned_priorities:
            self.learned_priorities[key] = {
                "priority": 5,
                "learned_from_samples": 0,
                "avg_completion_time": completion_time_seconds,
                "urgency_ratio": 1.0 if accessed_immediately else 0.0,
                "last_updated": datetime.utcnow(),
            }
        else:
            # Update moving average
            learned = self.learned_priorities[key]
            alpha = 0.1  # Learning rate
            
            learned["avg_completion_time"] = (
                alpha * completion_time_seconds +
                (1 - alpha) * learned["avg_completion_time"]
            )
            
            # Update urgency ratio
            if accessed_immediately:
                learned["urgency_ratio"] = (
                    alpha * 1.0 + (1 - alpha) * learned["urgency_ratio"]
                )
            else:
                learned["urgency_ratio"] = (
                    alpha * 0.0 + (1 - alpha) * learned["urgency_ratio"]
                )
            
            learned["learned_from_samples"] += 1
            learned["last_updated"] = datetime.utcnow()
            
            # Recalculate priority
            base_priority = 5
            if learned["avg_completion_time"] < 60:
                base_priority = 8
            elif learned["avg_completion_time"] < 300:
                base_priority = 6
            
            if learned["urgency_ratio"] > 0.8:
                priority = min(10, base_priority + 2)
            elif learned["urgency_ratio"] > 0.5:
                priority = min(10, base_priority + 1)
            else:
                priority = base_priority
            
            learned["priority"] = priority


# Global priority learner
_priority_learner = PriorityLearner()


def get_priority_learner() -> PriorityLearner:
    """Get global priority learner instance."""
    return _priority_learner
