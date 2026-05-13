"""Authentication endpoints: register, login, logout, refresh, /me, MFA, API keys, GitHub OAuth."""
import base64
import hashlib
import hmac
import io
import json
import httpx
import secrets
import logging
import pyotp
import qrcode
import time
from datetime import datetime, timedelta
from typing import Optional, List
from urllib.parse import urlencode

from qrcode.image.svg import SvgPathImage

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.config import get_settings
from core.security import create_access_token, decode_access_token, get_password_hash, verify_password
from db.session import get_db
from db.models import (
    APIKey,
    InviteStatus,
    SecurityAuditLog,
    SignupLead,
    TokenWallet,
    User,
    UserRole,
    UserSession,
    UserStatus,
    Workspace,
    WorkspaceInvite,
)
from apps.api.deps import get_current_user
from core.services.trial_onboarding import issue_trial_license, send_trial_welcome
from core.services.workspace_profiles import ensure_workspace_profile_defaults, normalize_industry
from onboarding.trial import post_signup_onboarding

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

_API_KEY_PREFIX = "byos_"
FREE_EVALUATION_RESERVE_UNITS = 0
# Deprecated compatibility alias. Free Evaluation is run-limited, not prepaid reserve-funded.
FREE_TRIAL_CREDITS = FREE_EVALUATION_RESERVE_UNITS
CUSTOMER_API_KEY_SCOPES = {"READ", "EXEC", "WRITE"}
INTERNAL_API_KEY_SCOPES = {"ADMIN", "AUTOMATION", "MARKETPLACE_AUTOMATION", "JOB_PROCESSOR"}


# ─── Schemas ────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    name: Optional[str] = None
    workspace_name: str
    invite_code: Optional[str] = None
    trial_tier: Optional[str] = None
    signup_type: str = "general"
    industry: Optional[str] = None
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    workspace_id: str
    role: str
    trial_api_key: Optional[str] = None
    reserve_balance_units: Optional[int] = None
    reserve_balance_usd: Optional[str] = None
    # Deprecated compatibility field. New product language is Operating Reserve.
    wallet_balance: Optional[int] = None
    signup_type: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class AcceptInviteRequest(BaseModel):
    invite_secret: Optional[str] = None
    token: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_url: str


class APIKeyCreateRequest(BaseModel):
    name: str
    scopes: List[str] = ["read"]
    rate_limit_per_minute: int = 60
    allowed_ips: Optional[List[str]] = None
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    rate_limit_per_minute: int
    is_active: bool
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]


class APIKeyCreateResponse(APIKeyResponse):
    raw_key: str


class ConnectedAccountsResponse(BaseModel):
    github_configured: bool
    github_connected: bool
    github_username: Optional[str] = None
    github_connected_at: Optional[str] = None
    github_account_id: Optional[str] = None


class MFAEnableResponse(BaseModel):
    message: str
    mfa_enabled: bool
    audit_event: str
    backup_codes: list[str]


class MFARecoveryCodeStatusResponse(BaseModel):
    backup_codes_remaining: int
    backup_codes_total: int


class MFARegenerateRequest(BaseModel):
    password: str
    mfa_code: str


class MFAAdminResetRequest(BaseModel):
    reason: Optional[str] = None


class MFACompleteGithubLoginRequest(BaseModel):
    challenge_token: str
    mfa_code: str


# ─── Helpers ────────────────────────────────────────────────────────────────

def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _hash_recovery_code(raw_code: str) -> str:
    return hmac.new(settings.secret_key.encode(), raw_code.encode(), hashlib.sha256).hexdigest()


def _load_recovery_codes(user: User) -> list[dict]:
    raw = getattr(user, "mfa_recovery_codes_json", None)
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _store_recovery_codes(user: User, codes: list[dict]) -> None:
    user.mfa_recovery_codes_json = json.dumps(codes, sort_keys=True)


def _generate_backup_codes(count: int = 10) -> tuple[list[str], list[dict]]:
    plain: list[str] = []
    stored: list[dict] = []
    for _ in range(count):
        code = secrets.token_hex(4).upper()
        plain.append(code)
        stored.append({"code_hash": _hash_recovery_code(code), "used_at": None})
    return plain, stored


def _remaining_backup_codes(user: User) -> int:
    return sum(1 for item in _load_recovery_codes(user) if not item.get("used_at"))


