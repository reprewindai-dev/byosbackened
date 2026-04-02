"""FastAPI dependencies."""
import hashlib
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from db.session import get_db
from core.security import decode_access_token
from typing import Optional


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
        from db.models import APIKey
        from datetime import datetime
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        api_key = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        ).first()
        if not api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")
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
