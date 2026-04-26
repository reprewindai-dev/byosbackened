"""Task distributor - decide which tasks run at edge vs central."""
from typing import Dict, Optional, List, Any
from decimal import Decimal
from core.edge.agent import EdgeAgent
from core.edge.placement_learner import PlacementLearner
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
placement_learner = PlacementLearner()


class TaskDistributor:
    """
    Task distributor - decides which tasks run at edge vs central.
    
    Automatic task distribution based on:
    - Operation complexity
    - Input size
    - Learned patterns (which operations benefit from edge)
    """

    # Operations that should run at edge
    EDGE_OPERATIONS = ["cache", "preprocess", "filter", "validate"]

    # Operations that should run centrally
    CENTRAL_OPERATIONS = ["train", "export", "analyze"]

    def __init__(self):
        self.edge_agents: Dict[str, EdgeAgent] = {}  # region -> agent

    def get_agent_for_region(self, region: str) -> EdgeAgent:
        """Get or create edge agent for region."""
        if region not in self.edge_agents:
            from core.edge.agent import create_edge_agent
            self.edge_agents[region] = create_edge_agent(region)
        return self.edge_agents[region]

    def should_run_at_edge(
        self,
        workspace_id: str,
        operation_type: str,
        input_size_bytes: int,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Decide if task should run at edge or central.
        
        Returns decision with reasoning.
        """
        # Check if operation is explicitly edge or central
        if operation_type in self.EDGE_OPERATIONS:
            return {
                "run_at_edge": True,
                "reasoning": f"Operation '{operation_type}' is optimized for edge",
                "region": region or "us-east",
            }
        
        if operation_type in self.CENTRAL_OPERATIONS:
            return {
                "run_at_edge": False,
                "reasoning": f"Operation '{operation_type}' requires central resources",
                "region": None,
            }
        
        # Check learned patterns
        if workspace_id:
            learned_edge = placement_learner.should_use_edge(
                workspace_id=workspace_id,
                operation_type=operation_type,
            )
            
            if learned_edge:
                optimal_region = placement_learner.get_optimal_region(
                    workspace_id=workspace_id,
                    operation_type=operation_type,
                )
                return {
                    "run_at_edge": True,
                    "reasoning": f"Learned pattern: '{operation_type}' benefits from edge",
                    "region": optimal_region or region or "us-east",
                }
        
        # Default: use edge for small operations, central for large
        if input_size_bytes < 10_000_000:  # < 10MB
            return {
                "run_at_edge": True,
                "reasoning": f"Small operation ({input_size_bytes} bytes) - run at edge",
                "region": region or "us-east",
            }
        else:
            return {
                "run_at_edge": False,
                "reasoning": f"Large operation ({input_size_bytes} bytes) - run centrally",
                "region": None,
            }

    def distribute_task(
        self,
        workspace_id: str,
        operation_type: str,
        input_data: Any,
        metadata: Optional[Dict] = None,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Distribute task to edge or central.
        
        Returns execution result or forwarding instruction.
        """
        input_size_bytes = len(str(input_data))
        
        decision = self.should_run_at_edge(
            workspace_id=workspace_id,
            operation_type=operation_type,
            input_size_bytes=input_size_bytes,
            region=region,
        )
        
        if decision["run_at_edge"]:
            # Execute at edge
            agent = self.get_agent_for_region(decision["region"])
            result = agent.execute_operation(
                operation_type=operation_type,
                input_data=input_data,
                metadata=metadata,
            )
            
            if result.get("handled"):
                return {
                    "executed_at": "edge",
                    "region": decision["region"],
                    "result": result,
                }
            else:
                # Edge couldn't handle, forward to central
                return {
                    "executed_at": "central",
                    "reasoning": result.get("reason", "Edge execution failed"),
                    "forward": True,
                }
        else:
            # Forward to central
            return {
                "executed_at": "central",
                "reasoning": decision["reasoning"],
                "forward": True,
            }

    def get_distribution_stats(
        self,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Get task distribution statistics for workspace."""
        # This would track edge vs central execution counts
        # For now, return placeholder
        return {
            "workspace_id": workspace_id,
            "edge_executions": 0,
            "central_executions": 0,
            "edge_savings_ms": 0,
        }


# Global task distributor
_task_distributor = TaskDistributor()


def get_task_distributor() -> TaskDistributor:
    """Get global task distributor instance."""
    return _task_distributor