def _log_security_event(
    db: Session,
    *,
    event_type: str,
    event_category: str,
    request: Request | None = None,
    actor: User | None = None,
    target_user: User | None = None,
    success: bool = True,
    failure_reason: str | None = None,
    details: dict | None = None,
) -> None:
    payload = dict(details or {})
    if actor:
        payload.setdefault("actor_email", actor.email)
        payload.setdefault("actor_role", actor.role.value if hasattr(actor.role, "value") else actor.role)
    if target_user:
        payload.setdefault("target_user_id", target_user.id)
        payload.setdefault("target_user_email", target_user.email)
    db.add(
        SecurityAuditLog(
            workspace_id=(target_user.workspace_id if target_user else actor.workspace_id if actor else None),
            user_id=actor.id if actor else None,
            event_type=event_type,
            event_category=event_category,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            success=success,
            failure_reason=failure_reason,
            details=json.dumps(payload, sort_keys=True) if payload else None,
        )
    )


def _issue_session_tokens(
    *,
    user: User,
    request: Request | None,
    db: Session,
) -> dict:
    tokens = _create_tokens(user)
    session = UserSession(
        user_id=user.id,
        session_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        expires_at=datetime.utcnow() + timedelta(seconds=tokens["expires_in"]),
    )
    db.add(session)
    return tokens


def _consume_mfa_code(
    *,
    user: User,
    code: str,
    db: Session,
    request: Request | None,
    audit_context: str,
) -> str:
    submitted = str(code or "").strip().replace(" ", "").upper()
    if not submitted:
        _log_security_event(
            db,
            event_type="mfa_verification_failed",
            event_category="authentication",
            request=request,
            actor=user,
            target_user=user,
            success=False,
            failure_reason="missing_code",
            details={"context": audit_context},
        )
        raise HTTPException(status_code=401, detail="MFA code required")

    if user.mfa_secret:
        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(submitted, valid_window=1):
            _log_security_event(
                db,
                event_type="mfa_totp_verified",
                event_category="authentication",
                request=request,
                actor=user,
                target_user=user,
                details={"context": audit_context, "method": "totp"},
            )
            return "totp"

    recovery_codes = _load_recovery_codes(user)
    hashed = _hash_recovery_code(submitted)
    for item in recovery_codes:
        if item.get("code_hash") == hashed and not item.get("used_at"):
            item["used_at"] = datetime.utcnow().isoformat()
            _store_recovery_codes(user, recovery_codes)
            _log_security_event(
                db,
                event_type="mfa_backup_code_used",
                event_category="authentication",
                request=request,
                actor=user,
                target_user=user,
                details={"context": audit_context, "method": "backup_code"},
            )
            return "backup_code"

    _log_security_event(
        db,
        event_type="mfa_verification_failed",
        event_category="authentication",
        request=request,
        actor=user,
        target_user=user,
        success=False,
        failure_reason="invalid_code",
        details={"context": audit_context},
    )
    raise HTTPException(status_code=401, detail="Invalid MFA code")


def _create_tokens(user: User) -> dict:
    access_payload = {
        "user_id": user.id,
        "workspace_id": user.workspace_id,
        "role": user.role.value,
        "is_superuser": user.is_superuser,
    }
    refresh_payload = {**access_payload, "type": "refresh"}
    return {
        "access_token": create_access_token(access_payload),
        "refresh_token": create_access_token(refresh_payload, expires_delta=timedelta(days=30)),
        "expires_in": settings.access_token_expire_minutes * 60,
    }


def _normalize_api_key_scopes(scopes: List[str], current_user: User) -> List[str]:
    """Normalize and constrain API-key scopes before persistence.

    Customer API keys are tenant-scoped execution/read/write credentials. Internal
    automation scopes are reserved for platform superusers so a workspace owner
    cannot mint a key that reaches Veklom-only operator surfaces.
    """
    normalized = []
    for scope in scopes or ["read"]:
        value = str(scope or "").strip().upper()
        if not value:
            continue
        if value not in normalized:
            normalized.append(value)

    if not normalized:
        normalized = ["READ"]

    reserved = set(normalized) & INTERNAL_API_KEY_SCOPES
    if reserved and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal automation API-key scopes are reserved for Veklom operators",
        )

    allowed = CUSTOMER_API_KEY_SCOPES | (INTERNAL_API_KEY_SCOPES if current_user.is_superuser else set())
    unsupported = set(normalized) - allowed
    if unsupported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported API-key scope(s): {', '.join(sorted(unsupported))}",
        )

    return normalized


