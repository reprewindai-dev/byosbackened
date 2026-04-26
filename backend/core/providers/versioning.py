"""Provider version management."""
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ProviderVersionManager:
    """Manage provider versions."""

    def __init__(self):
        self.provider_versions: Dict[str, Dict[str, Any]] = {}

    def register_version(
        self,
        provider: str,
        version: str,
        api_compatible: bool = True,
        deprecated: bool = False,
    ):
        """Register provider version."""
        if provider not in self.provider_versions:
            self.provider_versions[provider] = {}
        
        self.provider_versions[provider][version] = {
            "api_compatible": api_compatible,
            "deprecated": deprecated,
        }
        
        logger.info(f"Registered provider version: {provider} v{version}")

    def get_latest_version(self, provider: str) -> Optional[str]:
        """Get latest version of provider."""
        if provider not in self.provider_versions:
            return None
        
        versions = list(self.provider_versions[provider].keys())
        # Simple: return last registered (can be enhanced with semver)
        return versions[-1] if versions else None

    def is_deprecated(self, provider: str, version: str) -> bool:
        """Check if version is deprecated."""
        if provider not in self.provider_versions:
            return False
        if version not in self.provider_versions[provider]:
            return False
        return self.provider_versions[provider][version].get("deprecated", False)

    def get_migration_path(self, provider: str, from_version: str, to_version: str) -> Optional[dict]:
        """Get migration path between versions with detailed steps."""
        if provider not in self.provider_versions:
            return None
        
        if from_version not in self.provider_versions[provider]:
            return None
        
        if to_version not in self.provider_versions[provider]:
            return None
        
        # Check if versions are API compatible
        from_compat = self.provider_versions[provider][from_version].get("api_compatible", True)
        to_compat = self.provider_versions[provider][to_version].get("api_compatible", True)
        
        # Generate migration path
        migration = {
            "provider": provider,
            "from_version": from_version,
            "to_version": to_version,
            "path_type": "automatic" if (from_compat and to_compat) else "manual",
            "steps": [],
            "compatibility": {
                "from_compatible": from_compat,
                "to_compatible": to_compat,
            },
            "deprecated_warnings": [],
        }
        
        # Check for deprecated versions in path
        if self.is_deprecated(provider, from_version):
            migration["deprecated_warnings"].append(f"Source version {from_version} is deprecated")
        if self.is_deprecated(provider, to_version):
            migration["deprecated_warnings"].append(f"Target version {to_version} is deprecated")
        
        # Add migration steps
        if from_compat and to_compat:
            migration["steps"] = [
                {"step": 1, "action": "backup_current_config", "description": f"Backup current {provider} v{from_version} configuration"},
                {"step": 2, "action": "update_provider_version", "description": f"Update to {provider} v{to_version}"},
                {"step": 3, "action": "verify_api_compatibility", "description": "Verify API compatibility and run tests"},
                {"step": 4, "action": "deploy", "description": "Deploy to production"},
            ]
        else:
            migration["steps"] = [
                {"step": 1, "action": "backup_current_config", "description": f"Backup current {provider} v{from_version} configuration"},
                {"step": 2, "action": "review_api_changes", "description": f"Review API changes between v{from_version} and v{to_version}"},
                {"step": 3, "action": "update_client_code", "description": "Update client code for API changes"},
                {"step": 4, "action": "test_in_staging", "description": "Test thoroughly in staging environment"},
                {"step": 5, "action": "deploy", "description": "Deploy to production with monitoring"},
            ]
        
        return migration
    
    def can_migrate_directly(self, provider: str, from_version: str, to_version: str) -> bool:
        """Check if direct migration is possible."""
        path = self.get_migration_path(provider, from_version, to_version)
        if not path:
            return False
        return path["path_type"] == "automatic"
    
    def get_upgrade_path(self, provider: str, current_version: str) -> Optional[str]:
        """Get recommended upgrade path from current version to latest."""
        latest = self.get_latest_version(provider)
        if not latest or latest == current_version:
            return None
        
        migration = self.get_migration_path(provider, current_version, latest)
        if migration:
            return f"Recommended: Upgrade {provider} from v{current_version} to v{latest}"
        return None


# Global version manager
_version_manager = ProviderVersionManager()


def get_version_manager() -> ProviderVersionManager:
    """Get version manager."""
    return _version_manager
