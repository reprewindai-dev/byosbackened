"""Plugin management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from apps.plugins.loader import PluginLoader
from apps.plugins.registry import get_plugin_registry
from pydantic import BaseModel

router = APIRouter(prefix="/plugins", tags=["plugins"])
plugin_loader = PluginLoader()
plugin_registry = get_plugin_registry()


class EnablePluginRequest(BaseModel):
    """Enable plugin request."""
    plugin_name: str


@router.get("")
async def list_plugins(
    workspace_id: str = Depends(get_current_workspace_id),
):
    """List available plugins."""
    plugins = plugin_loader.load_all_plugins()
    enabled = plugin_registry.get_enabled_plugins(workspace_id)
    
    return {
        "available_plugins": [
            {
                "name": name,
                "version": info.get("version", "1.0.0"),
                "description": info.get("description", ""),
                "enabled": name in enabled,
            }
            for name, info in plugins.items()
        ],
    }


@router.post("/{plugin_name}/enable")
async def enable_plugin(
    plugin_name: str,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Enable plugin for workspace."""
    # Load plugin first
    plugin_info = plugin_loader.load_plugin(plugin_name)
    if not plugin_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found: {plugin_name}",
        )
    
    # Enable plugin
    success = plugin_registry.enable_plugin(db, workspace_id, plugin_name)
    
    return {
        "message": f"Plugin {plugin_name} enabled",
        "plugin": plugin_info,
    }


@router.post("/{plugin_name}/disable")
async def disable_plugin(
    plugin_name: str,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Disable plugin for workspace."""
    success = plugin_registry.disable_plugin(db, workspace_id, plugin_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not enabled: {plugin_name}",
        )
    
    return {
        "message": f"Plugin {plugin_name} disabled",
    }


@router.get("/{plugin_name}/docs")
async def get_plugin_docs(
    plugin_name: str,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Get plugin documentation."""
    plugin_info = plugin_loader.get_plugin(plugin_name)
    if not plugin_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found: {plugin_name}",
        )
    
    return {
        "name": plugin_info.get("name"),
        "version": plugin_info.get("version"),
        "description": plugin_info.get("description"),
        "providers": plugin_info.get("providers", []),
        "workflows": plugin_info.get("workflows", []),
    }
