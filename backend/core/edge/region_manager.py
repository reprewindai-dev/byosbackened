"""Multi-region deployment manager."""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import Deployment
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class RegionManager:
    """
    Manage multi-region deployments.
    
    Edge-aware by default - deploys to multiple regions automatically.
    """

    # Supported regions
    REGIONS = {
        "us-east": {"name": "US East", "lat": 40.7128, "lon": -74.0060},
        "eu-west": {"name": "EU West", "lat": 52.5200, "lon": 13.4050},
        "asia-pacific": {"name": "Asia Pacific", "lat": 1.3521, "lon": 103.8198},
    }

    def __init__(self):
        self.active_regions: Dict[str, bool] = {
            region: True for region in self.REGIONS.keys()
        }

    def get_regions(self) -> List[str]:
        """Get list of active regions."""
        return [region for region, active in self.active_regions.items() if active]

    def deploy_to_region(
        self,
        db: Session,
        workspace_id: str,
        region: str,
        service_type: str,  # "api", "worker"
    ) -> Deployment:
        """Record deployment to region."""
        deployment = Deployment(
            workspace_id=workspace_id,
            region=region,
            service_type=service_type,
            status="active",
            deployed_at=datetime.utcnow(),
        )
        db.add(deployment)
        db.commit()
        db.refresh(deployment)
        
        logger.info(f"Deployed {service_type} to {region} for workspace {workspace_id}")
        
        return deployment

    def get_deployments(
        self,
        db: Session,
        workspace_id: str,
    ) -> List[Deployment]:
        """Get all deployments for workspace."""
        return db.query(Deployment).filter(
            Deployment.workspace_id == workspace_id,
            Deployment.status == "active",
        ).all()
