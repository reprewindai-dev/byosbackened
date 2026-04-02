"""Workspace management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from db.models.workspace import Workspace
from db.models.app import App
from db.models.app_workspace import AppWorkspace
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceResponse(BaseModel):
    """Workspace response schema."""

    id: str
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EnableAppRequest(BaseModel):
    """Request to enable app for workspace."""

    config: Optional[dict] = None


@router.post("/{workspace_id}/apps/{app_slug}/enable")
async def enable_app_for_workspace(
    workspace_id: str,
    app_slug: str,
    request: EnableAppRequest,
    current_workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Enable an app for a workspace."""
    # Verify user has access to the workspace
    if workspace_id != current_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify other workspaces",
        )

    # Get workspace
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.is_active == True)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # Get app
    app = db.query(App).filter(App.slug == app_slug, App.is_active == True).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App '{app_slug}' not found",
        )

    # Check if already enabled
    existing = (
        db.query(AppWorkspace)
        .filter(AppWorkspace.app_id == app.id, AppWorkspace.workspace_id == workspace.id)
        .first()
    )

    if existing:
        # Update existing
        existing.is_active = True
        if request.config:
            existing.config = request.config
        db.commit()
        db.refresh(existing)
        return {
            "message": f"App '{app_slug}' already enabled for workspace",
            "app_workspace_id": existing.id,
            "is_active": existing.is_active,
        }

    # Create new app-workspace link
    app_workspace = AppWorkspace(
        app_id=app.id,
        workspace_id=workspace.id,
        is_active=True,
        config=request.config or {},
    )
    db.add(app_workspace)
    db.commit()
    db.refresh(app_workspace)

    return {
        "message": f"App '{app_slug}' enabled for workspace",
        "app_workspace_id": app_workspace.id,
        "is_active": app_workspace.is_active,
    }


@router.post("/{workspace_id}/apps/{app_slug}/disable")
async def disable_app_for_workspace(
    workspace_id: str,
    app_slug: str,
    current_workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Disable an app for a workspace."""
    # Verify user has access to the workspace
    if workspace_id != current_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify other workspaces",
        )

    # Get workspace
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.is_active == True)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # Get app
    app = db.query(App).filter(App.slug == app_slug, App.is_active == True).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App '{app_slug}' not found",
        )

    # Get app-workspace link
    app_workspace = (
        db.query(AppWorkspace)
        .filter(AppWorkspace.app_id == app.id, AppWorkspace.workspace_id == workspace.id)
        .first()
    )

    if not app_workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App '{app_slug}' is not enabled for this workspace",
        )

    # Disable (don't delete, just mark inactive)
    app_workspace.is_active = False
    db.commit()
    db.refresh(app_workspace)

    return {
        "message": f"App '{app_slug}' disabled for workspace",
        "app_workspace_id": app_workspace.id,
        "is_active": app_workspace.is_active,
    }


@router.get("/{workspace_id}/apps")
async def list_workspace_apps(
    workspace_id: str,
    current_workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List apps enabled for a workspace."""
    # Verify user has access to the workspace
    if workspace_id != current_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other workspaces",
        )

    # Get workspace
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.is_active == True)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # Get enabled apps
    app_workspaces = (
        db.query(AppWorkspace)
        .filter(AppWorkspace.workspace_id == workspace.id, AppWorkspace.is_active == True)
        .all()
    )

    apps = []
    for aw in app_workspaces:
        app = db.query(App).filter(App.id == aw.app_id).first()
        if app and app.is_active:
            apps.append(
                {
                    "id": app.id,
                    "name": app.name,
                    "slug": app.slug,
                    "description": app.description,
                    "icon_url": app.icon_url,
                    "enabled_at": aw.created_at.isoformat(),
                    "config": aw.config,
                }
            )

    return {
        "workspace_id": workspace.id,
        "workspace_name": workspace.name,
        "apps": apps,
    }
