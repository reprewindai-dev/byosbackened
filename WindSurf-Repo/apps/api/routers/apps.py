"""App management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from db.models.app import App
from db.models.app_workspace import AppWorkspace
from apps.api.schemas.app import AppResponse, AppWithWorkspaceStatus
from typing import List

router = APIRouter(prefix="/apps", tags=["apps"])


@router.get("", response_model=List[AppWithWorkspaceStatus])
async def list_apps(
    request: Request,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List all apps with workspace access status."""
    # Get all active apps
    apps = db.query(App).filter(App.is_active == True).all()

    # Get workspace's app access
    workspace_apps = {
        aw.app_id: aw
        for aw in db.query(AppWorkspace).filter(AppWorkspace.workspace_id == workspace_id).all()
    }

    result = []
    for app in apps:
        app_workspace = workspace_apps.get(app.id)
        result.append(
            AppWithWorkspaceStatus(
                id=app.id,
                name=app.name,
                slug=app.slug,
                description=app.description,
                icon_url=app.icon_url,
                is_active=app.is_active,
                created_at=app.created_at,
                updated_at=app.updated_at,
                workspace_has_access=app_workspace is not None,
                workspace_is_active=app_workspace.is_active if app_workspace else None,
            )
        )

    return result


@router.get("/{app_slug}", response_model=AppWithWorkspaceStatus)
async def get_app(
    app_slug: str,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get app details with workspace access status."""
    app = db.query(App).filter(App.slug == app_slug, App.is_active == True).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App '{app_slug}' not found",
        )

    # Check workspace access
    app_workspace = (
        db.query(AppWorkspace)
        .filter(AppWorkspace.app_id == app.id, AppWorkspace.workspace_id == workspace_id)
        .first()
    )

    return AppWithWorkspaceStatus(
        id=app.id,
        name=app.name,
        slug=app.slug,
        description=app.description,
        icon_url=app.icon_url,
        is_active=app.is_active,
        created_at=app.created_at,
        updated_at=app.updated_at,
        workspace_has_access=app_workspace is not None,
        workspace_is_active=app_workspace.is_active if app_workspace else None,
    )
