"""Workspace gateway dashboard APIs."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from db.models import InviteStatus, User, UserRole, UserStatus, WorkspaceInvite
from db.session import get_db
from core.services.financial_analytics import (
    fetch_workspace_request_metrics,
    workspace_financial_summary,
)
from core.services.workspace_gateway import (
    fetch_api_key_rows,
    fetch_cost_budget_payload,
    fetch_observability_payload,
    fetch_overview,
    fetch_public_status_payload,
    fetch_model_rows,
    set_model_enabled,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])
public_router = APIRouter(tags=["public-status"])


class ModelToggleRequest(BaseModel):
    enabled: bool


class BudgetUpdateRequest(BaseModel):
    budget_type: str = "monthly"
    amount: Decimal
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    alert_thresholds: Optional[list[int]] = [50, 80, 95]


def _parse_datetime_param(value: Optional[str], field: str) -> Optional[datetime]:
    """Parse optional ISO8601 datetime query string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except (AttributeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid ISO datetime for {field}") from exc


@router.get("/analytics/summary")
async def workspace_financial_overview(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return workspace_financial_summary(
        db=db,
        workspace_id=current_user.workspace_id,
        start_date=_parse_datetime_param(start_date, "start_date"),
        end_date=_parse_datetime_param(end_date, "end_date"),
    )


@router.get("/overview")
async def workspace_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return fetch_overview(db, workspace_id=current_user.workspace_id)


@router.get("/observability")
async def workspace_observability(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    model: Optional[str] = None,
    status: Optional[str] = None,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    payload = fetch_observability_payload(
        db,
        workspace_id=current_user.workspace_id,
        start_date=start_date,
        end_date=end_date,
        model=model,
        status=status,
    )
    payload["rows"] = payload["rows"][offset : offset + limit]
    payload["limit"] = limit
    payload["offset"] = offset
    return payload


@router.get("/analytics/requests")
async def workspace_analytics_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    request_path: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=0, le=500),
    offset: int = Query(0, ge=0),
    include_rows: bool = Query(False),
):
    parsed_end = _parse_datetime_param(end_date, "end_date") or datetime.utcnow()
    parsed_start = _parse_datetime_param(start_date, "start_date") or (parsed_end - timedelta(days=30))
    return fetch_workspace_request_metrics(
        db=db,
        workspace_id=current_user.workspace_id,
        start_date=parsed_start,
        end_date=parsed_end,
        model=model,
        request_path=request_path,
        status=status,
        limit=limit,
        offset=offset,
        include_rows=include_rows,
    )


@router.get("/api-keys")
async def workspace_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "keys": fetch_api_key_rows(db, workspace_id=current_user.workspace_id),
    }


@router.get("/models")
async def workspace_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "models": fetch_model_rows(db, workspace_id=current_user.workspace_id),
    }


@router.patch("/models/{model_slug}")
async def workspace_model_toggle(
    model_slug: str,
    payload: ModelToggleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = set_model_enabled(db, current_user.workspace_id, model_slug, payload.enabled)
    return {
        "model_slug": row.model_slug,
        "enabled": row.enabled,
        "bedrock_model_id": row.bedrock_model_id,
    }


@router.get("/cost-budget")
async def workspace_cost_budget(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return fetch_cost_budget_payload(db, workspace_id=current_user.workspace_id)


@router.post("/budget")
async def workspace_budget_update(
    payload: BudgetUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from apps.api.routers.budget import create_budget, BudgetRequest

    request = BudgetRequest(
        budget_type=payload.budget_type,
        amount=payload.amount,
        period_start=payload.period_start,
        period_end=payload.period_end,
        alert_thresholds=payload.alert_thresholds,
    )
    return await create_budget(request=request, workspace_id=current_user.workspace_id, db=db)


@router.get("/budget")
async def workspace_budget_get(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from apps.api.routers.budget import get_budget_status

    return await get_budget_status(
        workspace_id=current_user.workspace_id,
        budget_type="monthly",
        db=db,
        limit=100,
    )


@router.get("/cost-budget.csv")
async def workspace_cost_budget_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = fetch_cost_budget_payload(db, workspace_id=current_user.workspace_id)
    lines = ["date,cost_usd"]
    for row in payload["monthly_spend_chart"]:
        lines.append(f"{row['date']},{row['cost_usd']}")
    csv = "\n".join(lines) + "\n"
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="veklom-costs.csv"'})


# ── Members + invites ──────────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str
    role: str = "user"


class InviteAcceptRequest(BaseModel):
    token: str


def _is_admin(user: User) -> bool:
    return user.role in (UserRole.OWNER, UserRole.ADMIN) or user.is_superuser


@router.get("/members")
async def list_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    members = (
        db.query(User)
        .filter(User.workspace_id == current_user.workspace_id)
        .order_by(User.created_at.asc())
        .all()
    )
    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value if hasattr(u.role, "value") else u.role,
                "status": u.status.value if hasattr(u.status, "value") else u.status,
                "is_active": u.is_active,
                "mfa_enabled": u.mfa_enabled,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat(),
            }
            for u in members
        ]
    }


@router.get("/members/invites")
async def list_invites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin access required")
    rows = (
        db.query(WorkspaceInvite)
        .filter(WorkspaceInvite.workspace_id == current_user.workspace_id)
        .order_by(WorkspaceInvite.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": i.id,
                "email": i.email,
                "role": i.role,
                "status": i.status.value if hasattr(i.status, "value") else i.status,
                "expires_at": i.expires_at.isoformat() if i.expires_at else None,
                "created_at": i.created_at.isoformat(),
            }
            for i in rows
        ]
    }


