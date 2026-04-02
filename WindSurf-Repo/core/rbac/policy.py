"""RBAC policy system for role-based access control."""

from enum import Enum
from typing import Dict, List, Optional, Set

from db.models.workspace_membership import WorkspaceRole


class Permission(str, Enum):
    """System permissions."""
    # Workspace permissions
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_WRITE = "workspace:write"
    WORKSPACE_DELETE = "workspace:delete"
    WORKSPACE_MANAGE_MEMBERS = "workspace:manage_members"
    WORKSPACE_MANAGE_APPS = "workspace:manage_apps"
    WORKSPACE_MANAGE_SETTINGS = "workspace:manage_settings"
    
    # App permissions
    APP_ENABLE = "app:enable"
    APP_DISABLE = "app:disable"
    APP_CONFIG = "app:config"
    
    # User permissions
    USER_INVITE = "user:invite"
    USER_REMOVE = "user:remove"
    USER_UPDATE_ROLE = "user:update_role"
    
    # Data permissions
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"
    DATA_DELETE = "data:delete"
    
    # Admin permissions
    AUDIT_READ = "audit:read"
    SSO_MANAGE = "sso:manage"
    SCIM_MANAGE = "scim:manage"
    RETENTION_MANAGE = "retention:manage"


# Role permission mappings
ROLE_PERMISSIONS: Dict[WorkspaceRole, Set[Permission]] = {
    WorkspaceRole.GUEST: {
        Permission.WORKSPACE_READ,
    },
    WorkspaceRole.VIEWER: {
        Permission.WORKSPACE_READ,
        Permission.DATA_EXPORT,
    },
    WorkspaceRole.MEMBER: {
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_WRITE,
        Permission.APP_ENABLE,
        Permission.APP_DISABLE,
        Permission.APP_CONFIG,
        Permission.DATA_EXPORT,
        Permission.DATA_IMPORT,
    },
    WorkspaceRole.ADMIN: {
        # Include all member permissions
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_WRITE,
        Permission.APP_ENABLE,
        Permission.APP_DISABLE,
        Permission.APP_CONFIG,
        Permission.DATA_EXPORT,
        Permission.DATA_IMPORT,
        # Admin-specific permissions
        Permission.WORKSPACE_DELETE,
        Permission.WORKSPACE_MANAGE_MEMBERS,
        Permission.WORKSPACE_MANAGE_APPS,
        Permission.WORKSPACE_MANAGE_SETTINGS,
        Permission.USER_INVITE,
        Permission.USER_REMOVE,
        Permission.USER_UPDATE_ROLE,
        Permission.DATA_DELETE,
        Permission.AUDIT_READ,
        Permission.SSO_MANAGE,
        Permission.SCIM_MANAGE,
        Permission.RETENTION_MANAGE,
    },
}


def role_at_least(role: WorkspaceRole, minimum_role: WorkspaceRole) -> bool:
    """Check if a role meets or exceeds the minimum required role."""
    role_hierarchy = {
        WorkspaceRole.GUEST: 0,
        WorkspaceRole.VIEWER: 1,
        WorkspaceRole.MEMBER: 2,
        WorkspaceRole.ADMIN: 3,
    }
    
    return role_hierarchy.get(role, 0) >= role_hierarchy.get(minimum_role, 0)


def get_permissions_for_role(role: WorkspaceRole) -> Set[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(
    user_role: WorkspaceRole,
    required_permission: Permission,
    context: Optional[Dict] = None,
) -> bool:
    """Check if a user role has a specific permission."""
    permissions = get_permissions_for_role(user_role)
    return required_permission in permissions


def has_any_permission(
    user_role: WorkspaceRole,
    required_permissions: List[Permission],
    context: Optional[Dict] = None,
) -> bool:
    """Check if a user role has any of the required permissions."""
    permissions = get_permissions_for_role(user_role)
    return any(perm in permissions for perm in required_permissions)


def has_all_permissions(
    user_role: WorkspaceRole,
    required_permissions: List[Permission],
    context: Optional[Dict] = None,
) -> bool:
    """Check if a user role has all of the required permissions."""
    permissions = get_permissions_for_role(user_role)
    return all(perm in permissions for perm in required_permissions)


def can_access_resource(
    user_role: WorkspaceRole,
    resource_type: str,
    action: str,
    resource_id: Optional[str] = None,
    context: Optional[Dict] = None,
) -> bool:
    """Check if a user can access a specific resource with an action."""
    # Map resource+action to permissions
    resource_permission_map = {
        ("workspace", "read"): Permission.WORKSPACE_READ,
        ("workspace", "write"): Permission.WORKSPACE_WRITE,
        ("workspace", "delete"): Permission.WORKSPACE_DELETE,
        ("workspace", "manage_members"): Permission.WORKSPACE_MANAGE_MEMBERS,
        ("workspace", "manage_apps"): Permission.WORKSPACE_MANAGE_APPS,
        ("workspace", "manage_settings"): Permission.WORKSPACE_MANAGE_SETTINGS,
        ("app", "enable"): Permission.APP_ENABLE,
        ("app", "disable"): Permission.APP_DISABLE,
        ("app", "config"): Permission.APP_CONFIG,
        ("user", "invite"): Permission.USER_INVITE,
        ("user", "remove"): Permission.USER_REMOVE,
        ("user", "update_role"): Permission.USER_UPDATE_ROLE,
        ("data", "export"): Permission.DATA_EXPORT,
        ("data", "import"): Permission.DATA_IMPORT,
        ("data", "delete"): Permission.DATA_DELETE,
        ("audit", "read"): Permission.AUDIT_READ,
        ("sso", "manage"): Permission.SSO_MANAGE,
        ("scim", "manage"): Permission.SCIM_MANAGE,
        ("retention", "manage"): Permission.RETENTION_MANAGE,
    }
    
    permission = resource_permission_map.get((resource_type, action))
    if not permission:
        return False
    
    return has_permission(user_role, permission, context)
