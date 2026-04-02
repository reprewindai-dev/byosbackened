"""Plugin system."""

from apps.plugins.loader import PluginLoader
from apps.plugins.registry import PluginRegistry

__all__ = [
    "PluginLoader",
    "PluginRegistry",
]
