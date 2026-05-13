"""Admin router: workspace management, user management, system-wide controls (superuser/admin only)."""
from datetime import datetime, timedelta
from typing import List, Optional

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
    SecurityEvent, Job, AIAuditLog,
    IncidentLog, IncidentSeverity, IncidentStatus,
    CommercialArtifact, ProductUsageEvent, SignupLead, UserSession, WorkspaceRequestLog,
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
