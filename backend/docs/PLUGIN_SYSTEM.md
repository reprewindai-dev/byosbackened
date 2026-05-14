# Plugin System

## Overview

The plugin system lets you extend BYOS AI with custom AI providers, processing pipelines, or integrations without touching core code. Plugins are auto-discovered at startup and can be independently enabled/disabled per workspace.

---

## Plugin Architecture

```
apps/
  plugins/
    __init__.py           ← plugin registry + auto-discovery
    base_plugin.py        ← BasePlugin abstract class
    my_custom_plugin/
      __init__.py
      plugin.py           ← must implement BasePlugin
      config.py           ← optional plugin-specific config
```

---

## BasePlugin Interface

Every plugin must implement these methods:

```python
from apps.plugins.base_plugin import BasePlugin

class MyCustomPlugin(BasePlugin):
    name = "my_custom_plugin"
    version = "1.0.0"
    description = "Does something custom"

    async def initialize(self, config: dict) -> None:
        """Called once at plugin load. Set up connections, load models."""
        pass

    async def execute(self, request: dict) -> dict:
        """Called for each request routed to this plugin."""
        return {"response": "...", "provider": self.name}

    async def health_check(self) -> bool:
        """Return True if plugin is healthy and ready."""
        return True

    async def shutdown(self) -> None:
        """Clean up connections on shutdown."""
        pass
```

---

## Plugin Management Endpoints

### List Plugins
```
GET /api/v1/plugins
→ [{
  "id": "my_custom_plugin",
  "name": "My Custom Plugin",
  "version": "1.0.0",
  "enabled": true,
  "healthy": true,
  "workspace_id": null   ← null = global, UUID = workspace-scoped
}]
```

### Enable/Disable
```
POST /api/v1/plugins/{plugin_id}/enable
POST /api/v1/plugins/{plugin_id}/disable
```

### Plugin Health
```
GET /api/v1/plugins/{plugin_id}/health
→ { "healthy": true, "last_check": "2026-01-15T14:30:00Z" }
```

---

## Creating a Custom AI Provider Plugin

Example: adding Anthropic Claude as a provider.

```python
# apps/plugins/anthropic_plugin/plugin.py
import httpx
from apps.plugins.base_plugin import BasePlugin

class AnthropicPlugin(BasePlugin):
    name = "anthropic"
    version = "1.0.0"
    description = "Anthropic Claude provider"

    async def initialize(self, config: dict) -> None:
        self.api_key = config.get("ANTHROPIC_API_KEY")
        self.model = config.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        self.client = httpx.AsyncClient(timeout=60)

    async def execute(self, request: dict) -> dict:
        resp = await self.client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.model,
                "max_tokens": request.get("max_tokens", 2048),
                "messages": [{"role": "user", "content": request["prompt"]}]
            }
        )
        data = resp.json()
        return {
            "response": data["content"][0]["text"],
            "provider": "anthropic",
            "model": self.model,
        }

    async def health_check(self) -> bool:
        return bool(self.api_key)

    async def shutdown(self) -> None:
        await self.client.aclose()
```

The plugin is automatically discovered at startup. Enable it via:
```
POST /api/v1/plugins/anthropic/enable
```

---

## Plugin Configuration

Plugins receive their configuration from the workspace plugin settings:

```
POST /api/v1/plugins/{plugin_id}/config
{
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "ANTHROPIC_MODEL": "claude-3-opus-20240229"
}
```

Config is stored encrypted in the database per workspace.

---

## Using a Plugin in Routing

Once enabled, reference the plugin by name in routing policies:

```
POST /api/v1/routing/policy
{
  "strategy": "quality_optimized",
  "preferred_providers": ["anthropic", "ollama"],
  "excluded_providers": []
}
```

Or force a specific plugin in a single call:
```
POST /v1/exec
{
  "prompt": "...",
  "model": "claude-3-opus-20240229",
  "provider_override": "anthropic"
}
```

---

## Plugin Scoping

| Scope | Description |
|---|---|
| **Global** | Available to all workspaces. Set by system admin. |
| **Workspace** | Available only to one workspace. Set by workspace admin. |

A plugin enabled globally can be disabled for a specific workspace.
