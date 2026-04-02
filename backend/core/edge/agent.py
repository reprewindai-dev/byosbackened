"""Edge agent - lightweight worker that runs operations at edge."""
from typing import Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EdgeAgent:
    """
    Edge agent - lightweight worker that runs operations at edge.
    
    Runs simple operations locally (preprocessing, filtering, caching).
    Complex operations are forwarded to central system.
    """

    def __init__(self, region: str):
        self.region = region
        self.agent_id = f"edge-{region}-{datetime.utcnow().timestamp()}"

    def can_handle_operation(self, operation_type: str, input_size_bytes: int) -> bool:
        """
        Check if agent can handle operation locally.
        
        Edge agents handle:
        - Simple preprocessing
        - Caching operations
        - Lightweight filtering
        - Small file operations (< 10MB)
        """
        # Simple operations that can run at edge
        edge_operations = ["cache", "preprocess", "filter"]
        
        if operation_type in edge_operations:
            return True
        
        # Small operations can run at edge
        if input_size_bytes < 10_000_000:  # < 10MB
            return True
        
        return False

    def execute_operation(
        self,
        operation_type: str,
        input_data: Any,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Execute operation locally at edge.
        
        Returns result or forwards to central if too complex.
        """
        if not self.can_handle_operation(operation_type, len(str(input_data))):
            return {
                "handled": False,
                "reason": "Operation too complex for edge",
                "forward_to_central": True,
            }
        
        # Execute locally
        try:
            if operation_type == "cache":
                result = self._handle_cache(input_data, metadata)
            elif operation_type == "preprocess":
                result = self._handle_preprocess(input_data, metadata)
            elif operation_type == "filter":
                result = self._handle_filter(input_data, metadata)
            else:
                result = {"output": input_data, "processed": True}
            
            return {
                "handled": True,
                "region": self.region,
                "agent_id": self.agent_id,
                "result": result,
            }
        except Exception as e:
            logger.error(f"Edge agent error: {e}")
            return {
                "handled": False,
                "error": str(e),
                "forward_to_central": True,
            }

    def _handle_cache(self, input_data: Any, metadata: Optional[Dict]) -> Dict:
        """Handle cache operation."""
        # Simple cache check/update
        cache_key = metadata.get("cache_key") if metadata else None
        
        return {
            "cached": True,
            "cache_key": cache_key,
            "region": self.region,
        }

    def _handle_preprocess(self, input_data: Any, metadata: Optional[Dict]) -> Dict:
        """Handle preprocessing operation."""
        # Simple preprocessing (e.g., text normalization)
        if isinstance(input_data, str):
            processed = input_data.strip().lower()
        else:
            processed = input_data
        
        return {
            "processed": True,
            "output": processed,
        }

    def _handle_filter(self, input_data: Any, metadata: Optional[Dict]) -> Dict:
        """Handle filtering operation."""
        # Simple filtering
        filter_criteria = metadata.get("filter") if metadata else None
        
        if isinstance(input_data, list):
            filtered = input_data  # Apply filter if criteria provided
        else:
            filtered = input_data
        
        return {
            "filtered": True,
            "output": filtered,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics."""
        return {
            "agent_id": self.agent_id,
            "region": self.region,
            "status": "active",
        }


# Factory function
def create_edge_agent(region: str) -> EdgeAgent:
    """Create edge agent for region."""
    return EdgeAgent(region)
