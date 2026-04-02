"""Example plugin - demonstrates plugin structure."""

PLUGIN_NAME = "example-plugin"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Example plugin demonstrating plugin system"


def register_providers():
    """Register custom providers."""
    # Example: return list of provider classes
    return []


def register_workflows():
    """Register custom workflows."""
    # Example: return list of workflow definitions
    return []


def register_routes():
    """Register custom API routes."""
    # Example: return list of FastAPI routers
    return []
