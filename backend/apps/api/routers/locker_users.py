"""
LockerPhycer Users Router - Integrated into BYOS Backend

User management, profile operations, and user activity tracking.
Originally from LockerPhycer, now part of unified BYOS backend.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr

from db.session import get_db
from db.models import User, UserRole, UserStatus, UserSession
from apps.api.deps import get_current_user
from core.security import get_password_hash

router = APIRouter(prefix="/locker/users", tags=["locker-users"])


# ─── Pydantic Schemas ───────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: UserRole
    status: UserStatus
    is_active: bool
    mfa_enabled: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER


class UserActivityResponse(BaseModel):
    user_id: str
    sessions: List[dict]
    total_sessions: int
    active_sessions: int


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List users with filtering (admin only)"""
    
    # Check admin permissions
    if current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    query = db.query(User).filter(User.workspace_id == current_user.workspace_id)
    
    if role:
        query = query.filter(User.role == role)
    
    if status:
        query = query.filter(User.status == status)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user by ID"""
    
    # Users can only view their own profile or admins can view any
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other user's data"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.workspace_id == current_user.workspace_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    # Check permissions
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify other user's data"
        )
    
    # Only admins can change roles
    if update_data.role and current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change user roles"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.workspace_id == current_user.workspace_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if update_data.full_name is not None:
        user.full_name = update_data.full_name
    if update_data.role is not None:
        user.role = update_data.role
    if update_data.status is not None:
        user.status = update_data.status
    if update_data.is_active is not None:
        user.is_active = update_data.is_active
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/", response_model=UserResponse)
def create_user(
    user_data: UserCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)"""
    
    if current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        workspace_id=current_user.workspace_id,
        status=UserStatus.ACTIVE
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete/deactivate a user (admin only)"""
    
    if current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.workspace_id == current_user.workspace_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Soft delete - deactivate instead of hard delete
    user.is_active = False
    user.status = UserStatus.INACTIVE
    db.commit()
    
    return {"message": "User deactivated successfully"}


@router.get("/{user_id}/activity")
def get_user_activity(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user activity and sessions"""
    
    # Check permissions
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other user's activity"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.workspace_id == current_user.workspace_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get sessions
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id
    ).order_by(UserSession.last_accessed.desc()).all()
    
    session_data = []
    for session in sessions:
        session_data.append({
            "id": session.id,
            "is_active": session.is_active,
            "created_at": session.created_at,
            "last_accessed": session.last_accessed,
            "expires_at": session.expires_at,
            "ip_address": session.ip_address
        })
    
    return {
        "user_id": user_id,
        "total_sessions": len(sessions),
        "active_sessions": sum(1 for s in sessions if s.is_active),
        "sessions": session_data
    }


@router.post("/{user_id}/sessions/revoke")
def revoke_all_sessions(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke all user sessions (force logout)"""
    
    # Check permissions
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke other user's sessions"
        )
    
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_active == True
    ).all()
    
    for session in sessions:
        session.is_active = False
    
    db.commit()
    
    return {
        "message": f"Revoked {len(sessions)} active sessions",
        "revoked_count": len(sessions)
    }
