"""
Core dependency injection and authentication utilities.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.authentication import AuthCredentials
from sqlalchemy.orm import Session
from db.session import get_db
from typing import Optional

security = HTTPBearer()


async def get_current_user(
    credentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    # TODO: Implement JWT verification
    return {"token": token}


async def get_current_workspace(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get current workspace for authenticated user."""
    # TODO: Implement workspace resolution
    return {"workspace_id": "default", "user": current_user}
