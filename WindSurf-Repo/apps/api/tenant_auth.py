"""Tenant authentication dependencies for multi-tenant API."""

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
import hashlib
import hmac
from db.session import get_db, set_tenant_context
from core.security import get_password_hash
from core.config import get_settings

settings = get_settings()


def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage."""
    return hmac.new(
        settings.secret_key.encode('utf-8'),
        api_key.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify API key against stored hash."""
    return hmac.compare_digest(
        hash_api_key(api_key),
        hashed_key
    )


async def get_tenant_from_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> str:
    """Extract and validate tenant from API key."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Hash the provided key for comparison
    hashed_key = hash_api_key(x_api_key)
    
    # Query tenant by hashed API key
    from db.models.tenant import Tenant
    tenant = db.query(Tenant).filter(
        Tenant.api_key_hash == hashed_key,
        Tenant.is_active == True
    ).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Set tenant context for database session
    set_tenant_context(tenant.tenant_id)
    
    return tenant.tenant_id


async def get_tenant_info(
    tenant_id: str = Depends(get_tenant_from_api_key),
    db: Session = Depends(get_db)
) -> dict:
    """Get full tenant information for usage tracking."""
    from db.models.tenant import Tenant
    
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return {
        "tenant_id": tenant.tenant_id,
        "name": tenant.name,
        "execution_limit": tenant.execution_limit,
        "daily_execution_count": tenant.daily_execution_count,
        "is_active": tenant.is_active
    }