@router.post("/members/invite", status_code=201)
async def invite_member(
    payload: InviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(current_user):
        raise HTTPException(403, "Only admins can invite team members")

    email = (payload.email or "").strip().lower()
    if not email or "@" not in email or len(email) > 200:
        raise HTTPException(400, "Invalid email address")

    role = payload.role.lower()
    valid_roles = {r.value for r in UserRole}
    if role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of {sorted(valid_roles)}")
    if role == UserRole.OWNER.value and not current_user.is_superuser:
        raise HTTPException(403, "Only superusers can invite owners")

    existing_user = (
        db.query(User)
        .filter(User.email == email, User.workspace_id == current_user.workspace_id)
        .first()
    )
    if existing_user:
        raise HTTPException(409, "User with this email is already a workspace member")

    pending = (
        db.query(WorkspaceInvite)
        .filter(
            WorkspaceInvite.workspace_id == current_user.workspace_id,
            WorkspaceInvite.email == email,
            WorkspaceInvite.status == InviteStatus.PENDING,
        )
        .first()
    )
    if pending:
        raise HTTPException(409, "Pending invite already exists for this email")

    invite = WorkspaceInvite(
        workspace_id=current_user.workspace_id,
        email=email,
        role=role,
        invited_by=current_user.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return {
        "id": invite.id,
        "email": invite.email,
        "role": invite.role,
        "status": invite.status.value,
        "token": invite.token,  # one-shot — caller is responsible for delivering
        "expires_at": invite.expires_at.isoformat(),
        "created_at": invite.created_at.isoformat(),
    }


@router.post("/members/invites/{invite_id}/revoke")
async def revoke_invite(
    invite_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin access required")
    invite = (
        db.query(WorkspaceInvite)
        .filter(
            WorkspaceInvite.id == invite_id,
            WorkspaceInvite.workspace_id == current_user.workspace_id,
        )
        .first()
    )
    if not invite:
        raise HTTPException(404, "Invite not found")
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(409, f"Cannot revoke invite with status {invite.status}")
    invite.status = InviteStatus.REVOKED
    invite.revoked_at = datetime.utcnow()
    db.commit()
    return {"id": invite.id, "status": invite.status.value}


@public_router.get("/status/data")
async def public_status_data(db: Session = Depends(get_db)):
    return fetch_public_status_payload(db)


@public_router.get("/status", include_in_schema=False)
async def public_status_page():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Veklom Status</title>
<meta name="robots" content="noindex, nofollow" />
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:wght@400;500;600&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/app/app.css">
<style>
.status-shell { max-width: 980px; margin: 0 auto; padding: 64px 24px 96px; }
.status-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin-top:20px; }
.status-card { background:var(--ink-2); border:1px solid var(--rule); border-radius:6px; padding:20px; }
.status-pill { display:inline-flex; padding:4px 10px; border:1px solid var(--ok); color:var(--ok); font-family:var(--mono); font-size:10px; text-transform:uppercase; letter-spacing:.16em; border-radius:2px; }
.status-row { display:flex; justify-content:space-between; gap:10px; padding:12px 0; border-bottom:1px solid var(--rule); }
.status-row:last-child { border-bottom:0; }
.status-title { font-family:var(--mono); font-size:10px; text-transform:uppercase; letter-spacing:.18em; color:var(--mute); }
.status-value { color:var(--bone); }
.status-small { color:var(--bone-2); font-size:14px; line-height:1.6; }
</style>
</head>
<body>
<main class="status-shell">
  <div class="app-brand"><img src="/logo.svg" alt="Veklom" /> Veklom Status</div>
  <div class="status-card">
    <div class="status-pill" id="status-pill">Loading</div>
    <h1 class="app-h1" style="margin-top:14px;">Service status and incident feed</h1>
    <p class="app-sub">Public uptime and incident view for API, Auth, Marketplace, and AI Proxy.</p>
    <div id="status-root" class="status-small">Loading status...</div>
  </div>
</main>
<script src="/app/auth.js"></script>
<script>
async function loadStatus() {
  const root = document.getElementById("status-root");
  const pill = document.getElementById("status-pill");
  try {
    const out = await VK.publicRequest("/status/data");
    pill.textContent = "Operational";
    root.innerHTML = [
      '<div class="status-grid">' + out.services.map(service =>
        '<div class="status-card">' +
          '<div class="status-title">' + service.name + '</div>' +
          '<div style="font-family:var(--serif); font-size:28px; margin:10px 0 6px;">' + Number(service.uptime_90d).toFixed(2) + '%</div>' +
          '<div class="status-small">Status: ' + service.status + '</div>' +
        '</div>'
      ).join("") + '</div>',
      '<div class="status-card" style="margin-top:18px;">' +
        '<div class="status-title">Current Incidents</div>' +
        (out.incidents.length ? out.incidents.map(i => '<div class="status-row"><div><strong>' + i.title + '</strong><div class="status-small">' + (i.description || "") + '</div></div><div class="status-value">' + i.severity + ' / ' + i.status + '</div></div>').join("") : '<p class="status-small" style="margin-top:12px;">No current incidents.</p>') +
      '</div>',
      '<div class="status-card" style="margin-top:18px;">' +
        '<div class="status-title">Scheduled Maintenance</div>' +
        (out.maintenance.length ? out.maintenance.map(i => '<div class="status-row"><div><strong>' + i.title + '</strong><div class="status-small">' + (i.description || "") + '</div></div><div class="status-value">' + i.severity + '</div></div>').join("") : '<p class="status-small" style="margin-top:12px;">No scheduled maintenance.</p>') +
      '</div>'
    ].join("");
  } catch (err) {
    pill.textContent = "Degraded";
    root.innerHTML = '<div class="alert alert-error">' + (err.message || "Unable to load status") + '</div>';
  }
}
loadStatus();
</script>
</body>
</html>"""
    return Response(content=html, media_type="text/html")
