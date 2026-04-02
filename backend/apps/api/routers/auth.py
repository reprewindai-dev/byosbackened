"""Authentication endpoints: register, login, logout, refresh, /me, MFA, API keys."""
import hashlib
import hmac
import os
import secrets
import pyotp
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.config import get_settings
from core.security import create_access_token, decode_access_token, get_password_hash, verify_password
from db.session import get_db
from db.models import User, UserRole, UserStatus, UserSession, APIKey, Workspace
from apps.api.deps import get_current_user

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])

_API_KEY_PREFIX = "byos_"


# ─── Schemas ────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    workspace_name: str
    invite_code: Optional[str] = None


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


class RefreshRequest(BaseModel):
    refresh_token: str


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


# ─── Helpers ────────────────────────────────────────────────────────────────

def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


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


# ─── Auth Routes ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new workspace + owner user."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    workspace = Workspace(
        name=payload.workspace_name,
        slug=payload.workspace_name.lower().replace(" ", "-") + "-" + secrets.token_hex(4),
    )
    db.add(workspace)
    db.flush()

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        workspace_id=workspace.id,
        role=UserRole.OWNER,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    tokens = _create_tokens(user)
    return TokenResponse(
        **tokens,
        user_id=user.id,
        workspace_id=user.workspace_id,
        role=user.role.value,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate user, enforce MFA if enabled."""
    user = db.query(User).filter(User.email == payload.email).first()
    credentials_error = HTTPException(status_code=401, detail="Invalid credentials")

    if not user:
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
        db.commit()
        raise credentials_error

    if user.mfa_enabled:
        if not payload.mfa_code:
            raise HTTPException(status_code=401, detail="MFA code required")
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(payload.mfa_code, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid MFA code")

    user.failed_login_attempts = 0
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
        UserSession.is_active == True,
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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Invalidate all active sessions for current user."""
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True,
    ).update({"is_active": False})
    db.commit()


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    """Return authenticated user profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "status": current_user.status.value,
        "workspace_id": current_user.workspace_id,
        "mfa_enabled": current_user.mfa_enabled,
        "is_superuser": current_user.is_superuser,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "created_at": current_user.created_at.isoformat(),
    }


# ─── MFA Routes ───────────────────────────────────────────────────────────────

@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a new TOTP secret for MFA setup."""
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA already enabled")
    secret = pyotp.random_base32()
    current_user.mfa_secret = secret
    db.commit()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name=settings.app_name)
    return MFASetupResponse(
        secret=secret,
        provisioning_uri=uri,
        qr_url=f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={uri}",
    )


@router.post("/mfa/verify")
async def mfa_verify(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm and activate MFA after scanning QR code."""
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="Run /auth/mfa/setup first")
    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.mfa_enabled = True
    db.commit()
    return {"message": "MFA enabled successfully"}


@router.delete("/mfa/disable")
async def mfa_disable(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable MFA — requires valid code to prevent accidental lockout."""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")
    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    db.commit()
    return {"message": "MFA disabled"}


# ─── API Key Routes ───────────────────────────────────────────────────────────

@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new workspace-scoped API key."""
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
        scopes=payload.scopes,
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
        APIKey.is_active == True,
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
