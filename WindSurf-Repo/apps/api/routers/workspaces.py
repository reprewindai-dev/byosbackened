"""Workspace management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from db.models.workspace import Workspace
from db.models.app import App
from db.models.app_workspace import AppWorkspace
from db.models.workspace_retention_policy import WorkspaceRetentionPolicy
from apps.api.deps_rbac import require_workspace_role
from db.models.workspace_membership import WorkspaceRole
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


class RetentionPolicyResponse(BaseModel):
    id: str
    workspace_id: str
    retention_days: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RetentionPolicyUpsertRequest(BaseModel):
    name: str
    description: Optional[str] = None
    policy_type: str
    retention_days: int = 90
    retention_action: str = "delete"
    conditions: Optional[str] = None
    exceptions: Optional[str] = None
    is_active: bool = True


@router.get("")
async def list_workspaces(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List accessible workspaces for current user."""
    # Return the current workspace
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.is_active == True)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return [
        WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            is_active=workspace.is_active,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
    ]


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


@router.get("/{workspace_id}/retention-policy", response_model=RetentionPolicyResponse)
async def get_retention_policy(
    workspace_id: str,
    current_workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    # Verify user has access to the workspace
    if workspace_id != current_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other workspaces",
        )

    # Get retention policies
    policies = db.query(WorkspaceRetentionPolicy).filter(
        WorkspaceRetentionPolicy.workspace_id == workspace_id,
        WorkspaceRetentionPolicy.is_active == True
    ).all()

    return [
        RetentionPolicyResponse(
            id=policy.id,
            workspace_id=policy.workspace_id,
            name=policy.name,
            description=policy.description,
            policy_type=policy.policy_type,
            retention_days=policy.retention_days,
            retention_action=policy.retention_action,
            is_active=policy.is_active,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )
        for policy in policies
    ]


@router.put("/{workspace_id}/retention-policy", response_model=RetentionPolicyResponse)
async def upsert_retention_policy(
    workspace_id: str,
    request: RetentionPolicyUpsertRequest,
    current_workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    _user=Depends(require_workspace_role(WorkspaceRole.ADMIN)),
):
    if workspace_id != current_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify other workspaces",
        )

    # Check for existing policy of the same type
    existing = db.query(WorkspaceRetentionPolicy).filter(
        WorkspaceRetentionPolicy.workspace_id == workspace_id,
        WorkspaceRetentionPolicy.policy_type == request.policy_type
    ).first()

    if existing:
        # Update existing policy
        existing.name = request.name
        existing.description = request.description
        existing.retention_days = request.retention_days
        existing.retention_action = request.retention_action
        existing.conditions = request.conditions
        existing.exceptions = request.exceptions
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        policy = existing
    else:
        # Create new policy
        import uuid
        policy = WorkspaceRetentionPolicy(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            name=request.name,
            description=request.description,
            policy_type=request.policy_type,
            retention_days=request.retention_days,
            retention_action=request.retention_action,
            conditions=request.conditions,
            exceptions=request.exceptions,
            is_active=True,
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

    return RetentionPolicyResponse(
        id=policy.id,
        workspace_id=policy.workspace_id,
        name=policy.name,
        description=policy.description,
        policy_type=policy.policy_type,
        retention_days=policy.retention_days,
        retention_action=policy.retention_action,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )
