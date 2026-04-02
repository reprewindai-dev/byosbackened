"""SCIM 2.0 provisioning endpoints (baseline)."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Optional, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import get_settings
from db.session import get_db

# from db.session import tenant_enforcement_disabled
# from db.models import (
#     SCIMToken,
#     User,
#     Workspace,
#     WorkspaceMembership,
#     WorkspaceRole,
#     SCIMGroup,
#     SCIMGroupMember,
#     SCIMGroupWorkspaceRole,
# )

settings = get_settings()

router = APIRouter(prefix="/scim/v2", tags=["scim"])


def _hash_token(token: str) -> str:
    return hmac.new(settings.secret_key.encode(), token.encode("utf-8"), hashlib.sha256).hexdigest()


async def get_scim_org_id(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization"
        )
    try:
        scheme, token = authorization.split()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header"
        )
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")

    token_hash = _hash_token(token)
    with tenant_enforcement_disabled():
        row = (
            db.query(SCIMToken)
            .filter(SCIMToken.token_hash == token_hash, SCIMToken.is_active == True)
            .first()
        )
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid SCIM token")
    return row.organization_id


class SCIMName(BaseModel):
    givenName: Optional[str] = None
    familyName: Optional[str] = None


class SCIMUserCreate(BaseModel):
    userName: str
    name: Optional[SCIMName] = None
    active: bool = True


class SCIMGroupMemberRef(BaseModel):
    value: str


class SCIMGroupCreate(BaseModel):
    displayName: str
    externalId: Optional[str] = None
    members: Optional[list[SCIMGroupMemberRef]] = None


def _scim_user_resource(user: User) -> dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": user.id,
        "userName": user.email,
        "active": user.is_active,
        "name": {
            "givenName": user.full_name.split(" ")[0] if user.full_name else None,
            "familyName": (
                " ".join(user.full_name.split(" ")[1:])
                if user.full_name and " " in user.full_name
                else None
            ),
        },
        "meta": {"resourceType": "User"},
    }


def _scim_group_resource(group: SCIMGroup, member_ids: list[str]) -> dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "id": group.id,
        "displayName": group.display_name,
        "externalId": group.external_id,
        "members": [{"value": uid} for uid in member_ids],
        "meta": {"resourceType": "Group"},
    }


def _apply_group_workspace_roles(db: Session, org_id: str, group_id: str, user_id: str) -> None:
    """Ensure a user's workspace memberships align to the group's active workspace-role mappings."""
    rows = (
        db.query(SCIMGroupWorkspaceRole)
        .filter(
            SCIMGroupWorkspaceRole.organization_id == org_id,
            SCIMGroupWorkspaceRole.scim_group_id == group_id,
            SCIMGroupWorkspaceRole.is_active == True,
        )
        .all()
    )
    for r in rows:
        # Validate role is a known enum value; ignore invalid rows to avoid breaking provisioning.
        try:
            role = WorkspaceRole(r.role)
        except Exception:
            continue

        m = (
            db.query(WorkspaceMembership)
            .filter(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.workspace_id == r.workspace_id,
            )
            .first()
        )
        if not m:
            db.add(
                WorkspaceMembership(
                    organization_id=org_id,
                    workspace_id=r.workspace_id,
                    user_id=user_id,
                    role=role,
                    is_active=True,
                )
            )
        else:
            if m.organization_id != org_id:
                continue
            m.role = role
            m.is_active = True


def _resolve_scim_member_user(db: Session, org_id: str, ref_value: str) -> Optional[User]:
    """Resolve SCIM member reference to a user.

    Some IdPs send SCIM Group member `value` as the SCIM user resource `id`.
    Others may send username/email. We accept either.
    """
    if not ref_value:
        return None
    u = db.query(User).filter(User.id == ref_value, User.organization_id == org_id).first()
    if u:
        return u
    return db.query(User).filter(User.email == ref_value, User.organization_id == org_id).first()


@router.get("/ServiceProviderConfig")
async def service_provider_config():
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {"supported": False},
        "bulk": {"supported": False},
        "filter": {"supported": False},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "Bearer Token",
                "description": "SCIM token",
                "specUri": "https://www.rfc-editor.org/rfc/rfc6750",
                "primary": True,
            }
        ],
    }


@router.get("/Users")
async def list_users(
    org_id: str = Depends(get_scim_org_id),
    db: Session = Depends(get_db),
):
    with tenant_enforcement_disabled():
        users = db.query(User).filter(User.organization_id == org_id).all()
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(users),
        "Resources": [_scim_user_resource(u) for u in users],
    }


@router.get("/Users/{user_id}")
async def get_user(
    user_id: str,
    org_id: str = Depends(get_scim_org_id),
    db: Session = Depends(get_db),
):
    with tenant_enforcement_disabled():
        user = db.query(User).filter(User.id == user_id, User.organization_id == org_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return _scim_user_resource(user)


@router.post("/Users", status_code=201)
async def create_user(
    req: SCIMUserCreate,
    org_id: str = Depends(get_scim_org_id),
    db: Session = Depends(get_db),
):
    # Provision into first active workspace in org.
    with tenant_enforcement_disabled():
        ws = (
            db.query(Workspace)
            .filter(Workspace.organization_id == org_id, Workspace.is_active == True)
            .first()
        )
        if not ws:
            raise HTTPException(status_code=400, detail="Organization has no active workspace")

        existing = db.query(User).filter(User.email == req.userName).first()
        if existing:
            # Ensure org linkage + membership exists.
            if existing.organization_id != org_id:
                raise HTTPException(status_code=409, detail="User exists in different organization")
            m = (
                db.query(WorkspaceMembership)
                .filter(
                    WorkspaceMembership.user_id == existing.id,
                    WorkspaceMembership.workspace_id == ws.id,
                )
                .first()
            )
            if not m:
                db.add(
                    WorkspaceMembership(
                        organization_id=org_id,
                        workspace_id=ws.id,
                        user_id=existing.id,
                        role=WorkspaceRole.MEMBER,
                        is_active=True,
                    )
                )
                db.commit()
            return _scim_user_resource(existing)

        full_name = None
        if req.name and (req.name.givenName or req.name.familyName):
            full_name = " ".join([p for p in [req.name.givenName, req.name.familyName] if p])

        user = User(
            id=str(uuid.uuid4()),
            email=req.userName,
            hashed_password="scim-provisioned",  # must be rotated via password reset if using local auth
            full_name=full_name,
            is_active=bool(req.active),
            is_superuser=False,
            organization_id=org_id,
            workspace_id=ws.id,
        )
        db.add(user)
        db.flush()
        db.add(
            WorkspaceMembership(
                organization_id=org_id,
                workspace_id=ws.id,
                user_id=user.id,
                role=WorkspaceRole.MEMBER,
                is_active=True,
            )
        )
        db.commit()
        db.refresh(user)
        return _scim_user_resource(user)


@router.delete("/Users/{user_id}", status_code=204)
async def deprovision_user(
    user_id: str,
    org_id: str = Depends(get_scim_org_id),
    db: Session = Depends(get_db),
):
    with tenant_enforcement_disabled():
        user = db.query(User).filter(User.id == user_id, User.organization_id == org_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_active = False
        db.query(WorkspaceMembership).filter(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.organization_id == org_id,
        ).update({WorkspaceMembership.is_active: False})

        db.commit()
    return None


@router.get("/Groups")
async def list_groups(
    org_id: str = Depends(get_scim_org_id),
    db: Session = Depends(get_db),
):
    with tenant_enforcement_disabled():
        groups = (
            db.query(SCIMGroup)
            .filter(SCIMGroup.organization_id == org_id, SCIMGroup.is_active == True)
            .all()
        )
        resources: list[dict[str, Any]] = []
        for g in groups:
            member_ids = [
                m.user_id
                for m in db.query(SCIMGroupMember)
                .filter(SCIMGroupMember.scim_group_id == g.id)
                .all()
            ]
            resources.append(_scim_group_resource(g, member_ids))
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(resources),
        "Resources": resources,
    }


@router.post("/Groups", status_code=201)
async def create_group(
    req: SCIMGroupCreate,
    org_id: str = Depends(get_scim_org_id),
    db: Session = Depends(get_db),
):
    with tenant_enforcement_disabled():
        g = SCIMGroup(
            organization_id=org_id,
            display_name=req.displayName,
            external_id=req.externalId,
            is_active=True,
        )
        db.add(g)
        db.flush()

        if req.members:
            for m in req.members:
                u = _resolve_scim_member_user(db, org_id=org_id, ref_value=m.value)
                if not u:
                    continue
                db.add(SCIMGroupMember(organization_id=org_id, scim_group_id=g.id, user_id=u.id))
                _apply_group_workspace_roles(db, org_id=org_id, group_id=g.id, user_id=u.id)

        db.commit()
        db.refresh(g)
        member_ids = [
            row.user_id
            for row in db.query(SCIMGroupMember).filter(SCIMGroupMember.scim_group_id == g.id).all()
        ]
        return _scim_group_resource(g, member_ids)


@router.get("/Groups/{group_id}")
async def get_group(
    group_id: str,
    org_id: str = Depends(get_scim_org_id),
    db: Session = Depends(get_db),
):
    with tenant_enforcement_disabled():
        g = (
            db.query(SCIMGroup)
            .filter(SCIMGroup.id == group_id, SCIMGroup.organization_id == org_id)
            .first()
        )
        if not g or not g.is_active:
            raise HTTPException(status_code=404, detail="Group not found")
        member_ids = [
            m.user_id
            for m in db.query(SCIMGroupMember).filter(SCIMGroupMember.scim_group_id == g.id).all()
        ]
        return _scim_group_resource(g, member_ids)


@router.put("/Groups/{group_id}")
async def replace_group(
    group_id: str,
    req: SCIMGroupCreate,
    org_id: str = Depends(get_scim_org_id),
    db: Session = Depends(get_db),
):
    with tenant_enforcement_disabled():
        g = (
            db.query(SCIMGroup)
            .filter(SCIMGroup.id == group_id, SCIMGroup.organization_id == org_id)
            .first()
        )
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")

        g.display_name = req.displayName
        g.external_id = req.externalId
        g.is_active = True

        # Replace membership set.
        db.query(SCIMGroupMember).filter(SCIMGroupMember.scim_group_id == g.id).delete(
            synchronize_session=False
        )
        if req.members:
            for m in req.members:
                u = _resolve_scim_member_user(db, org_id=org_id, ref_value=m.value)
                if not u:
                    continue
                db.add(SCIMGroupMember(organization_id=org_id, scim_group_id=g.id, user_id=u.id))
                _apply_group_workspace_roles(db, org_id=org_id, group_id=g.id, user_id=u.id)

        db.commit()
        db.refresh(g)
        member_ids = [
            row.user_id
            for row in db.query(SCIMGroupMember).filter(SCIMGroupMember.scim_group_id == g.id).all()
        ]
        return _scim_group_resource(g, member_ids)


@router.delete("/Groups/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    org_id: str = Depends(get_scim_org_id),
    db: Session = Depends(get_db),
):
    with tenant_enforcement_disabled():
        g = (
            db.query(SCIMGroup)
            .filter(SCIMGroup.id == group_id, SCIMGroup.organization_id == org_id)
            .first()
        )
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        g.is_active = False
        db.query(SCIMGroupMember).filter(SCIMGroupMember.scim_group_id == g.id).delete(
            synchronize_session=False
        )
        db.commit()
    return None
