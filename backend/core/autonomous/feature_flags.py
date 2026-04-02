"""Feature flags and kill switches for autonomous features."""
from typing import Dict, Optional
from core.config import get_settings
import os
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class FeatureFlags:
    """
    Feature flags and kill switches.
    
    Allows disabling autonomous features quickly in production.
    Can be controlled via environment variables or database.
    """
    
    def __init__(self):
        # Load from environment variables (fastest way to disable)
        # SAFE DEFAULT: All features OFF by default (must explicitly enable)
        # This prevents accidental autonomous behavior in production
        self._flags = {
            "autonomous_routing_enabled": os.getenv("AUTONOMOUS_ROUTING_ENABLED", "false").lower() == "true",
            "ml_cost_prediction_enabled": os.getenv("ML_COST_PREDICTION_ENABLED", "false").lower() == "true",
            "ml_routing_optimizer_enabled": os.getenv("ML_ROUTING_OPTIMIZER_ENABLED", "false").lower() == "true",
            "model_retraining_enabled": os.getenv("MODEL_RETRAINING_ENABLED", "false").lower() == "true",
            "canary_deployment_enabled": os.getenv("CANARY_DEPLOYMENT_ENABLED", "false").lower() == "true",
            "auto_remediation_enabled": os.getenv("AUTO_REMEDIATION_ENABLED", "false").lower() == "true",
            "edge_routing_enabled": os.getenv("EDGE_ROUTING_ENABLED", "false").lower() == "true",
            "traffic_prediction_enabled": os.getenv("TRAFFIC_PREDICTION_ENABLED", "false").lower() == "true",
        }
    
    def is_enabled(self, feature: str) -> bool:
        """
        Check if feature is enabled.
        
        Args:
            feature: Feature name (e.g., "autonomous_routing_enabled")
        
        Returns:
            True if enabled, False if disabled
        """
        return self._flags.get(feature, False)
    
    def disable(self, feature: str):
        """Disable a feature (runtime override)."""
        self._flags[feature] = False
        logger.warning(f"Feature flag disabled: {feature}")
    
    def enable(self, feature: str):
        """Enable a feature (runtime override)."""
        self._flags[feature] = True
        logger.info(f"Feature flag enabled: {feature}")
    
    def get_all_flags(self) -> Dict[str, bool]:
        """Get all feature flags."""
        return self._flags.copy()
    
    def disable_all_autonomous(self):
        """Emergency kill switch: disable all autonomous features."""
        autonomous_features = [
            "autonomous_routing_enabled",
            "ml_cost_prediction_enabled",
            "ml_routing_optimizer_enabled",
            "model_retraining_enabled",
            "canary_deployment_enabled",
            "auto_remediation_enabled",
            "edge_routing_enabled",
            "traffic_prediction_enabled",
        ]
        for feature in autonomous_features:
            self.disable(feature)
        logger.critical("EMERGENCY: All autonomous features disabled via kill switch")


# Global feature flags
_feature_flags = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    """Get global feature flags instance."""
    return _feature_flags
