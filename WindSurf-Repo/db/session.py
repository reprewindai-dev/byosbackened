"""Database session management."""

from contextvars import ContextVar
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Tenant enforcement system
# Context variable to track current tenant
current_tenant_id: ContextVar[Optional[str]] = ContextVar('current_tenant_id', default=None)
current_workspace_id: ContextVar[Optional[str]] = ContextVar('current_workspace_id', default=None)


def get_current_tenant_id() -> Optional[str]:
    """Get the current tenant ID from context."""
    return current_tenant_id.get()


def get_current_workspace_id() -> Optional[str]:
    """Get the current workspace ID from context."""
    return current_workspace_id.get()


def set_current_tenant_id(tenant_id: str) -> None:
    """Set the current tenant ID in context."""
    current_tenant_id.set(tenant_id)


def set_current_workspace_id(workspace_id: str) -> None:
    """Set the current workspace ID in context."""
    current_workspace_id.set(workspace_id)


def clear_tenant_context() -> None:
    """Clear the current tenant context."""
    current_tenant_id.set(None)
    current_workspace_id.set(None)


def tenant_enforcement_disabled() -> bool:
    """Check if tenant enforcement is disabled (for system operations).
    
    In production, this should be controlled by environment variables
    and only enabled for specific system operations.
    """
    # For now, return False to enforce tenant isolation
    # In a real system, this might check for a system flag or environment variable
    return False


def enforce_tenant_access(resource_tenant_id: Optional[str] = None) -> None:
    """Enforce tenant access rules.
    
    Args:
        resource_tenant_id: Tenant ID of the resource being accessed
        
    Raises:
        PermissionError: If tenant access is not allowed
    """
    if tenant_enforcement_disabled():
        return
    
    current_id = get_current_tenant_id()
    if not current_id:
        raise PermissionError("No tenant context established")
    
    if resource_tenant_id and resource_tenant_id != current_id:
        raise PermissionError(f"Access denied: tenant {current_id} cannot access tenant {resource_tenant_id}")


def enforce_workspace_access(resource_workspace_id: Optional[str] = None) -> None:
    """Enforce workspace access rules.
    
    Args:
        resource_workspace_id: Workspace ID of the resource being accessed
        
    Raises:
        PermissionError: If workspace access is not allowed
    """
    if tenant_enforcement_disabled():
        return
    
    current_id = get_current_workspace_id()
    if not current_id:
        raise PermissionError("No workspace context established")
    
    if resource_workspace_id and resource_workspace_id != current_id:
        raise PermissionError(f"Access denied: workspace {current_id} cannot access workspace {resource_workspace_id}")


class TenantContext:
    """Context manager for tenant enforcement."""
    
    def __init__(self, tenant_id: str, workspace_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self.token_tenant = None
        self.token_workspace = None
    
    def __enter__(self):
        # Store current context
        self.token_tenant = current_tenant_id.set(self.tenant_id)
        if self.workspace_id:
            self.token_workspace = current_workspace_id.set(self.workspace_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        if self.token_tenant is not None:
            current_tenant_id.reset(self.token_tenant)
        if self.token_workspace is not None:
            current_workspace_id.reset(self.token_workspace)


def with_tenant_context(tenant_id: str, workspace_id: Optional[str] = None):
    """Decorator to run function with tenant context.
    
    Args:
        tenant_id: Tenant ID to set
        workspace_id: Optional workspace ID to set
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with TenantContext(tenant_id, workspace_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def check_tenant_isolation(query, tenant_id_field: str = 'tenant_id'):
    """Add tenant isolation filter to a database query.
    
    Args:
        query: SQLAlchemy query object
        tenant_id_field: Name of the tenant ID field in the model
        
    Returns:
        Query with tenant filter applied
    """
    if tenant_enforcement_disabled():
        return query
    
    current_id = get_current_tenant_id()
    if current_id:
        return query.filter(getattr(query.column_descriptions[0]['type'], tenant_id_field) == current_id)
    
    return query


def check_workspace_isolation(query, workspace_id_field: str = 'workspace_id'):
    """Add workspace isolation filter to a database query.
    
    Args:
        query: SQLAlchemy query object
        workspace_id_field: Name of the workspace ID field in the model
        
    Returns:
        Query with workspace filter applied
    """
    if tenant_enforcement_disabled():
        return query
    
    current_id = get_current_workspace_id()
    if current_id:
        return query.filter(getattr(query.column_descriptions[0]['type'], workspace_id_field) == current_id)
    
    return query
