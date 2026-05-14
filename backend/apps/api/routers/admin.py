"""Admin router: workspace management, user management, system-wide controls (superuser/admin only)."""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from apps.api.deps import require_admin, require_superuser
from core.security import get_password_hash
from core.services.financial_analytics import platform_financial_overview
from core.services.status_updates import notify_status_subscribers
from db.session import get_db
from db.models import (
    User, UserRole, UserStatus,
    Workspace, Subscription,
    SecurityEvent, SecurityAuditLog, Job, AIAuditLog,
    IncidentLog, IncidentSeverity, IncidentStatus,
    CommercialArtifact, ProductUsageEvent, SignupLead, UserSession, WorkspaceRequestLog,
    APIKey, Deployment, Export, Pipeline, PipelineRun,
    WorkspaceGithubRepoSelection, WorkspaceInvite,
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


class LiveOccupantResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    role: str
    is_superuser: bool
    session_id: str
    last_accessed: str
    expires_at: str
    ip_address: Optional[str]


class LiveWorkspaceResponse(BaseModel):
    workspace_id: str
    workspace_name: str
    workspace_slug: str
    is_active: bool
    active_session_count: int
    active_user_count: int
    recent_requests_15m: int
    failed_requests_15m: int
    last_request_at: Optional[str]
    last_error_at: Optional[str]
    current_status: str
    occupants: List[LiveOccupantResponse]


class LiveOpsSummaryResponse(BaseModel):
    generated_at: str
    active_tenants: int
    open_rooms: int
    live_users: int
    live_sessions: int
    degraded_workspaces: int
    workspaces: List[LiveWorkspaceResponse]


class AcquisitionUsageRow(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    workspace_id: str
    workspace_name: str
    workspace_slug: str
    signup_type: str
    source: str
    created_at: str
    last_login: Optional[str]
    last_activity: Optional[str]
    requests_14d: int
    failed_requests_14d: int
    tokens_14d: int
    cost_14d_usd: float
    last_request_at: Optional[str]
    top_paths: list[dict]
    top_models: list[dict]
    page_views_14d: int
    active_minutes_14d: float
    top_surfaces: list[dict]
    last_seen_route: Optional[str]
    converted: bool
    conversion_signal: str


class AcquisitionUsageSummary(BaseModel):
    generated_at: str
    window_days: int
    total_signups: int
    signups_in_window: int
    active_users_in_window: int
    zero_usage_in_window: int
    converted_in_window: int
    conversion_rate_pct: float
    leads: List[AcquisitionUsageRow]


class CommercialScorecardSummary(BaseModel):
    generated_at: str
    window_days: int
    vertical_demos_generated: int
    gpc_handoffs_prepared: int
    founder_reviewed_vertical_artifacts: int
    evaluation_conversations_influenced_by_vertical_demo: int
    targets_14d: dict
    over_the_bar: dict


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


# Platform Financials (superuser)

@router.get("/financials")
async def get_platform_financials(
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    """Platform financial KPIs: MRR, ARR, churn, cost, usage — superuser only."""
    return platform_financial_overview(db=db)


@router.get("/live-ops", response_model=LiveOpsSummaryResponse)
async def live_ops_snapshot(
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    """Live owner-only operator snapshot across tenant rooms and sessions."""
    now = datetime.utcnow()
    active_since = now - timedelta(minutes=15)

    active_sessions = (
        db.query(UserSession, User, Workspace)
        .join(User, User.id == UserSession.user_id)
        .join(Workspace, Workspace.id == User.workspace_id)
        .filter(
            UserSession.is_active.is_(True),
            UserSession.expires_at > now,
            UserSession.last_accessed >= active_since,
            User.is_active.is_(True),
        )
        .order_by(UserSession.last_accessed.desc())
        .all()
    )

    recent_request_rows = (
        db.query(
            WorkspaceRequestLog.workspace_id.label("workspace_id"),
            func.count(WorkspaceRequestLog.id).label("recent_requests"),
            func.max(WorkspaceRequestLog.created_at).label("last_request_at"),
        )
        .filter(WorkspaceRequestLog.created_at >= active_since)
        .group_by(WorkspaceRequestLog.workspace_id)
        .all()
    )
    recent_requests_by_workspace = {
        row.workspace_id: {
            "recent_requests": int(row.recent_requests or 0),
            "last_request_at": row.last_request_at,
        }
        for row in recent_request_rows
    }

    failed_request_rows = (
        db.query(
            WorkspaceRequestLog.workspace_id.label("workspace_id"),
            func.count(WorkspaceRequestLog.id).label("failed_requests"),
            func.max(WorkspaceRequestLog.created_at).label("last_error_at"),
        )
        .filter(
            WorkspaceRequestLog.created_at >= active_since,
            WorkspaceRequestLog.status.notin_(["success", "ok", "200", "completed", "succeeded"]),
        )
        .group_by(WorkspaceRequestLog.workspace_id)
        .all()
    )
    failed_requests_by_workspace = {
        row.workspace_id: {
            "failed_requests": int(row.failed_requests or 0),
            "last_error_at": row.last_error_at,
        }
        for row in failed_request_rows
    }

    workspace_map: dict[str, LiveWorkspaceResponse] = {}
    for session, user, workspace in active_sessions:
        entry = workspace_map.get(workspace.id)
        if entry is None:
            request_meta = recent_requests_by_workspace.get(workspace.id, {})
            failure_meta = failed_requests_by_workspace.get(workspace.id, {})
            entry = LiveWorkspaceResponse(
                workspace_id=workspace.id,
                workspace_name=workspace.name,
                workspace_slug=workspace.slug,
                is_active=bool(workspace.is_active),
                active_session_count=0,
                active_user_count=0,
                recent_requests_15m=int(request_meta.get("recent_requests", 0)),
                failed_requests_15m=int(failure_meta.get("failed_requests", 0)),
                last_request_at=request_meta.get("last_request_at").isoformat() if request_meta.get("last_request_at") else None,
                last_error_at=failure_meta.get("last_error_at").isoformat() if failure_meta.get("last_error_at") else None,
                current_status="live",
                occupants=[],
            )
            workspace_map[workspace.id] = entry

        entry.active_session_count += 1
        entry.occupants.append(
            LiveOccupantResponse(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                is_superuser=bool(user.is_superuser),
                session_id=session.id,
                last_accessed=session.last_accessed.isoformat(),
                expires_at=session.expires_at.isoformat(),
                ip_address=session.ip_address,
            )
        )

    for entry in workspace_map.values():
        entry.active_user_count = len({occupant.user_id for occupant in entry.occupants})
        if entry.failed_requests_15m > 0:
            entry.current_status = "degraded"
        elif entry.recent_requests_15m == 0:
            entry.current_status = "idle"

    return LiveOpsSummaryResponse(
        generated_at=now.isoformat(),
        active_tenants=len(workspace_map),
        open_rooms=len(workspace_map),
        live_users=len({user.id for _, user, _ in active_sessions}),
        live_sessions=len(active_sessions),
        degraded_workspaces=sum(1 for entry in workspace_map.values() if entry.current_status == "degraded"),
        workspaces=sorted(
            workspace_map.values(),
            key=lambda entry: (
                0 if entry.current_status == "degraded" else 1,
                -entry.active_session_count,
                -(entry.recent_requests_15m or 0),
                entry.workspace_name.lower(),
            ),
        ),
    )


@router.get("/acquisition", response_model=AcquisitionUsageSummary)
async def acquisition_usage_snapshot(
    days: int = Query(14, ge=1, le=90),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    """Owner-only signup and usage ledger for conversion diagnostics."""
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    users = (
        db.query(User, Workspace)
        .join(Workspace, Workspace.id == User.workspace_id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .all()
    )
    user_ids = [user.id for user, _ in users]
    workspace_ids = [workspace.id for _, workspace in users]

    leads = {}
    if user_ids:
        lead_rows = (
            db.query(SignupLead)
            .filter(SignupLead.user_id.in_(user_ids))
            .order_by(SignupLead.created_at.desc())
            .all()
        )
        for lead in lead_rows:
            leads.setdefault(lead.user_id, lead)

    subscriptions = {}
    if workspace_ids:
        for sub in db.query(Subscription).filter(Subscription.workspace_id.in_(workspace_ids)).all():
            subscriptions[sub.workspace_id] = sub

    rows: list[AcquisitionUsageRow] = []
    for user, workspace in users:
        request_query = db.query(WorkspaceRequestLog).filter(
            WorkspaceRequestLog.workspace_id == workspace.id,
            WorkspaceRequestLog.created_at >= start,
            WorkspaceRequestLog.created_at <= now,
        )
        user_request_query = request_query.filter(
            (WorkspaceRequestLog.user_id == user.id) | (WorkspaceRequestLog.user_id.is_(None))
        )
        requests_14d = user_request_query.count()
        failed_requests_14d = user_request_query.filter(
            WorkspaceRequestLog.status.notin_(["success", "ok", "200", "completed", "succeeded"])
        ).count()
        totals = user_request_query.with_entities(
            func.coalesce(func.sum(WorkspaceRequestLog.tokens_in + WorkspaceRequestLog.tokens_out), 0),
            func.coalesce(func.sum(WorkspaceRequestLog.cost_usd), 0),
            func.max(WorkspaceRequestLog.created_at),
        ).first()
        top_paths = [
            {"path": path or "unknown", "requests": int(count or 0)}
            for path, count in (
                user_request_query.with_entities(
                    WorkspaceRequestLog.request_path,
                    func.count(WorkspaceRequestLog.id),
                )
                .group_by(WorkspaceRequestLog.request_path)
                .order_by(func.count(WorkspaceRequestLog.id).desc())
                .limit(5)
                .all()
            )
        ]
        top_models = [
            {"model": model or "unknown", "requests": int(count or 0)}
            for model, count in (
                user_request_query.with_entities(
                    WorkspaceRequestLog.model,
                    func.count(WorkspaceRequestLog.id),
                )
                .group_by(WorkspaceRequestLog.model)
                .order_by(func.count(WorkspaceRequestLog.id).desc())
                .limit(5)
                .all()
            )
        ]
        usage_query = db.query(ProductUsageEvent).filter(
            ProductUsageEvent.user_id == user.id,
            ProductUsageEvent.created_at >= start,
            ProductUsageEvent.created_at <= now,
        )
        page_views = usage_query.filter(ProductUsageEvent.event_type == "page_view").count()
        duration_total = usage_query.with_entities(func.coalesce(func.sum(ProductUsageEvent.duration_ms), 0)).scalar() or 0
        top_surfaces = [
            {"surface": surface or "unknown", "events": int(count or 0)}
            for surface, count in (
                usage_query.with_entities(ProductUsageEvent.surface, func.count(ProductUsageEvent.id))
                .group_by(ProductUsageEvent.surface)
                .order_by(func.count(ProductUsageEvent.id).desc())
                .limit(5)
                .all()
            )
        ]
        last_usage = usage_query.order_by(ProductUsageEvent.created_at.desc()).first()
        sub = subscriptions.get(workspace.id)
        sub_status = getattr(getattr(sub, "status", None), "value", getattr(sub, "status", None))
        converted = bool(
            sub_status in {"active", "trialing"}
            or (workspace.license_tier and workspace.license_tier.lower() not in {"free", "free_evaluation", "trial"})
        )
        conversion_signal = (
            f"subscription:{sub_status}" if sub_status else
            f"license:{workspace.license_tier}" if workspace.license_tier else
            "no paid conversion signal"
        )
        lead = leads.get(user.id)
        last_request_at = totals[2] if totals else None
        rows.append(
            AcquisitionUsageRow(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name or (lead.full_name if lead else None),
                workspace_id=workspace.id,
                workspace_name=workspace.name,
                workspace_slug=workspace.slug,
                signup_type=(lead.signup_type if lead else "account"),
                source=(lead.source if lead else "users_table"),
                created_at=user.created_at.isoformat(),
                last_login=user.last_login.isoformat() if user.last_login else None,
                last_activity=(
                    max(filter(None, [user.last_activity, last_request_at]), default=None).isoformat()
                    if any([user.last_activity, last_request_at])
                    else None
                ),
                requests_14d=requests_14d,
                failed_requests_14d=failed_requests_14d,
                tokens_14d=int(totals[0] or 0) if totals else 0,
                cost_14d_usd=float(totals[1] or 0) if totals else 0.0,
                last_request_at=last_request_at.isoformat() if last_request_at else None,
                top_paths=top_paths,
                top_models=top_models,
                page_views_14d=page_views,
                active_minutes_14d=round(float(duration_total or 0) / 60000, 2),
                top_surfaces=top_surfaces,
                last_seen_route=last_usage.route if last_usage else None,
                converted=converted,
                conversion_signal=conversion_signal,
            )
        )

    window_rows = [row for row in rows if datetime.fromisoformat(row.created_at) >= start]
    active_users = [row for row in window_rows if row.requests_14d > 0 or row.last_login]
    zero_usage = [row for row in window_rows if row.requests_14d == 0]
    converted_rows = [row for row in window_rows if row.converted]
    conversion_rate = (len(converted_rows) / len(window_rows) * 100) if window_rows else 0.0

    return AcquisitionUsageSummary(
        generated_at=now.isoformat(),
        window_days=days,
        total_signups=db.query(func.count(User.id)).scalar() or 0,
        signups_in_window=len(window_rows),
        active_users_in_window=len(active_users),
        zero_usage_in_window=len(zero_usage),
        converted_in_window=len(converted_rows),
        conversion_rate_pct=round(conversion_rate, 2),
        leads=rows,
    )


@router.get("/commercial-scorecard", response_model=CommercialScorecardSummary)
async def commercial_scorecard_snapshot(
    days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    usage_query = db.query(ProductUsageEvent).filter(
        ProductUsageEvent.created_at >= start,
        ProductUsageEvent.created_at <= now,
    )
    artifact_query = db.query(CommercialArtifact).filter(
        CommercialArtifact.created_at >= start,
        CommercialArtifact.created_at <= now,
    )
    return CommercialScorecardSummary(
        generated_at=now.isoformat(),
        window_days=days,
        vertical_demos_generated=usage_query.filter(
            ProductUsageEvent.event_type == "feature_use",
            ProductUsageEvent.feature == "vertical_demo_generated",
        ).count(),
        gpc_handoffs_prepared=usage_query.filter(
            ProductUsageEvent.event_type == "feature_use",
            ProductUsageEvent.feature == "gpc_handoff_prepared",
        ).count(),
        founder_reviewed_vertical_artifacts=artifact_query.filter(
            CommercialArtifact.founder_review_status != "pending_founder_review"
        ).count(),
        evaluation_conversations_influenced_by_vertical_demo=usage_query.filter(
            ProductUsageEvent.event_type == "feature_use",
            ProductUsageEvent.feature == "evaluation_conversation_influenced_by_vertical_demo",
        ).count(),
        targets_14d={
            "qualified_evaluation_conversations": 3,
            "serious_byos_private_backend_access_requests": 1,
            "credible_vendor_tool_conversations": 1,
            "approved_package_concepts": 3,
            "founder_approved_public_community_interactions": 10,
        },
        over_the_bar={
            "signed_evaluation_agreements": 1,
            "paid_pilot_or_operating_reserve_funded": 1,
            "technical_procurement_processes_started": 1,
            "credible_vendor_tool_committed": 1,
        },
    )


# --- Founder Command Center -------------------------------------------------

COMMAND_CENTER_MODULES: Dict[str, Dict[str, Any]] = {
    "overview": {
        "title": "Overview",
        "route": "/overview",
        "events": ["overview_view", "overview_center_view"],
    },
    "playground": {
        "title": "Playground Intelligence",
        "route": "/playground",
        "events": [
            "playground_session",
            "scenario_selected",
            "compile_with_gpc_clicked",
            "audit_export_clicked",
            "github_repo_context_used",
        ],
    },
    "gpc": {
        "title": "GPC Intelligence",
        "route": "/uacp",
        "events": [
            "gpc_view",
            "gpc_paid_gate_hit",
            "gpc_handoff_prepared",
            "handoff_preview_opened",
            "handoff_exported",
            "handoff_abandoned",
        ],
    },
    "marketplace": {
        "title": "Marketplace Intelligence",
        "route": "/marketplace",
        "events": [
            "marketplace_view",
            "listing_viewed",
            "listing_clicked",
            "listing_purchased",
            "marketplace_search",
            "empty_marketplace_search",
            "vendor_listing_clicked",
        ],
    },
    "models": {
        "title": "Models Intelligence",
        "route": "/models",
        "events": ["model_viewed", "model_deploy_clicked", "model_selected_in_playground", "model_deploy_failed"],
    },
    "pipelines": {
        "title": "Pipelines Intelligence",
        "route": "/pipelines",
        "events": [
            "pipeline_created",
            "pipeline_template_used",
            "pipeline_node_added",
            "policy_gate_node_used",
            "retrieval_node_used",
            "tool_node_used",
            "pipeline_test_run",
            "deploy_as_endpoint_clicked",
            "pipeline_test_failed",
        ],
    },
    "deployments": {
        "title": "Deployments Intelligence",
        "route": "/deployments",
        "events": [
            "endpoint_created",
            "endpoint_view",
            "sdk_copy_clicked",
            "api_key_created",
            "webhook_setup",
            "rate_limit_hit",
            "endpoint_error",
        ],
    },
    "vault": {
        "title": "Vault Intelligence",
        "route": "/vault",
        "events": [
            "secret_created",
            "secret_rotated",
            "runtime_injection_enabled",
            "hsm_seal_status_viewed",
            "egress_allowlist_status_viewed",
            "dangerous_secret_event",
        ],
    },
    "compliance": {
        "title": "Compliance Intelligence",
        "route": "/compliance",
        "events": [
            "compliance_view",
            "framework_viewed",
            "evidence_exported",
            "auditor_package_downloaded",
            "control_inspected",
            "control_failed",
            "scheduled_export_configured",
        ],
    },
    "monitoring": {
        "title": "Monitoring Intelligence",
        "route": "/monitoring",
        "events": [
            "monitoring_view",
            "alert_configured",
            "logs_searched",
            "latency_panel_viewed",
            "audit_chain_viewed",
            "error_spike",
        ],
    },
    "billing": {
        "title": "Billing Intelligence",
        "route": "/billing",
        "events": [
            "billing_view",
            "upgrade_clicked",
            "invoice_downloaded",
            "plan_changed",
            "reserve_funded",
            "failed_payment",
            "cap_hit",
        ],
    },
    "team_access": {
        "title": "Team / Access Intelligence",
        "route": "/team",
        "events": [
            "team_invite_sent",
            "role_created",
            "mfa_enabled",
            "mfa_disabled",
            "sso_configured",
            "scim_configured",
            "github_oauth_enabled",
            "session_timeout_changed",
            "access_changed",
        ],
    },
    "settings_integrations": {
        "title": "Settings / Integrations Intelligence",
        "route": "/settings",
        "events": [
            "routing_changed",
            "security_changed",
            "data_residency_changed",
            "integration_enabled",
            "github_enabled",
            "slack_enabled",
            "pagerduty_enabled",
            "datadog_enabled",
            "dangerous_action",
            "workspace_region_changed",
        ],
    },
    "github": {
        "title": "GitHub Intelligence",
        "route": "/settings",
        "events": [
            "github_connect",
            "github_disconnect",
            "github_repos_fetched",
            "github_repo_selected",
            "github_repo_context_used",
            "github_context_sent_to_gpc",
            "github_oauth_failure",
            "github_permission_error",
        ],
    },
    "risk_trust": {
        "title": "Risk & Trust",
        "route": "/monitoring",
        "events": [
            "policy_block",
            "unsafe_claim_attempt",
            "external_fallback_block",
            "phi_redaction",
            "pii_redaction",
            "evidence_exported",
            "github_token_error",
            "vault_rotation",
            "tenant_isolation_warning",
        ],
    },
}

COMMAND_CENTER_FUNNEL = [
    ("visit", "Product visit", {"event_types": ["page_view"]}),
    ("signup", "Signup", {"model": "users"}),
    ("workspace_created", "Workspace created", {"model": "workspaces"}),
    ("playground_used", "Playground used", {"routes": ["/playground"], "surfaces": ["playground"]}),
    ("gpc_handoff_prepared", "GPC handoff prepared", {"features": ["gpc_handoff_prepared"]}),
    ("pipeline_created", "Pipeline created", {"model": "pipelines"}),
    ("deployment_attempted", "Deployment attempted", {"features": ["model_deploy_clicked", "deploy_as_endpoint_clicked"]}),
    ("evidence_exported", "Evidence exported", {"features": ["evidence_exported", "audit_export_clicked"]}),
    ("billing_viewed", "Billing viewed", {"routes": ["/billing"], "surfaces": ["billing"]}),
    ("trial_started", "Trial started", {"subscription_statuses": ["trialing"]}),
    ("backend_access_requested", "Backend/private access requested", {"features": ["backend_access_requested", "private_backend_access_requested"]}),
    ("paid_or_reserve_funded", "Paid/reserve funded", {"features": ["reserve_funded"], "subscription_statuses": ["active"]}),
]


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value else None


def _json_loads(value: Any, fallback: Any = None) -> Any:
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _not_wired(metric: str, route_or_event: str) -> Dict[str, Any]:
    return {"metric": metric, "value": None, "status": "not_wired", "needs": route_or_event}


def _metric(metric: str, value: Any, status: str = "wired", detail: Optional[str] = None) -> Dict[str, Any]:
    row: Dict[str, Any] = {"metric": metric, "value": value, "status": status}
    if detail:
        row["detail"] = detail
    return row


def _usage_query(db: Session, start: datetime, end: datetime):
    return db.query(ProductUsageEvent).filter(
        ProductUsageEvent.created_at >= start,
        ProductUsageEvent.created_at <= end,
    )


def _usage_count(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    event_types: Optional[List[str]] = None,
    surfaces: Optional[List[str]] = None,
    routes: Optional[List[str]] = None,
    features: Optional[List[str]] = None,
) -> int:
    query = _usage_query(db, start, end)
    if event_types:
        query = query.filter(ProductUsageEvent.event_type.in_(event_types))
    if surfaces:
        query = query.filter(ProductUsageEvent.surface.in_(surfaces))
    if routes:
        query = query.filter(ProductUsageEvent.route.in_(routes))
    if features:
        query = query.filter(ProductUsageEvent.feature.in_(features))
    return query.count()


def _feature_count(db: Session, start: datetime, end: datetime, features: List[str]) -> int:
    return _usage_count(db, start, end, features=features)


def _record_command_center_access(
    db: Session,
    current_user: User,
    route: str,
) -> None:
    db.add(
        SecurityAuditLog(
            workspace_id=current_user.workspace_id,
            user_id=current_user.id,
            event_type="command_center_access",
            event_category="superuser_control",
            success=True,
            details=json.dumps({"route": route, "redaction": "raw_prompts_and_repo_contents_omitted"}),
        )
    )
    db.commit()


def _workspace_label(workspaces: Dict[str, Workspace], workspace_id: Optional[str]) -> str:
    if not workspace_id or workspace_id not in workspaces:
        return "unknown"
    return workspaces[workspace_id].name


def _build_usage_section(db: Session, start: datetime, end: datetime) -> Dict[str, Any]:
    rows = [
        _metric("Overview views", _usage_count(db, start, end, routes=["/overview"], surfaces=["overview"])),
        _metric("Playground sessions", _usage_count(db, start, end, routes=["/playground"], surfaces=["playground"])),
        _metric("GPC clicks", _feature_count(db, start, end, ["compile_with_gpc_clicked", "gpc_view", "gpc_paid_gate_hit"])),
        _metric("GPC handoffs prepared", _feature_count(db, start, end, ["gpc_handoff_prepared"])),
        _metric("Marketplace views", _usage_count(db, start, end, routes=["/marketplace"], surfaces=["marketplace"])),
        _metric("Model deploy clicks", _feature_count(db, start, end, ["model_deploy_clicked"])),
        _metric("Pipeline builds", db.query(Pipeline).filter(Pipeline.created_at >= start, Pipeline.created_at <= end).count()),
        _metric("Deployment attempts", _feature_count(db, start, end, ["model_deploy_clicked", "deploy_as_endpoint_clicked"])),
        _metric("Vault secrets created", _feature_count(db, start, end, ["secret_created"])),
        _metric("Compliance exports", _feature_count(db, start, end, ["evidence_exported", "auditor_package_downloaded"])),
        _metric("Monitoring views", _usage_count(db, start, end, routes=["/monitoring"], surfaces=["monitoring"])),
        _metric("Billing views", _usage_count(db, start, end, routes=["/billing"], surfaces=["billing"])),
        _metric("Team invites", db.query(WorkspaceInvite).filter(WorkspaceInvite.created_at >= start, WorkspaceInvite.created_at <= end).count()),
        _metric("Settings changes", _feature_count(db, start, end, ["routing_changed", "security_changed", "data_residency_changed", "integration_enabled"])),
    ]
    return {"title": "Usage", "window": {"start": start.isoformat(), "end": end.isoformat()}, "metrics": rows}


def _build_funnel_section(db: Session, start: datetime, end: datetime) -> Dict[str, Any]:
    counts: List[Dict[str, Any]] = []
    previous: Optional[int] = None
    for key, label, spec in COMMAND_CENTER_FUNNEL:
        if spec.get("model") == "users":
            value = db.query(User).filter(User.created_at >= start, User.created_at <= end).count()
        elif spec.get("model") == "workspaces":
            value = db.query(Workspace).filter(Workspace.created_at >= start, Workspace.created_at <= end).count()
        elif spec.get("model") == "pipelines":
            value = db.query(Pipeline).filter(Pipeline.created_at >= start, Pipeline.created_at <= end).count()
        else:
            value = _usage_count(
                db,
                start,
                end,
                event_types=spec.get("event_types"),
                surfaces=spec.get("surfaces"),
                routes=spec.get("routes"),
                features=spec.get("features"),
            )
            statuses = spec.get("subscription_statuses")
            if statuses:
                sub_count = db.query(Subscription).filter(Subscription.status.in_(statuses)).count()
                value = max(value, sub_count)
        conversion = round((value / previous * 100), 2) if previous and previous > 0 else None
        counts.append({"key": key, "label": label, "value": value, "conversion_from_prior_pct": conversion})
        previous = value
    return {"title": "Funnel", "steps": counts}


def _build_verticals_section(db: Session, start: datetime, end: datetime) -> Dict[str, Any]:
    workspace_rows = db.query(Workspace).all()
    rows: List[Dict[str, Any]] = []
    for industry in [
        "banking_fintech",
        "healthcare_hospital",
        "insurance",
        "legal_compliance",
        "government_public_sector",
        "enterprise_operations",
        "generic",
    ]:
        ids = [workspace.id for workspace in workspace_rows if (workspace.industry or "generic") == industry]
        usage = _usage_query(db, start, end).filter(ProductUsageEvent.workspace_id.in_(ids)) if ids else None
        top_scenarios = []
        common_evidence = []
        common_blocks = []
        if usage is not None:
            scenario_counts: Dict[str, int] = {}
            evidence_counts: Dict[str, int] = {}
            block_counts: Dict[str, int] = {}
            for event in usage.all():
                meta = _json_loads(event.metadata_json, {}) or {}
                scenario = meta.get("scenario_title") or meta.get("scenario_id")
                if scenario:
                    scenario_counts[str(scenario)] = scenario_counts.get(str(scenario), 0) + 1
                for item in meta.get("evidence_requirements") or []:
                    evidence_counts[str(item)] = evidence_counts.get(str(item), 0) + 1
                for item in meta.get("blocking_rules") or []:
                    block_counts[str(item)] = block_counts.get(str(item), 0) + 1
            top_scenarios = sorted(scenario_counts.items(), key=lambda item: item[1], reverse=True)[:5]
            common_evidence = sorted(evidence_counts.items(), key=lambda item: item[1], reverse=True)[:5]
            common_blocks = sorted(block_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        handoffs = (
            _usage_query(db, start, end)
            .filter(ProductUsageEvent.workspace_id.in_(ids), ProductUsageEvent.feature == "gpc_handoff_prepared")
            .count()
            if ids
            else 0
        )
        sessions = (
            _usage_query(db, start, end)
            .filter(ProductUsageEvent.workspace_id.in_(ids))
            .with_entities(func.count(func.distinct(ProductUsageEvent.session_id)))
            .scalar()
            if ids
            else 0
        ) or 0
        duration = (
            _usage_query(db, start, end)
            .filter(ProductUsageEvent.workspace_id.in_(ids))
            .with_entities(func.coalesce(func.sum(ProductUsageEvent.duration_ms), 0))
            .scalar()
            if ids
            else 0
        ) or 0
        paid = (
            db.query(Subscription)
            .filter(Subscription.workspace_id.in_(ids), Subscription.status == "active")
            .count()
            if ids
            else 0
        )
        rows.append(
            {
                "industry": industry,
                "workspaces": len(ids),
                "most_used_scenarios": [{"label": label, "count": count} for label, count in top_scenarios],
                "ignored_scenarios": _not_wired("ignored scenarios", "scenario impression + selection events"),
                "gpc_handoff_rate_pct": round((handoffs / sessions * 100), 2) if sessions else 0,
                "average_session_duration_min": round((duration / max(sessions, 1)) / 60000, 2) if sessions else 0,
                "common_evidence_requirements": [{"label": label, "count": count} for label, count in common_evidence],
                "common_policy_blocks": [{"label": label, "count": count} for label, count in common_blocks],
                "conversion_rate_pct": round((paid / len(ids) * 100), 2) if ids else 0,
            }
        )
    return {"title": "Verticals", "rows": rows}


def _build_module_intelligence(db: Session, start: datetime, end: datetime) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    for key, config in COMMAND_CENTER_MODULES.items():
        events = config["events"]
        metrics = [
            _metric("Telemetry events", _feature_count(db, start, end, events)),
            _metric("Page views", _usage_count(db, start, end, routes=[config["route"]], surfaces=[key])),
        ]
        if key == "models":
            metrics.extend(
                [
                    _metric("Models deployed", db.query(Deployment).filter(Deployment.deployed_at >= start, Deployment.deployed_at <= end).count()),
                    _not_wired("latency by model", "workspace_request_logs.model latency rollup by model"),
                ]
            )
        elif key == "pipelines":
            metrics.extend(
                [
                    _metric("Pipelines created", db.query(Pipeline).filter(Pipeline.created_at >= start, Pipeline.created_at <= end).count()),
                    _metric("Test runs", db.query(PipelineRun).filter(PipelineRun.created_at >= start, PipelineRun.created_at <= end).count()),
                ]
            )
        elif key == "deployments":
            metrics.extend(
                [
                    _metric("Live endpoints", db.query(Deployment).filter(Deployment.status == "ACTIVE").count()),
                    _metric("API keys created", db.query(APIKey).filter(APIKey.created_at >= start, APIKey.created_at <= end).count()),
                ]
            )
        elif key == "github":
            metrics.extend(
                [
                    _metric("Repos connected", db.query(WorkspaceGithubRepoSelection).count()),
                    _metric("Repo selections", db.query(WorkspaceGithubRepoSelection).filter(WorkspaceGithubRepoSelection.selected_at >= start).count()),
                ]
            )
        elif key == "billing":
            metrics.extend(
                [
                    _metric("Reserve funded", _feature_count(db, start, end, ["reserve_funded"])),
                    _metric("Paid workspaces", db.query(Subscription).filter(Subscription.status == "active").count()),
                ]
            )
        elif key == "compliance":
            metrics.append(_metric("Evidence exports", db.query(Export).filter(Export.created_at >= start, Export.created_at <= end).count()))
        elif key == "risk_trust":
            metrics.extend(
                [
                    _metric("PII audit flags", db.query(AIAuditLog).filter(AIAuditLog.created_at >= start, AIAuditLog.pii_detected.is_(True)).count()),
                    _metric("Admin users without MFA", db.query(User).filter(User.role.in_([UserRole.ADMIN, UserRole.OWNER]), User.mfa_enabled.is_(False)).count()),
                ]
            )
        sections.append({"key": key, "title": config["title"], "route": config["route"], "metrics": metrics})
    return sections


def _score_workspace(
    workspace: Workspace,
    signals: Dict[str, int],
    paid: bool,
    github_connected: bool,
) -> Dict[str, Any]:
    score = 0
    score += min(signals.get("sessions", 0), 5) * 4
    score += min(signals.get("duration_min", 0), 120) // 10
    score += signals.get("playground", 0) * 5
    score += signals.get("gpc_handoffs", 0) * 12
    score += signals.get("billing", 0) * 8
    score += signals.get("compliance_exports", 0) * 10
    score += signals.get("backend_access", 0) * 18
    score += signals.get("team_invites", 0) * 6
    score += 10 if github_connected else 0
    score += signals.get("pipeline_deploy", 0) * 12
    score -= min(signals.get("errors", 0), 8) * 2
    if paid or signals.get("backend_access", 0) or (signals.get("billing", 0) and signals.get("gpc_handoffs", 0)):
        state = "commercially_serious"
    elif signals.get("gpc_handoffs", 0) or signals.get("compliance_exports", 0) or signals.get("pipeline_deploy", 0):
        state = "evaluation_ready"
    elif signals.get("sessions", 0) or signals.get("playground", 0):
        state = "active"
    elif score > 0:
        state = "curious"
    else:
        state = "cold"
    if signals.get("errors", 0) >= 5 and signals.get("sessions", 0) <= 1:
        state = "at_risk"
    return {"score": int(score), "state": state}


def _build_heatmap_section(db: Session, start: datetime, end: datetime) -> Dict[str, Any]:
    workspaces = db.query(Workspace).all()
    subscriptions = {row.workspace_id: row for row in db.query(Subscription).all()}
    github_counts = {
        row.workspace_id: row.count
        for row in db.query(WorkspaceGithubRepoSelection.workspace_id, func.count(WorkspaceGithubRepoSelection.id).label("count"))
        .group_by(WorkspaceGithubRepoSelection.workspace_id)
        .all()
    }
    rows: List[Dict[str, Any]] = []
    for workspace in workspaces:
        events = _usage_query(db, start, end).filter(ProductUsageEvent.workspace_id == workspace.id).all()
        sessions = len({event.session_id for event in events if event.session_id})
        duration_min = round(sum(event.duration_ms or 0 for event in events) / 60000)
        signals = {
            "sessions": sessions,
            "duration_min": duration_min,
            "playground": sum(1 for event in events if event.surface == "playground" or event.route == "/playground"),
            "gpc_handoffs": sum(1 for event in events if event.feature == "gpc_handoff_prepared"),
            "billing": sum(1 for event in events if event.surface == "billing" or event.route == "/billing"),
            "compliance_exports": sum(1 for event in events if event.feature in {"evidence_exported", "audit_export_clicked", "auditor_package_downloaded"}),
            "backend_access": sum(1 for event in events if event.feature in {"backend_access_requested", "private_backend_access_requested"}),
            "team_invites": db.query(WorkspaceInvite).filter(WorkspaceInvite.workspace_id == workspace.id, WorkspaceInvite.created_at >= start).count(),
            "pipeline_deploy": sum(1 for event in events if event.feature in {"pipeline_created", "model_deploy_clicked", "deploy_as_endpoint_clicked"}),
            "errors": db.query(WorkspaceRequestLog).filter(
                WorkspaceRequestLog.workspace_id == workspace.id,
                WorkspaceRequestLog.created_at >= start,
                WorkspaceRequestLog.status != "success",
            ).count(),
        }
        sub = subscriptions.get(workspace.id)
        paid = bool(sub and _enum_value(sub.status) == "active")
        github_connected = bool(github_counts.get(workspace.id))
        score = _score_workspace(workspace, signals, paid, github_connected)
        rows.append(
            {
                "workspace_id": workspace.id,
                "workspace_name": workspace.name,
                "tenant": workspace.slug,
                "industry": workspace.industry or "generic",
                "plan": _enum_value(sub.plan) if sub else workspace.license_tier or "not_wired",
                "status": score["state"],
                "score": score["score"],
                "signals": signals,
                "github_connected": github_connected,
                "paid": paid,
            }
        )
    return {"title": "Customer Heat Map", "rows": sorted(rows, key=lambda row: row["score"], reverse=True)}


def _build_live_tenants_section(db: Session, now: datetime) -> Dict[str, Any]:
    active_since = now - timedelta(minutes=30)
    sessions = (
        db.query(UserSession, User, Workspace)
        .join(User, UserSession.user_id == User.id)
        .join(Workspace, User.workspace_id == Workspace.id)
        .filter(UserSession.is_active.is_(True), UserSession.last_accessed >= active_since)
        .order_by(UserSession.last_accessed.desc())
        .all()
    )
    subscriptions = {row.workspace_id: row for row in db.query(Subscription).all()}
    github_counts = {
        row.workspace_id: row.count
        for row in db.query(WorkspaceGithubRepoSelection.workspace_id, func.count(WorkspaceGithubRepoSelection.id).label("count"))
        .group_by(WorkspaceGithubRepoSelection.workspace_id)
        .all()
    }
    rows: List[Dict[str, Any]] = []
    for session, user, workspace in sessions:
        latest_event = (
            db.query(ProductUsageEvent)
            .filter(ProductUsageEvent.user_id == user.id)
            .order_by(ProductUsageEvent.created_at.desc())
            .first()
        )
        sub = subscriptions.get(workspace.id)
        rows.append(
            {
                "workspace_name": workspace.name,
                "tenant": workspace.slug,
                "industry": workspace.industry or "generic",
                "profile": workspace.playground_profile or "generic",
                "current_page": latest_event.route if latest_event else "not wired",
                "last_action": latest_event.feature or latest_event.event_type if latest_event else "no telemetry event",
                "session_duration_min": round((now - session.created_at).total_seconds() / 60, 1),
                "plan": _enum_value(sub.plan) if sub else workspace.license_tier or "not wired",
                "region": "tenant policy",
                "sovereign_mode": "on-prem",
                "github_connected": bool(github_counts.get(workspace.id)),
                "mfa_status": "enabled" if user.mfa_enabled else "disabled",
                "byos_private_runtime_status": "not wired",
                "last_seen": _iso(session.last_accessed),
            }
        )
    return {"title": "Live Tenants", "rows": rows}


def _build_founder_tasks(heatmap: Dict[str, Any], module_sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    tasks: List[Dict[str, Any]] = []
    for row in heatmap.get("rows", [])[:12]:
        if row["status"] in {"commercially_serious", "evaluation_ready"}:
            tasks.append(
                {
                    "priority": "high" if row["status"] == "commercially_serious" else "medium",
                    "workspace": row["workspace_name"],
                    "action": "Founder follow-up",
                    "reason": f"{row['status']} from Playground/GPC/billing/compliance signals",
                }
            )
        if row["signals"].get("errors", 0) >= 5:
            tasks.append(
                {
                    "priority": "high",
                    "workspace": row["workspace_name"],
                    "action": "Investigate auth/runtime failures",
                    "reason": f"{row['signals']['errors']} backend errors in the scoring window",
                }
            )
    for section in module_sections:
        if section["key"] in {"gpc", "github", "billing"}:
            missing = [metric for metric in section["metrics"] if metric.get("status") == "not_wired"]
            if missing:
                tasks.append(
                    {
                        "priority": "medium",
                        "workspace": "platform",
                        "action": f"Wire {section['title']} metric",
                        "reason": missing[0]["needs"],
                    }
                )
    return {"title": "Founder Tasks", "rows": tasks[:20]}


def _build_system_health(db: Session, start: datetime, end: datetime) -> Dict[str, Any]:
    api_errors = (
        db.query(WorkspaceRequestLog)
        .filter(WorkspaceRequestLog.created_at >= start, WorkspaceRequestLog.created_at <= end, WorkspaceRequestLog.status != "success")
        .count()
    )
    return {
        "title": "System Health",
        "metrics": [
            _metric("API health", "healthy" if api_errors == 0 else "degraded", "wired", f"{api_errors} request errors in window"),
            _not_wired("license health", "license server health endpoint"),
            _not_wired("provider readiness", "provider readiness heartbeat event"),
            _not_wired("local runtime/vLLM status", "BYOS runtime health event"),
            _not_wired("queue/latency status", "queue worker heartbeat + latency rollup"),
            _not_wired("background workers", "worker heartbeat event"),
            _not_wired("database/migration status", "migration status check"),
            _not_wired("Cloudflare/cache/redirect status", "Cloudflare Pages/Workers health probe"),
        ],
    }


def _build_audit_section(db: Session, workspaces: Dict[str, Workspace]) -> Dict[str, Any]:
    rows = (
        db.query(SecurityAuditLog)
        .order_by(SecurityAuditLog.created_at.desc())
        .limit(80)
        .all()
    )
    return {
        "title": "Audit Log",
        "rows": [
            {
                "id": row.id,
                "workspace": _workspace_label(workspaces, row.workspace_id),
                "user_id": row.user_id,
                "event_type": row.event_type,
                "event_category": row.event_category,
                "success": row.success,
                "created_at": _iso(row.created_at),
                "details": _json_loads(row.details, {"redacted": True}),
            }
            for row in rows
        ],
    }


def _build_command_center_payload(db: Session, current_user: User, days: int = 14) -> Dict[str, Any]:
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    today = datetime(now.year, now.month, now.day)
    workspaces = {row.id: row for row in db.query(Workspace).all()}
    active_sessions_now = (
        db.query(UserSession)
        .filter(UserSession.is_active.is_(True), UserSession.last_accessed >= now - timedelta(minutes=30))
        .count()
    )
    active_users_now = (
        db.query(UserSession.user_id)
        .filter(UserSession.is_active.is_(True), UserSession.last_accessed >= now - timedelta(minutes=30))
        .distinct()
        .count()
    )
    gpc_today = _usage_count(db, today, now, features=["gpc_handoff_prepared"])
    heatmap = _build_heatmap_section(db, start, now)
    evaluation_ready = sum(1 for row in heatmap["rows"] if row["status"] == "evaluation_ready")
    serious = sum(1 for row in heatmap["rows"] if row["status"] == "commercially_serious")
    backend_requests = _feature_count(db, start, now, ["backend_access_requested", "private_backend_access_requested"])
    active_subs = db.query(Subscription).filter(Subscription.status == "active").count()
    reserve_funded = _feature_count(db, start, now, ["reserve_funded"])
    policy_blocks = _feature_count(db, start, now, ["policy_block", "external_fallback_block"])
    system_health = _build_system_health(db, start, now)
    module_sections = _build_module_intelligence(db, start, now)
    overview = {
        "title": "Overview",
        "metrics": [
            _metric("active workspaces", db.query(Workspace).filter(Workspace.is_active.is_(True)).count()),
            _metric("active users now", active_users_now),
            _metric("GPC handoffs today", gpc_today),
            _metric("evaluation-ready accounts", evaluation_ready),
            _metric("commercially serious accounts", serious),
            _metric("backend/private access requests", backend_requests),
            _metric("MRR / reserve funded", {"active_subscriptions": active_subs, "reserve_funded_events": reserve_funded}),
            _metric("policy blocks", policy_blocks),
            _metric("system health", "healthy" if all(m["status"] == "wired" and m["value"] != "degraded" for m in system_health["metrics"][:1]) else "degraded"),
        ],
    }
    return {
        "generated_at": now.isoformat(),
        "window_days": days,
        "redaction": "raw prompts and repo contents are omitted by default",
        "workspace_spine": {
            "workspace": ["Overview Center", "Playground", "GPC"],
            "infrastructure": ["Models", "Marketplace", "Pipelines", "Deployments"],
            "governance": ["Vault", "Compliance"],
            "operations": ["Monitoring", "Billing"],
            "access": ["Team", "Settings"],
            "sovereign_mode": "ON-PREM",
            "policy": "Hetzner-first policy evaluation. Approved fallback only when tenant rules allow it.",
            "badges": ["Hetzner", "Fallback", "Tenant-scoped"],
        },
        "overview": overview,
        "live_tenants": _build_live_tenants_section(db, now),
        "usage": _build_usage_section(db, start, now),
        "funnel": _build_funnel_section(db, start, now),
        "verticals": _build_verticals_section(db, start, now),
        "module_intelligence": module_sections,
        "heatmap": heatmap,
        "founder_tasks": _build_founder_tasks(heatmap, module_sections),
        "system_health": system_health,
        "audit": _build_audit_section(db, workspaces),
    }


@router.get("/command-center")
async def command_center_snapshot(
    days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    _record_command_center_access(db, current_user, "/api/v1/admin/command-center")
    return _build_command_center_payload(db, current_user, days)


@router.get("/command-center/live-tenants")
async def command_center_live_tenants(
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    _record_command_center_access(db, current_user, "/api/v1/admin/command-center/live-tenants")
    return _build_live_tenants_section(db, datetime.utcnow())


@router.get("/command-center/usage")
async def command_center_usage(
    days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    _record_command_center_access(db, current_user, "/api/v1/admin/command-center/usage")
    now = datetime.utcnow()
    return _build_usage_section(db, now - timedelta(days=days), now)


@router.get("/command-center/funnel")
async def command_center_funnel(
    days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    _record_command_center_access(db, current_user, "/api/v1/admin/command-center/funnel")
    now = datetime.utcnow()
    return _build_funnel_section(db, now - timedelta(days=days), now)


@router.get("/command-center/verticals")
async def command_center_verticals(
    days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    _record_command_center_access(db, current_user, "/api/v1/admin/command-center/verticals")
    now = datetime.utcnow()
    return _build_verticals_section(db, now - timedelta(days=days), now)


@router.get("/command-center/heatmap")
async def command_center_heatmap(
    days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    _record_command_center_access(db, current_user, "/api/v1/admin/command-center/heatmap")
    now = datetime.utcnow()
    return _build_heatmap_section(db, now - timedelta(days=days), now)


@router.get("/command-center/tasks")
async def command_center_tasks(
    days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    _record_command_center_access(db, current_user, "/api/v1/admin/command-center/tasks")
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    heatmap = _build_heatmap_section(db, start, now)
    modules = _build_module_intelligence(db, start, now)
    return _build_founder_tasks(heatmap, modules)


@router.get("/command-center/audit")
async def command_center_audit(
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    _record_command_center_access(db, current_user, "/api/v1/admin/command-center/audit")
    workspaces = {row.id: row for row in db.query(Workspace).all()}
    return _build_audit_section(db, workspaces)
