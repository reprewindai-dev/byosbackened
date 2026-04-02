"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.user import User
from db.models.workspace import Workspace
from db.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier
from core.security import verify_password, get_password_hash, create_access_token
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import uuid
from apps.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    workspace_id: str
    email: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    workspace_id: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create workspace for user
    workspace = Workspace(
        name=f"{user_data.email}'s Workspace",
        slug=f"workspace-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(workspace)
    db.flush()

    # Create user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        workspace_id=workspace.id,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        workspace_id=user.workspace_id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login and get access token."""
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Create access token
    access_token = create_access_token(
        data={
            "sub": user.id,
            "user_id": user.id,
            "email": user.email,
            "workspace_id": user.workspace_id,
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        workspace_id=user.workspace_id,
        email=user.email,
    )


@router.post("/login-json", response_model=TokenResponse)
async def login_json(
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    """Login with JSON body (for frontend)."""
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Create access token
    access_token = create_access_token(
        data={
            "sub": user.id,
            "user_id": user.id,
            "email": user.email,
            "workspace_id": user.workspace_id,
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        workspace_id=user.workspace_id,
        email=user.email,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user),
):
    """Get current user information."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        workspace_id=user.workspace_id,
    )
