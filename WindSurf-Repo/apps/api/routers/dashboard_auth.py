"""
Simple Authentication for Dashboards
==================================

Basic authentication system for admin and user dashboards.
In production, this would use proper JWT tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
from typing import Optional

from core.config import get_settings

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
settings = get_settings()

# Simple user database (in production, use real database)
USERS = {
    "admin": {
        "id": "admin",
        "username": "admin",
        "email": "admin@byos-ai.com",
        "role": "admin",
        "password_hash": "admin123"  # In production, use proper hashing
    },
    "user": {
        "id": "user",
        "username": "user", 
        "email": "user@byos-ai.com",
        "role": "user",
        "password_hash": "user123"  # In production, use proper hashing
    }
}

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict

class User(BaseModel):
    id: str
    username: str
    email: str
    role: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except jwt.PyJWTError:
        return None

def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = USERS.get(username)
    if user is None:
        raise credentials_exception
    
    return user

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Authenticate user and return access token."""
    
    user = USERS.get(login_data.username)
    if not user or user["password_hash"] != login_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}, 
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,  # 30 minutes in seconds
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    )

@router.get("/me", response_model=User)
async def get_current_user(current_user: dict = Depends(get_current_user_from_token)):
    """Get current user information."""
    return User(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"]
    )

@router.post("/logout")
async def logout():
    """Logout user (client-side token removal)."""
    return {"message": "Successfully logged out"}

# Dependency functions for dashboard routes
async def get_admin_user(current_user: dict = Depends(get_current_user_from_token)) -> dict:
    """Get admin user (admin only)."""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_any_user(current_user: dict = Depends(get_current_user_from_token)) -> dict:
    """Get any authenticated user."""
    return current_user
