"""Edge-specific worker implementation."""
from typing import Any
from celery import Celery
from core.config import get_settings
from core.edge.task_distributor import get_task_distributor
from core.edge.agent import EdgeAgent
from apps.worker.worker import celery_app
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
task_distributor = get_task_distributor()


class EdgeWorker:
    """
    Edge-specific worker implementation.
    
    Runs lightweight operations at edge regions.
    Forwards complex operations to central workers.
    """

    def __init__(self, region: str):
        self.region = region
        self.celery_app = celery_app
        self.agent = EdgeAgent(region)

    def process_task(
        self,
        workspace_id: str,
        operation_type: str,
        input_data: Any,
        metadata: dict = None,
    ):
        """
        Process task at edge.
        
        Returns result if handled locally, or forwards to central.
        """
        logger.info(
            f"Edge worker [{self.region}] processing {operation_type} "
            f"for workspace {workspace_id}"
        )
        
        # Use task distributor to decide
        result = task_distributor.distribute_task(
            workspace_id=workspace_id,
            operation_type=operation_type,
            input_data=input_data,
            metadata=metadata,
            region=self.region,
        )
        
        if result.get("executed_at") == "edge":
            logger.info(f"Task executed at edge [{self.region}]")
            return result["result"]
        else:
            # Forward to central
            logger.info(f"Task forwarded to central: {result.get('reasoning')}")
            # In production, this would enqueue to central queue
            return {
                "forwarded": True,
                "reasoning": result.get("reasoning"),
            }

    def get_metrics(self) -> dict:
        """Get edge worker metrics."""
        return {
            "region": self.region,
            "agent_id": self.agent.agent_id,
            "status": "active",
        }


# Factory function
def create_edge_worker(region: str) -> EdgeWorker:
    """Create edge worker for region."""
    return EdgeWorker(region)
