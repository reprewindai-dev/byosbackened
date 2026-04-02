"""Plugin loader."""

import os
import importlib
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PluginLoader:
    """Load plugins dynamically."""

    def __init__(self, plugin_dir: str = "apps/plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.loaded_plugins: Dict[str, any] = {}

    def discover_plugins(self) -> List[str]:
        """Discover plugins in plugin directory."""
        plugins = []

        if not self.plugin_dir.exists():
            return plugins

        for plugin_path in self.plugin_dir.iterdir():
            if plugin_path.is_dir() and (plugin_path / "plugin.py").exists():
                plugins.append(plugin_path.name)

        return plugins

    def load_plugin(self, plugin_name: str) -> Optional[Dict]:
        """Load a plugin."""
        plugin_path = self.plugin_dir / plugin_name / "plugin.py"

        if not plugin_path.exists():
            logger.warning(f"Plugin not found: {plugin_name}")
            return None

        try:
            # Import plugin module
            module_path = f"apps.plugins.{plugin_name}.plugin"
            module = importlib.import_module(module_path)

            # Get plugin metadata
            plugin_info = {
                "name": getattr(module, "PLUGIN_NAME", plugin_name),
                "version": getattr(module, "PLUGIN_VERSION", "1.0.0"),
                "description": getattr(module, "PLUGIN_DESCRIPTION", ""),
                "providers": getattr(module, "register_providers", lambda: [])(),
                "workflows": getattr(module, "register_workflows", lambda: [])(),
                "routes": getattr(module, "register_routes", lambda: [])(),
            }

            self.loaded_plugins[plugin_name] = plugin_info
            logger.info(f"Loaded plugin: {plugin_name} v{plugin_info['version']}")

            return plugin_info

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return None

    def load_all_plugins(self) -> Dict[str, Dict]:
        """Load all discovered plugins."""
        plugins = self.discover_plugins()
        loaded = {}

        for plugin_name in plugins:
            plugin_info = self.load_plugin(plugin_name)
            if plugin_info:
                loaded[plugin_name] = plugin_info

        return loaded

    def get_plugin(self, plugin_name: str) -> Optional[Dict]:
        """Get loaded plugin info."""
        return self.loaded_plugins.get(plugin_name)
