# Plugin System

## Overview

Full extensibility - add providers, workflows, routes, middleware without core code changes.

## Plugin Structure

```
apps/plugins/
  {plugin_name}/
    __init__.py
    plugin.py          # Plugin metadata + registration
    providers/         # Custom AI providers (optional)
    workflows/         # Custom workflows (optional)
    routes/            # Custom API routes (optional)
    middleware/        # Custom middleware (optional)
    requirements.txt   # Plugin dependencies
```

## Creating a Plugin

### 1. Create Plugin Directory

```bash
mkdir -p apps/plugins/my-plugin
```

### 2. Create plugin.py

```python
PLUGIN_NAME = "my-plugin"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "My custom plugin"

def register_providers():
    """Register custom providers."""
    from apps.plugins.my_plugin.providers.custom_provider import CustomProvider
    return [CustomProvider]

def register_workflows():
    """Register custom workflows."""
    return []

def register_routes():
    """Register custom API routes."""
    from apps.plugins.my_plugin.routes.custom_route import router
    return [router]
```

### 3. Implement Provider (if needed)

```python
from apps.ai.contracts import LLMProvider, ChatMessage, ChatResult

class CustomProvider(LLMProvider):
    async def chat(self, messages, temperature=0.7, max_tokens=None):
        # Your implementation
        return ChatResult(...)
    
    async def embed(self, text):
        # Your implementation
        return EmbeddingResult(...)
    
    def get_name(self):
        return "custom-provider"
```

## Plugin Management

### List Plugins

```bash
GET /api/v1/plugins

Response:
{
  "available_plugins": [
    {
      "name": "my-plugin",
      "version": "1.0.0",
      "description": "My custom plugin",
      "enabled": false
    }
  ]
}
```

### Enable Plugin

```bash
POST /api/v1/plugins/{plugin_name}/enable

Response:
{
  "message": "Plugin my-plugin enabled",
  "plugin": {...}
}
```

### Disable Plugin

```bash
POST /api/v1/plugins/{plugin_name}/disable
```

### Get Plugin Docs

```bash
GET /api/v1/plugins/{plugin_name}/docs
```

## Plugin Benefits

- **Extensibility**: Add new providers without core changes
- **Isolation**: Plugins don't affect core functionality
- **Versioning**: Support multiple plugin versions
- **Workspace-scoped**: Enable plugins per workspace