# ─── Auth Routes ─────────────────────────────────────────────────────────────

def _totp_qr_data_uri(provisioning_uri: str) -> str:
    """Return a CSP-safe QR image payload for authenticator apps."""
    img = qrcode.make(provisioning_uri, image_factory=SvgPathImage)
    buffer = io.BytesIO()
    img.save(buffer)
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{payload}"


def _record_signup_lead(
    db: Session,
    *,
    email: str,
    full_name: str | None,
    workspace_name: str | None,
    workspace_id: str | None,
    user_id: str | None,
    signup_type: str,
    source: str,
    request: Request | None,
    utm_source: str | None = None,
    utm_campaign: str | None = None,
) -> None:
    db.add(
        SignupLead(
            email=email,
            full_name=full_name,
            workspace_name=workspace_name,
            workspace_id=workspace_id,
            user_id=user_id,
            signup_type=(signup_type or "general")[:80],
            source=source[:80],
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            referer=request.headers.get("referer") if request else None,
            utm_source=(utm_source or "")[:120] or None,
            utm_campaign=(utm_campaign or "")[:120] or None,
            landing_path=str(request.url.path) if request else None,
        )
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Register a new workspace + owner user."""
    full_name = (payload.full_name or payload.name or "").strip() or None
    # Password strength enforcement
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(c.isupper() for c in payload.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in payload.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")

    # Workspace name validation
    if not payload.workspace_name or len(payload.workspace_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Workspace name must be at least 2 characters")
    if len(payload.workspace_name) > 100:
        raise HTTPException(status_code=400, detail="Workspace name too long (max 100 characters)")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    workspace = Workspace(
        name=payload.workspace_name,
        slug=payload.workspace_name.lower().replace(" ", "-") + "-" + secrets.token_hex(4),
    )
    ensure_workspace_profile_defaults(workspace, normalize_industry(payload.industry))
    db.add(workspace)
    db.flush()

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=full_name,
        workspace_id=workspace.id,
        role=UserRole.OWNER,
        is_superuser=False,
    )
    db.add(user)
    wallet = TokenWallet(
        workspace_id=workspace.id,
        balance=FREE_EVALUATION_RESERVE_UNITS,
        monthly_credits_included=0,
        monthly_credits_used=0,
        total_credits_purchased=0,
        total_credits_used=0,
    )
    db.add(wallet)
    db.flush()
    _record_signup_lead(
        db,
        email=payload.email,
        full_name=full_name,
        workspace_name=payload.workspace_name,
        workspace_id=workspace.id,
        user_id=user.id,
        signup_type=payload.signup_type,
        source="password_register",
        request=request,
        utm_source=payload.utm_source,
        utm_campaign=payload.utm_campaign,
    )
    license_payload = None
    try:
        license_payload = await issue_trial_license(
            db=db,
            workspace=workspace,
            user_email=payload.email,
            user_name=full_name or payload.workspace_name,
            requested_tier=payload.trial_tier,
        )
    except Exception as exc:
        logger.warning("Trial license issuance deferred for workspace %s: %s", workspace.id, exc)

    db.commit()
    db.refresh(user)
    db.refresh(workspace)
    onboarding = {
        "api_key": None,
        "wallet_balance": wallet.balance,
        "signup_type": payload.signup_type,
    }
    try:
        onboarding = await post_signup_onboarding(
            user_id=str(user.id),
            email=user.email,
            first_name=full_name or user.email.split("@")[0],
            workspace_id=str(workspace.id),
            signup_type=payload.signup_type,
            db=db,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Post-signup onboarding deferred for workspace %s: %s", workspace.id, exc)

    tokens = _create_tokens(user)
    if license_payload:
        try:
            await send_trial_welcome(
                workspace=workspace,
                user_email=payload.email,
                user_name=full_name or payload.workspace_name,
                license_payload=license_payload,
            )
        except Exception as exc:
            logger.warning("Trial welcome email failed for workspace %s: %s", workspace.id, exc)
    return TokenResponse(
        **tokens,
        user_id=user.id,
        workspace_id=user.workspace_id,
        role=user.role.value,
        trial_api_key=onboarding.get("api_key"),
        wallet_balance=onboarding.get("wallet_balance"),
        reserve_balance_units=onboarding.get("wallet_balance"),
        reserve_balance_usd="0.00",
        signup_type=onboarding.get("signup_type"),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate user, enforce MFA if enabled."""
    user = db.query(User).filter(User.email == payload.email).first()
    credentials_error = HTTPException(status_code=401, detail="Invalid credentials")

    if not user:
        # Constant-time dummy check to prevent user enumeration via timing
        verify_password("dummy_password", "$2b$12$LJ3m4ys3Gz8KBOhGivQn3O4IFCmsfGRDMIMKPGQp0Nv0CGJxFHEV6")
        _log_security_event(
            db,
            event_type="login_failed",
            event_category="authentication",
            request=request,
            success=False,
            failure_reason="user_not_found",
            details={"email": payload.email},
        )
        db.commit()
        raise credentials_error

    if user.status == UserStatus.LOCKED:
        if user.account_locked_until and datetime.utcnow() < user.account_locked_until:
            raise HTTPException(status_code=401, detail="Account temporarily locked")
        user.status = UserStatus.ACTIVE
        user.failed_login_attempts = 0

    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            user.status = UserStatus.LOCKED
            user.account_locked_until = datetime.utcnow() + timedelta(minutes=settings.account_lockout_minutes)
        _log_security_event(
            db,
            event_type="login_failed",
            event_category="authentication",
            request=request,
            actor=user,
            target_user=user,
            success=False,
            failure_reason="invalid_password",
        )
        db.commit()
        raise credentials_error

    if user.mfa_enabled:
        _consume_mfa_code(
            user=user,
            code=payload.mfa_code or "",
            db=db,
            request=request,
            audit_context="password_login",
        )

    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    user.last_activity = datetime.utcnow()

    tokens = _issue_session_tokens(user=user, request=request, db=db)
    _log_security_event(
        db,
        event_type="login_succeeded",
        event_category="authentication",
        request=request,
        actor=user,
        target_user=user,
        details={"mfa_enabled": user.mfa_enabled},
    )
    db.commit()

    return TokenResponse(
        **tokens,
        user_id=user.id,
        workspace_id=user.workspace_id,
        role=user.role.value,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Rotate access token using a refresh token."""
    token_data = decode_access_token(payload.refresh_token)
    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    session = db.query(UserSession).filter(
        UserSession.refresh_token == payload.refresh_token,
        UserSession.is_active.is_(True),
    ).first()
    if not session:
        raise HTTPException(status_code=401, detail="Session not found or revoked")

    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    tokens = _create_tokens(user)
    session.session_token = tokens["access_token"]
    session.refresh_token = tokens["refresh_token"]
    session.last_accessed = datetime.utcnow()
    session.expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
    user.last_activity = datetime.utcnow()
    db.commit()

    return TokenResponse(
        **tokens,
        user_id=user.id,
        workspace_id=user.workspace_id,
        role=user.role.value,
    )


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(payload: AcceptInviteRequest, request: Request, db: Session = Depends(get_db)):
    """Redeem a workspace invite link and sign the user into the invited workspace."""
    invite_secret = (payload.invite_secret or payload.token or "").strip()
    if not invite_secret:
        raise HTTPException(status_code=400, detail="Invite link is missing or invalid")

    invite = db.query(WorkspaceInvite).filter(WorkspaceInvite.token == invite_secret).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite link not found or already removed")

    if invite.expires_at and invite.expires_at < datetime.utcnow():
        invite.status = InviteStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=410, detail="Invite link has expired")

    if invite.status != InviteStatus.PENDING:
        status_value = invite.status.value if hasattr(invite.status, "value") else invite.status
        raise HTTPException(status_code=409, detail=f"Invite link is already {status_value}")

    password = payload.password or ""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")

    try:
        assigned_role = UserRole(invite.role)
    except ValueError:
        assigned_role = UserRole.USER

    user = db.query(User).filter(User.email == invite.email).first()
    if user:
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Existing account password is incorrect")
        user.workspace_id = invite.workspace_id
        user.role = assigned_role
        user.status = UserStatus.ACTIVE
        user.is_active = True
        if payload.full_name and not user.full_name:
            user.full_name = payload.full_name
    else:
        user = User(
            email=invite.email,
            hashed_password=get_password_hash(password),
            full_name=payload.full_name,
            workspace_id=invite.workspace_id,
            role=assigned_role,
            status=UserStatus.ACTIVE,
            is_superuser=False,
        )
        db.add(user)
        db.flush()

    invite.status = InviteStatus.ACCEPTED
    invite.accepted_at = datetime.utcnow()
    user.last_login = datetime.utcnow()
    user.last_activity = datetime.utcnow()

    tokens = _create_tokens(user)
    session = UserSession(
        user_id=user.id,
        session_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=datetime.utcnow() + timedelta(seconds=tokens["expires_in"]),
    )
    db.add(session)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        **tokens,
        user_id=user.id,
        workspace_id=user.workspace_id,
        role=user.role.value,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Invalidate all active sessions for current user."""
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active.is_(True),
    ).update({"is_active": False})
    db.commit()


@router.get("/me")
async def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return authenticated user profile."""
    workspace = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "status": current_user.status.value,
        "workspace_id": current_user.workspace_id,
        "workspace_name": workspace.name if workspace else None,
        "workspace_slug": workspace.slug if workspace else None,
        "industry": workspace.industry if workspace else "generic",
        "playground_profile": workspace.playground_profile if workspace else "generic",
        "risk_tier": workspace.risk_tier if workspace else "generic",
        "default_policy_pack": workspace.default_policy_pack if workspace else "generic_foundation_v1",
        "license_tier": workspace.license_tier if workspace else None,
        "license_expires_at": workspace.license_expires_at.isoformat() if workspace and workspace.license_expires_at else None,
        "license_download_url": workspace.license_download_url if workspace else None,
        "mfa_enabled": current_user.mfa_enabled,
        "mfa_backup_codes_remaining": _remaining_backup_codes(current_user),
        "is_superuser": current_user.is_superuser,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "created_at": current_user.created_at.isoformat(),
        "github_username": current_user.github_username,
        "github_connected": bool(current_user.github_id and current_user.github_access_token),
    }


# ─── MFA Routes ───────────────────────────────────────────────────────────────

@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None):
    """Generate a new TOTP secret for MFA setup."""
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA already enabled")
    secret = pyotp.random_base32()
    current_user.mfa_secret = secret
    current_user.mfa_recovery_codes_json = None
    _log_security_event(
        db,
        event_type="mfa_setup_started",
        event_category="authentication",
        request=request,
        actor=current_user,
        target_user=current_user,
        details={"method": "totp"},
    )
    db.commit()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name=settings.app_name)
    return MFASetupResponse(
        secret=secret,
        provisioning_uri=uri,
        qr_url=_totp_qr_data_uri(uri),
    )


@router.post("/mfa/verify", response_model=MFAEnableResponse)
async def mfa_verify(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Confirm and activate MFA after scanning QR code."""
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="Run /auth/mfa/setup first")
    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(code, valid_window=1):
        _log_security_event(
            db,
            event_type="mfa_verification_failed",
            event_category="authentication",
            request=request,
            actor=current_user,
            target_user=current_user,
            success=False,
            failure_reason="invalid_totp",
            details={"context": "mfa_enable"},
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    backup_codes, stored_codes = _generate_backup_codes()
    current_user.mfa_enabled = True
    _store_recovery_codes(current_user, stored_codes)
    _log_security_event(
        db,
        event_type="mfa_enabled",
        event_category="authentication",
        request=request,
        actor=current_user,
        target_user=current_user,
        details={
            "method": "totp",
            "issuer": settings.app_name,
            "confirmed_state": "enabled",
            "backup_codes_issued": len(backup_codes),
        },
    )
    db.commit()
    return {
        "message": "MFA enabled successfully",
        "mfa_enabled": True,
        "audit_event": "mfa_enabled",
        "backup_codes": backup_codes,
    }


@router.delete("/mfa/disable")
async def mfa_disable(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Disable MFA — requires valid code to prevent accidental lockout."""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")
    _consume_mfa_code(
        user=current_user,
        code=code,
        db=db,
        request=request,
        audit_context="mfa_disable",
    )
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_recovery_codes_json = None
    _log_security_event(
        db,
        event_type="mfa_disabled",
        event_category="authentication",
        request=request,
        actor=current_user,
        target_user=current_user,
    )
    db.commit()
    return {"message": "MFA disabled"}


@router.get("/mfa/recovery-codes/status", response_model=MFARecoveryCodeStatusResponse)
async def mfa_recovery_code_status(current_user: User = Depends(get_current_user)):
    codes = _load_recovery_codes(current_user)
    return {
        "backup_codes_remaining": sum(1 for item in codes if not item.get("used_at")),
        "backup_codes_total": len(codes),
    }


@router.post("/mfa/recovery-codes/regenerate", response_model=MFAEnableResponse)
async def mfa_regenerate_recovery_codes(
    payload: MFARegenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA must be enabled before regeneration")
    if not verify_password(payload.password, current_user.hashed_password):
        _log_security_event(
            db,
            event_type="mfa_recovery_regeneration_failed",
            event_category="authentication",
            request=request,
            actor=current_user,
            target_user=current_user,
            success=False,
            failure_reason="invalid_password",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid password")
    _consume_mfa_code(
        user=current_user,
        code=payload.mfa_code,
        db=db,
        request=request,
        audit_context="mfa_recovery_regeneration",
    )
    backup_codes, stored_codes = _generate_backup_codes()
    _store_recovery_codes(current_user, stored_codes)
    _log_security_event(
        db,
        event_type="mfa_recovery_codes_regenerated",
        event_category="authentication",
        request=request,
        actor=current_user,
        target_user=current_user,
        details={"backup_codes_issued": len(backup_codes)},
    )
    db.commit()
    return {
        "message": "Backup codes regenerated successfully",
        "mfa_enabled": True,
        "audit_event": "mfa_recovery_codes_regenerated",
        "backup_codes": backup_codes,
    }


@router.post("/mfa/admin-reset/{user_id}")
async def mfa_admin_reset(
    user_id: str,
    payload: MFAAdminResetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    actor_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if not (
        current_user.is_superuser
        or actor_role in {UserRole.OWNER.value, UserRole.ADMIN.value}
    ):
        raise HTTPException(status_code=403, detail="Admin authorization required")
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    if not current_user.is_superuser and target_user.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=403, detail="Admin reset is limited to your workspace")
    target_user.mfa_enabled = False
    target_user.mfa_secret = None
    target_user.mfa_recovery_codes_json = None
    target_user.failed_login_attempts = 0
    target_user.account_locked_until = None
    target_user.status = UserStatus.ACTIVE
    _log_security_event(
        db,
        event_type="mfa_admin_reset",
        event_category="authentication",
        request=request,
        actor=current_user,
        target_user=target_user,
        details={"reason": (payload.reason or "").strip() or "no_reason_provided"},
    )
    db.commit()
    return {"message": "MFA reset completed", "user_id": target_user.id, "mfa_enabled": False}


# ─── API Key Routes ───────────────────────────────────────────────────────────

@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new workspace-scoped API key."""
    scopes = _normalize_api_key_scopes(payload.scopes, current_user)
    raw_key = _API_KEY_PREFIX + secrets.token_urlsafe(40)
    prefix = raw_key[:12]
    key_hash = _hash_api_key(raw_key)
    expires_at = (
        datetime.utcnow() + timedelta(days=payload.expires_in_days)
        if payload.expires_in_days
        else None
    )
    api_key = APIKey(
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
        name=payload.name,
        key_hash=key_hash,
        key_prefix=prefix,
        scopes=scopes,
        rate_limit_per_minute=str(payload.rate_limit_per_minute),
        allowed_ips=payload.allowed_ips or [],
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        rate_limit_per_minute=int(api_key.rate_limit_per_minute),
        is_active=api_key.is_active,
        created_at=api_key.created_at.isoformat(),
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        last_used_at=None,
        raw_key=raw_key,
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all API keys for the current workspace."""
    keys = db.query(APIKey).filter(
        APIKey.workspace_id == current_user.workspace_id,
        APIKey.is_active.is_(True),
    ).all()
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            rate_limit_per_minute=int(k.rate_limit_per_minute),
            is_active=k.is_active,
            created_at=k.created_at.isoformat(),
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke an API key."""
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.workspace_id == current_user.workspace_id,
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    db.commit()


# ─── GitHub OAuth ─────────────────────────────────────────────────────────────

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def _build_github_state() -> str:
    """Build signed short-lived OAuth state token to mitigate CSRF."""
    ts = str(int(time.time()))
    nonce = secrets.token_urlsafe(16)
    payload = f"{ts}.{nonce}"
    sig = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{payload}.{sig_b64}"


def _validate_github_state(state: str, max_age_seconds: int = 600) -> bool:
    """Validate signed OAuth state and expiry window."""
    try:
        ts, nonce, sig_b64 = state.split(".", 2)
        if not ts.isdigit() or not nonce:
            return False
        payload = f"{ts}.{nonce}"
        expected_sig = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        if not hmac.compare_digest(expected_b64, sig_b64):
            return False
        age = int(time.time()) - int(ts)
        if age < 0 or age > max_age_seconds:
            return False
        return True
    except Exception:
        return False


@router.get("/github/login")
async def github_login():
    """Redirect user to GitHub OAuth consent screen."""
    if not settings.github_client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    state = _build_github_state()
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "user:email read:user repo",
        "state": state,
    }
    url = f"{GITHUB_AUTH_URL}?{urlencode(params)}"
    return {"auth_url": url, "state": state}


@router.post("/github/callback")
async def github_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Exchange GitHub auth code for tokens. Creates account if needed."""
    if not code or not state:
        try:
            body = await request.json()
        except Exception:
            body = {}
        code = code or body.get("code")
        state = state or body.get("state")

    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    if not code:
        raise HTTPException(status_code=400, detail="Missing GitHub OAuth code")
    if not state or not _validate_github_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="GitHub token exchange failed")
        token_data = token_resp.json()
        gh_access_token = token_data.get("access_token")
        if not gh_access_token:
            raise HTTPException(status_code=400, detail=token_data.get("error_description", "No access token"))

        gh_headers = {"Authorization": f"Bearer {gh_access_token}", "Accept": "application/json"}
        user_resp = await client.get(GITHUB_USER_URL, headers=gh_headers)
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub profile")
        gh_user = user_resp.json()

        email = gh_user.get("email")
        if not email:
            emails_resp = await client.get(GITHUB_EMAILS_URL, headers=gh_headers)
            if emails_resp.status_code == 200:
                for em in emails_resp.json():
                    if em.get("primary") and em.get("verified"):
                        email = em["email"]
                        break
        if not email:
            raise HTTPException(status_code=400, detail="No verified email found on GitHub account")

    github_username = gh_user.get("login", "")
    github_id = str(gh_user.get("id", ""))
    full_name = gh_user.get("name") or github_username

    # Enforce one GitHub identity per user account.
    already_linked = db.query(User).filter(User.github_id == github_id).first()
    user = db.query(User).filter(User.email == email).first()
    if already_linked and user and already_linked.id != user.id:
        raise HTTPException(
            status_code=409,
            detail="This GitHub account is already linked to a different user.",
        )
    is_new = False

    if not user:
        is_new = True
        workspace = Workspace(
            name=f"{github_username}",
            slug=f"{github_username.lower()}-{secrets.token_hex(4)}",
        )
        ensure_workspace_profile_defaults(workspace, "generic")
        db.add(workspace)
        db.flush()

        user = User(
            email=email,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            full_name=full_name,
            workspace_id=workspace.id,
            role=UserRole.OWNER,
            is_superuser=False,
            github_id=github_id,
            github_username=github_username,
            github_access_token=gh_access_token,
        )
        db.add(user)
        wallet = TokenWallet(
            workspace_id=workspace.id,
            balance=FREE_EVALUATION_RESERVE_UNITS,
            monthly_credits_included=0,
            monthly_credits_used=0,
            total_credits_purchased=0,
            total_credits_used=0,
        )
        db.add(wallet)
        _record_signup_lead(
            db,
            email=email,
            full_name=full_name,
            workspace_name=workspace.name,
            workspace_id=workspace.id,
            user_id=user.id,
            signup_type="github",
            source="github_oauth",
            request=request,
        )
        db.commit()
        db.refresh(user)
    else:
        # Existing account path: link OAuth credentials instead of creating duplicate account.
        user.github_id = github_id
        user.github_username = github_username
        user.github_access_token = gh_access_token
        user.last_login = datetime.utcnow()
        user.last_activity = datetime.utcnow()
        db.commit()

    _log_security_event(
        db,
        event_type="github_connected",
        event_category="authentication",
        request=request,
        actor=user,
        target_user=user,
        details={"github_username": github_username, "is_new_user": is_new},
    )

    if user.mfa_enabled:
        challenge_token = create_access_token(
            {"user_id": user.id, "workspace_id": user.workspace_id, "type": "github_mfa"},
            expires_delta=timedelta(minutes=10),
        )
        db.commit()
        return {
            "mfa_required": True,
            "mfa_challenge_token": challenge_token,
            "user_id": user.id,
            "workspace_id": user.workspace_id,
            "email": user.email,
            "github_username": github_username,
        }

    tokens = _issue_session_tokens(user=user, request=request, db=db)
    db.commit()

    return {
        **TokenResponse(
            **tokens,
            user_id=user.id,
            workspace_id=user.workspace_id,
            role=user.role.value,
        ).model_dump(),
        "is_new_user": is_new,
        "github_username": github_username,
    }


@router.post("/github/mfa/complete")
async def github_mfa_complete(
    payload: MFACompleteGithubLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    token_data = decode_access_token(payload.challenge_token)
    if not token_data or token_data.get("type") != "github_mfa":
        raise HTTPException(status_code=401, detail="Invalid or expired GitHub MFA challenge")
    user = db.query(User).filter(User.id == token_data.get("user_id")).first()
    if not user or not user.mfa_enabled:
        raise HTTPException(status_code=401, detail="GitHub MFA challenge is no longer valid")
    _consume_mfa_code(
        user=user,
        code=payload.mfa_code,
        db=db,
        request=request,
        audit_context="github_oauth_login",
    )
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    user.last_activity = datetime.utcnow()
    tokens = _issue_session_tokens(user=user, request=request, db=db)
    _log_security_event(
        db,
        event_type="login_succeeded",
        event_category="authentication",
        request=request,
        actor=user,
        target_user=user,
        details={"oauth_provider": "github", "mfa_enabled": True},
    )
    db.commit()
    return {
        **TokenResponse(
            **tokens,
            user_id=user.id,
            workspace_id=user.workspace_id,
            role=user.role.value,
        ).model_dump(),
        "github_username": user.github_username,
    }


@router.get("/connected-accounts", response_model=ConnectedAccountsResponse)
async def connected_accounts(current_user: User = Depends(get_current_user)):
    github_connected = bool(current_user.github_id and current_user.github_access_token)
    return ConnectedAccountsResponse(
        github_configured=bool(settings.github_client_id and settings.github_client_secret and settings.github_redirect_uri),
        github_connected=github_connected,
        github_username=current_user.github_username,
        github_connected_at=current_user.updated_at.isoformat() if github_connected and current_user.updated_at else None,
        github_account_id=current_user.github_id,
    )


@router.delete("/connected-accounts/github")
async def unlink_github_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    if not current_user.github_id:
        raise HTTPException(status_code=400, detail="GitHub is not connected.")
    current_user.github_id = None
    current_user.github_username = None
    current_user.github_access_token = None
    current_user.updated_at = datetime.utcnow()
    _log_security_event(
        db,
        event_type="github_disconnected",
        event_category="authentication",
        request=request,
        actor=current_user,
        target_user=current_user,
    )
    db.commit()
    return {"message": "GitHub account disconnected"}


@router.get("/github/repos")
async def github_repos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """List authenticated user's GitHub repos (for vendor listing connection)."""
    if not current_user.github_access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected. Sign in with GitHub first.")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"Bearer {current_user.github_access_token}",
                "Accept": "application/json",
            },
            params={"sort": "updated", "per_page": 50, "type": "owner"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch repos")
        repos = resp.json()
        _log_security_event(
            db,
            event_type="github_repo_list_fetched",
            event_category="data_access",
            request=request,
            actor=current_user,
            target_user=current_user,
            details={"repo_count": len(repos)},
        )
        db.commit()
        return {
            "repos": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "full_name": r["full_name"],
                    "description": r.get("description"),
                    "html_url": r["html_url"],
                    "stars": r["stargazers_count"],
                    "language": r.get("language"),
                    "updated_at": r["updated_at"],
                    "private": r["private"],
                    "visibility": r.get("visibility", "private" if r.get("private") else "public"),
                    "default_branch": r.get("default_branch"),
                    "permissions": r.get("permissions", {}),
                    "topics": r.get("topics", []),
                }
                for r in repos
            ]
        }
