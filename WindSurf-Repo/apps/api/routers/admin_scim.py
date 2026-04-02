"""Admin endpoints for SCIM provisioning management (tokens, group mappings)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from apps.api.deps_rbac import require_workspace_role
from core.config import get_settings

# from db.models import (
#     User,
#     SCIMToken,
#     WorkspaceRole,
#     SCIMGroup,
#     SCIMGroupWorkspaceRole,
# )
from db.session import get_db

# from db.session import tenant_enforcement_disabled


settings = get_settings()

router = APIRouter(prefix="/admin/scim", tags=["admin-scim"])


def _hash_token(token: str) -> str:
    return hmac.new(settings.secret_key.encode(), token.encode("utf-8"), hashlib.sha256).hexdigest()


class SCIMTokenCreateRequest(BaseModel):
    name: str


class SCIMTokenResponse(BaseModel):
    id: str
    name: str
    is_active: bool


class SCIMTokenCreateResponse(SCIMTokenResponse):
    token: str


class SCIMGroupWorkspaceRoleUpsertRequest(BaseModel):
    scim_group_id: str
    workspace_id: str
    role: str
    is_active: bool = True


class SCIMGroupWorkspaceRoleResponse(BaseModel):
    id: str
    scim_group_id: str
    workspace_id: str
    role: str
    is_active: bool


def _require_org_admin(
    user: User = Depends(get_current_user),
    # TODO: implement WorkspaceRole
    _rbac=Depends(require_workspace_role("ADMIN")),
) -> User:
    return user


@router.get("/tokens", response_model=list[SCIMTokenResponse])
async def list_scim_tokens(
    user: User = Depends(_require_org_admin),
    db: Session = Depends(get_db),
):
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    with tenant_enforcement_disabled():
        rows = (
            db.query(SCIMToken)
            .filter(SCIMToken.organization_id == user.organization_id)
            .order_by(SCIMToken.created_at.desc())
            .all()
        )

    return [SCIMTokenResponse(id=r.id, name=r.name, is_active=r.is_active) for r in rows]


@router.post("/tokens", response_model=SCIMTokenCreateResponse, status_code=201)
async def create_scim_token(
    req: SCIMTokenCreateRequest,
    user: User = Depends(_require_org_admin),
    db: Session = Depends(get_db),
):
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    raw = secrets.token_urlsafe(32)
    row = SCIMToken(
        organization_id=user.organization_id,
        name=req.name,
        token_hash=_hash_token(raw),
        is_active=True,
    )
    with tenant_enforcement_disabled():
        db.add(row)
        db.commit()
        db.refresh(row)

    return SCIMTokenCreateResponse(id=row.id, name=row.name, is_active=row.is_active, token=raw)


@router.post("/tokens/{token_id}/rotate", response_model=SCIMTokenCreateResponse)
async def rotate_scim_token(
    token_id: str,
    user: User = Depends(_require_org_admin),
    db: Session = Depends(get_db),
):
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    raw = secrets.token_urlsafe(32)

    with tenant_enforcement_disabled():
        row = (
            db.query(SCIMToken)
            .filter(SCIMToken.id == token_id, SCIMToken.organization_id == user.organization_id)
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Token not found")

        row.token_hash = _hash_token(raw)
        row.is_active = True
        db.commit()
        db.refresh(row)

    return SCIMTokenCreateResponse(id=row.id, name=row.name, is_active=row.is_active, token=raw)


@router.post("/tokens/{token_id}/revoke", response_model=SCIMTokenResponse)
async def revoke_scim_token(
    token_id: str,
    user: User = Depends(_require_org_admin),
    db: Session = Depends(get_db),
):
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    with tenant_enforcement_disabled():
        row = (
            db.query(SCIMToken)
            .filter(SCIMToken.id == token_id, SCIMToken.organization_id == user.organization_id)
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Token not found")
        row.is_active = False
        db.commit()
        db.refresh(row)

    return SCIMTokenResponse(id=row.id, name=row.name, is_active=row.is_active)


@router.put("/group-workspace-roles", response_model=SCIMGroupWorkspaceRoleResponse)
async def upsert_group_workspace_role(
    req: SCIMGroupWorkspaceRoleUpsertRequest,
    user: User = Depends(_require_org_admin),
    db: Session = Depends(get_db),
):
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # TODO: implement SCIM models
    raise HTTPException(status_code=501, detail="SCIM not implemented")


@router.get("/group-workspace-roles", response_model=list[SCIMGroupWorkspaceRoleResponse])
async def list_group_workspace_roles(
    scim_group_id: Optional[str] = None,
    user: User = Depends(_require_org_admin),
    db: Session = Depends(get_db),
):
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # TODO: implement SCIM models
    raise HTTPException(status_code=501, detail="SCIM not implemented")
