"""Plugin registry."""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from db.models import Workspace
import logging

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for enabled plugins per workspace."""

    def __init__(self):
        self.enabled_plugins: Dict[str, List[str]] = {}  # workspace_id -> [plugin_names]

    def enable_plugin(self, db: Session, workspace_id: str, plugin_name: str) -> bool:
        """Enable plugin for workspace."""
        if workspace_id not in self.enabled_plugins:
            self.enabled_plugins[workspace_id] = []
        
        if plugin_name not in self.enabled_plugins[workspace_id]:
            self.enabled_plugins[workspace_id].append(plugin_name)
            logger.info(f"Enabled plugin {plugin_name} for workspace {workspace_id}")
            return True
        
        return False

    def disable_plugin(self, db: Session, workspace_id: str, plugin_name: str) -> bool:
        """Disable plugin for workspace."""
        if workspace_id in self.enabled_plugins:
            if plugin_name in self.enabled_plugins[workspace_id]:
                self.enabled_plugins[workspace_id].remove(plugin_name)
                logger.info(f"Disabled plugin {plugin_name} for workspace {workspace_id}")
                return True
        
        return False

    def get_enabled_plugins(self, workspace_id: str) -> List[str]:
        """Get enabled plugins for workspace."""
        return self.enabled_plugins.get(workspace_id, [])

    def is_plugin_enabled(self, workspace_id: str, plugin_name: str) -> bool:
        """Check if plugin is enabled for workspace."""
        return plugin_name in self.get_enabled_plugins(workspace_id)


# Global plugin registry
_plugin_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """Get plugin registry."""
    return _plugin_registry
