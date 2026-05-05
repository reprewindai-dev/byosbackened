"""Admin router: workspace management, user management, system-wide controls (superuser/admin only)."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from apps.api.deps import require_admin, require_superuser
from core.security import get_password_hash
from core.services.status_updates import notify_status_subscribers
from db.session import get_db
from db.models import (
    User, UserRole, UserStatus,
    Workspace, Subscription,
    SecurityEvent, Job, AIAuditLog,
    IncidentLog, IncidentSeverity, IncidentStatus,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    user_count: int
    plan: Optional[str]
    subscription_status: Optional[str]
    created_at: str


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class UserAdminResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    status: str
    is_superuser: bool
    mfa_enabled: bool
    workspace_id: str
    last_login: Optional[str]
    created_at: str


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    workspace_id: str


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None


class StatusIncidentCreate(BaseModel):
    title: str
    description: str
    severity: str = "medium"
    incident_type: str = "system"
    status: str = "investigating"


# ─── Workspace Management (admin within workspace, superuser global) ───────────

@router.get("/workspaces", response_model=List[WorkspaceResponse])
async def list_workspaces(
    skip: int = 0,
    limit: int = Query(50, le=200),
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    """List all workspaces (superuser only)."""
    workspaces = db.query(Workspace).order_by(desc(Workspace.created_at)).offset(skip).limit(limit).all()
    result = []
    for ws in workspaces:
        user_count = db.query(func.count(User.id)).filter(User.workspace_id == ws.id).scalar() or 0
        sub = db.query(Subscription).filter(Subscription.workspace_id == ws.id).first()
        result.append(WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            slug=ws.slug,
            is_active=ws.is_active,
            user_count=user_count,
            plan=sub.plan.value if sub else None,
            subscription_status=sub.status.value if sub else None,
            created_at=ws.created_at.isoformat(),
        ))
    return result


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get workspace details. Admins can only view their own workspace."""
    target_id = workspace_id
    if not current_user.is_superuser and target_id != current_user.workspace_id:
        raise HTTPException(status_code=403, detail="Cannot access other workspaces")
    ws = db.query(Workspace).filter(Workspace.id == target_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    user_count = db.query(func.count(User.id)).filter(User.workspace_id == ws.id).scalar() or 0
    sub = db.query(Subscription).filter(Subscription.workspace_id == ws.id).first()
    return WorkspaceResponse(
        id=ws.id, name=ws.name, slug=ws.slug, is_active=ws.is_active,
        user_count=user_count,
        plan=sub.plan.value if sub else None,
        subscription_status=sub.status.value if sub else None,
        created_at=ws.created_at.isoformat(),
    )


@router.patch("/workspaces/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    payload: WorkspaceUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not current_user.is_superuser and workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=403, detail="Cannot modify other workspaces")
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if payload.name is not None:
        ws.name = payload.name
    if payload.is_active is not None:
        ws.is_active = payload.is_active
    db.commit()
    return {"message": "Workspace updated"}


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    """Hard-delete workspace and all data (superuser only)."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    db.delete(ws)
    db.commit()


# ─── User Management ──────────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserAdminResponse])
async def list_users(
    skip: int = 0,
    limit: int = Query(50, le=200),
    workspace_id: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List users. Admins see their workspace only; superusers can filter by any workspace."""
    q = db.query(User).order_by(desc(User.created_at))
    if current_user.is_superuser and workspace_id:
        q = q.filter(User.workspace_id == workspace_id)
    elif not current_user.is_superuser:
        q = q.filter(User.workspace_id == current_user.workspace_id)
    users = q.offset(skip).limit(limit).all()
    return [
        UserAdminResponse(
            id=u.id, email=u.email, full_name=u.full_name,
            role=u.role.value, status=u.status.value,
            is_superuser=u.is_superuser, mfa_enabled=u.mfa_enabled,
            workspace_id=u.workspace_id,
            last_login=u.last_login.isoformat() if u.last_login else None,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]


@router.post("/users", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a user in a workspace (admin creates in own workspace, superuser in any)."""
    target_ws = payload.workspace_id
    if not current_user.is_superuser and target_ws != current_user.workspace_id:
        raise HTTPException(status_code=403, detail="Cannot create users in other workspaces")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        workspace_id=target_ws,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserAdminResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role.value, status=user.status.value,
        is_superuser=user.is_superuser, mfa_enabled=user.mfa_enabled,
        workspace_id=user.workspace_id, last_login=None,
        created_at=user.created_at.isoformat(),
    )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not current_user.is_superuser and user.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=403, detail="Cannot modify users in other workspaces")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.status is not None:
        user.status = payload.status
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    return {"message": "User updated"}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not current_user.is_superuser and user.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=403, detail="Cannot delete users in other workspaces")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db.delete(user)
    db.commit()


# Public Status Operations (superuser only)

@router.post("/status/incidents", status_code=status.HTTP_201_CREATED)
async def create_status_incident(
    payload: StatusIncidentCreate,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    """Create a public status incident and notify status subscribers."""
    title = (payload.title or "").strip()
    description = (payload.description or "").strip()
    if len(title) < 3:
        raise HTTPException(status_code=400, detail="Title must be at least 3 characters")
    if len(description) < 10:
        raise HTTPException(status_code=400, detail="Description must be at least 10 characters")

    try:
        severity = IncidentSeverity(payload.severity.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Severity must be one of {[item.value for item in IncidentSeverity]}",
        ) from exc

    try:
        incident_status = IncidentStatus(payload.status.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of {[item.value for item in IncidentStatus]}",
        ) from exc

    incident = IncidentLog(
        workspace_id=None,
        incident_type=(payload.incident_type or "system").strip().lower()[:80],
        severity=severity,
        status=incident_status,
        title=title,
        description=description,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    delivery = await notify_status_subscribers(
        db,
        event_type="incident",
        title=incident.title,
        description=incident.description,
        severity=incident.severity.value,
        status=incident.status.value,
        url=f"https://veklom.com/status#{incident.id}",
    )

    return {
        "id": incident.id,
        "title": incident.title,
        "severity": incident.severity.value,
        "status": incident.status.value,
        "created_at": incident.created_at.isoformat(),
        "delivery": delivery,
    }


# System Overview (superuser)

@router.get("/overview")
async def system_overview(
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    """Platform-wide stats for superuser admin dashboard."""
    total_workspaces = db.query(func.count(Workspace.id)).scalar() or 0
    active_workspaces = db.query(func.count(Workspace.id)).filter(Workspace.is_active.is_(True)).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_jobs = db.query(func.count(Job.id)).scalar() or 0
    total_ai_ops = db.query(func.count(AIAuditLog.id)).scalar() or 0

    ai_cost = db.query(func.sum(AIAuditLog.cost)).scalar()
    total_ai_cost = float(ai_cost or 0)

    open_threats = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.status == "open"
    ).scalar() or 0

    by_plan = {}
    plan_rows = db.query(Subscription.plan, func.count()).group_by(Subscription.plan).all()
    for plan, count in plan_rows:
        by_plan[plan.value if plan else "none"] = count

    return {
        "workspaces": {"total": total_workspaces, "active": active_workspaces},
        "users": {"total": total_users},
        "jobs": {"total": total_jobs},
        "ai_operations": {"total": total_ai_ops, "total_cost_usd": round(total_ai_cost, 4)},
        "security": {"open_threats": open_threats},
        "subscriptions": {"by_plan": by_plan},
        "timestamp": datetime.utcnow().isoformat(),
    }
