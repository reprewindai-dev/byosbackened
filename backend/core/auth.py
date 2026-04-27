"""Auth re-exports — thin shim so 'from core.auth import ...' works everywhere."""

from apps.api.deps import get_current_workspace_id as get_current_workspace
from apps.api.deps import get_current_user, require_admin, require_superuser

__all__ = [
    "get_current_workspace",
    "get_current_user",
    "require_admin",
    "require_superuser",
]
