"""RBAC dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user, get_current_workspace_id
from db.session import get_db
from db.models.user import User
from db.models.workspace_membership import WorkspaceMembership, WorkspaceRole
from core.rbac.policy import role_at_least, has_permission, Permission


def require_workspace_role(minimum_role: WorkspaceRole):
    """Dependency to require minimum workspace role."""
    async def _dep(
        user: User = Depends(get_current_user),
        workspace_id: str = Depends(get_current_workspace_id),
        db: Session = Depends(get_db),
    ) -> User:
        if user.is_superuser:
            return user

        # Check user's membership in the workspace
        membership = db.query(WorkspaceMembership).filter(
            WorkspaceMembership.user_id == user.id,
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.status == "active"
        ).first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this workspace"
            )

        # Check if user's role meets the minimum requirement
        if not role_at_least(WorkspaceRole(membership.role), minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role.value} role or higher"
            )

        return user

    return _dep


def require_permission(permission: Permission):
    """Dependency to require specific permission."""
    async def _dep(
        user: User = Depends(get_current_user),
        workspace_id: str = Depends(get_current_workspace_id),
        db: Session = Depends(get_db),
    ) -> User:
        if user.is_superuser:
            return user

        # Get user's role in workspace
        membership = db.query(WorkspaceMembership).filter(
            WorkspaceMembership.user_id == user.id,
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.status == "active"
        ).first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this workspace"
            )

        # Check if user has the required permission
        if not has_permission(WorkspaceRole(membership.role), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {permission.value}"
            )

        return user

    return _dep


def can_access_workspace(workspace_id: str, user: User, db: Session) -> bool:
    """Check if user can access a workspace."""
    if user.is_superuser:
        return True

    membership = db.query(WorkspaceMembership).filter(
        WorkspaceMembership.user_id == user.id,
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.status == "active"
    ).first()

    return membership is not None


def get_user_workspace_role(workspace_id: str, user: User, db: Session) -> WorkspaceRole:
    """Get user's role in a workspace."""
    if user.is_superuser:
        return WorkspaceRole.ADMIN

    membership = db.query(WorkspaceMembership).filter(
        WorkspaceMembership.user_id == user.id,
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.status == "active"
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace"
        )

    return WorkspaceRole(membership.role)
