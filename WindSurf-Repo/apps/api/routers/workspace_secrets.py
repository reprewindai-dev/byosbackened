"""Workspace BYOK secrets management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.security.workspace_secrets import get_workspace_secrets_service

router = APIRouter(prefix="/workspace-secrets", tags=["workspace-secrets"])
secrets_service = get_workspace_secrets_service()


class SetSecretRequest(BaseModel):
    provider: str
    secret_name: str = "api_key"
    value: str
    is_active: bool = True


class DeleteSecretRequest(BaseModel):
    provider: str
    secret_name: str = "api_key"


@router.post("", status_code=status.HTTP_201_CREATED)
async def set_workspace_secret(
    request: SetSecretRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Create or update a workspace secret (encrypted at rest)."""
    secret = secrets_service.set_secret(
        db=db,
        workspace_id=workspace_id,
        provider=request.provider,
        secret_name=request.secret_name,
        value=request.value,
        is_active=request.is_active,
    )
    return {
        "id": secret.id,
        "workspace_id": secret.workspace_id,
        "provider": secret.provider,
        "secret_name": secret.secret_name,
        "is_active": secret.is_active,
        "updated_at": secret.updated_at.isoformat(),
    }


@router.get("")
async def list_workspace_secrets(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List workspace secrets (does not return values)."""
    from db.models.workspace_secret import WorkspaceSecret

    secrets = (
        db.query(WorkspaceSecret)
        .filter(WorkspaceSecret.workspace_id == workspace_id)
        .order_by(WorkspaceSecret.provider.asc(), WorkspaceSecret.secret_name.asc())
        .all()
    )

    return [
        {
            "id": s.id,
            "provider": s.provider,
            "secret_name": s.secret_name,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in secrets
    ]


@router.delete("")
async def delete_workspace_secret(
    request: DeleteSecretRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Delete a workspace secret."""
    deleted = secrets_service.delete_secret(
        db=db,
        workspace_id=workspace_id,
        provider=request.provider,
        secret_name=request.secret_name,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    return {"deleted": True}
