"""Authentication dependencies for FastAPI."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Optional

security = HTTPBearer()


async def get_current_user_token(
    credentials = Depends(security)
) -> str:
    """Extract and return the current user token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return credentials.credentials
