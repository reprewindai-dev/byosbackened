"""Provider version management."""
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ProviderVersionManager:
    """Manage provider versions."""

    def __init__(self):
        self.provider_versions: Dict[str, Dict[str, any]] = {}

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

    def get_migration_path(self, provider: str, from_version: str, to_version: str) -> Optional[str]:
        """Get migration path between versions."""
        # TODO: Implement migration scripts
        return f"Migrate {provider} from {from_version} to {to_version}"


# Global version manager
_version_manager = ProviderVersionManager()


def get_version_manager() -> ProviderVersionManager:
    """Get version manager."""
    return _version_manager
