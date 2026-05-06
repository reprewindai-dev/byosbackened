"""FastAPI dependencies."""
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from db.session import get_db
from core.security import decode_access_token
from typing import Optional


def _secure_compare(val1: str, val2: str) -> bool:
    """Timing-safe string comparison to prevent timing attacks."""
    return hmac.compare_digest(val1.encode(), val2.encode())


@dataclass(frozen=True)
class APIKeyPrincipal:
    workspace_id: str
    user_id: str
    api_key_id: str
    scopes: set[str]


async def require_api_key_principal(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> APIKeyPrincipal:
    """Require a live workspace API key and return its scoped principal.

    This dependency intentionally rejects JWT bearer tokens. It is for timers,
    workers, and machine agents, where drift control depends on issuing a
    purpose-specific key instead of reusing an owner session.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    try:
        scheme, token = authorization.split()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header") from exc
    if scheme.lower() != "bearer" or not token.startswith("byos_"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Automation API key required")

    from db.models import APIKey, User

    key_hash = hashlib.sha256(token.encode()).hexdigest()
    api_key = db.query(APIKey).filter(APIKey.key_hash == key_hash, APIKey.is_active.is_(True)).first()
    if not api_key:
        _secure_compare("dummy_hash_for_timing", hashlib.sha256(b"dummy").hexdigest())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    owner = db.query(User).filter(User.id == api_key.user_id, User.is_active.is_(True)).first()
    if not owner:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key owner inactive")

    api_key.last_used_at = datetime.utcnow()
    db.commit()
    return APIKeyPrincipal(
        workspace_id=api_key.workspace_id,
        user_id=api_key.user_id,
        api_key_id=api_key.id,
        scopes={str(scope).upper() for scope in (api_key.scopes or [])},
    )


def require_api_key_scope(scope: str):
    required = scope.upper()

    async def _dependency(principal: APIKeyPrincipal = Depends(require_api_key_principal)) -> APIKeyPrincipal:
        if required not in principal.scopes and "ADMIN" not in principal.scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{required} scope required")
        return principal

    return _dependency


async def get_current_workspace_id(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> str:
    """Get current workspace ID from JWT token or API key."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    # API key path (prefix: byos_)
    if token.startswith("byos_"):
        from db.models import APIKey, User
        from datetime import datetime
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        api_key = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        ).first()
        if not api_key:
            # Use constant-time comparison to prevent timing attacks on key enumeration
            _secure_compare("dummy_hash_for_timing", hashlib.sha256(b"dummy").hexdigest())
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")
        # Verify workspace owner is active
        workspace_owner = db.query(User).filter(
            User.workspace_id == api_key.workspace_id,
            User.is_active == True
        ).first()
        if not workspace_owner:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Workspace inactive")
        api_key.last_used_at = datetime.utcnow()
        db.commit()
        return api_key.workspace_id

    # JWT path
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    workspace_id = payload.get("workspace_id")
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace ID missing in token",
        )
    
    # Verify user is still active (token could be valid but user suspended)
    user_id = payload.get("user_id")
    if user_id:
        from db.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account inactive or deleted",
            )

    return workspace_id


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Get the authenticated User object from JWT token."""
    from db.models import User, UserStatus
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User ID missing in token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active or user.status == UserStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account inactive or suspended")

    return user


async def require_admin(current_user=Depends(get_current_user)):
    """Require admin or owner role."""
    from db.models import UserRole
    if current_user.role not in (UserRole.ADMIN, UserRole.OWNER) and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def require_superuser(current_user=Depends(get_current_user)):
    """Require superuser."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    return current_user
