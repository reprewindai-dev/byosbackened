"""Seed script for initial apps."""

from sqlalchemy.orm import Session
from db.models.app import App
from db.models.app_workspace import AppWorkspace
from db.models.workspace import Workspace
import logging

logger = logging.getLogger(__name__)


def seed_apps(db: Session):
    """Seed initial apps (TrapMaster Pro, ClipCrafter)."""
    apps_data = [
        {
            "name": "TrapMaster Pro",
            "slug": "trapmaster-pro",
            "description": "Professional music production and audio editing app",
            "icon_url": None,
            "is_active": True,
            "config": {},
        },
        {
            "name": "ClipCrafter",
            "slug": "clipcrafter",
            "description": "Video editing and clip creation app",
            "icon_url": None,
            "is_active": True,
            "config": {},
        },
    ]

    created_count = 0
    for app_data in apps_data:
        # Check if app already exists
        existing = db.query(App).filter(App.slug == app_data["slug"]).first()
        if existing:
            logger.info(f"App '{app_data['slug']}' already exists, skipping")
            continue

        app = App(**app_data)
        db.add(app)
        created_count += 1
        logger.info(f"Created app: {app_data['name']} ({app_data['slug']})")

    db.commit()

    if created_count > 0:
        logger.info(f"✅ Seeded {created_count} apps")
    else:
        logger.info("✅ All apps already exist")

    return created_count


def enable_apps_for_workspace(db: Session, workspace_id: str):
    """Enable all active apps for a workspace."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        logger.warning(f"Workspace '{workspace_id}' not found, skipping app enablement")
        return 0

    apps = db.query(App).filter(App.is_active == True).all()
    enabled_count = 0

    for app in apps:
        # Check if already enabled
        existing = (
            db.query(AppWorkspace)
            .filter(AppWorkspace.app_id == app.id, AppWorkspace.workspace_id == workspace_id)
            .first()
        )

        if existing:
            if not existing.is_active:
                existing.is_active = True
                enabled_count += 1
                logger.info(f"Re-enabled app '{app.slug}' for workspace '{workspace.slug}'")
            else:
                logger.debug(f"App '{app.slug}' already enabled for workspace '{workspace.slug}'")
            continue

        # Create new app-workspace link
        app_workspace = AppWorkspace(
            app_id=app.id,
            workspace_id=workspace_id,
            is_active=True,
            config={},
        )
        db.add(app_workspace)
        enabled_count += 1
        logger.info(f"Enabled app '{app.slug}' for workspace '{workspace.slug}'")

    db.commit()

    if enabled_count > 0:
        logger.info(f"✅ Enabled {enabled_count} apps for workspace '{workspace.slug}'")

    return enabled_count


def seed_all(db: Session, workspace_id: str = None):
    """Seed apps and optionally enable them for a workspace."""
    seed_apps(db)

    if workspace_id:
        enable_apps_for_workspace(db, workspace_id)
    else:
        logger.info("No workspace_id provided, skipping app enablement")


if __name__ == "__main__":
    # For running directly
    from db.session import SessionLocal
    import sys

    db = SessionLocal()
    try:
        workspace_id = sys.argv[1] if len(sys.argv) > 1 else None
        seed_all(db, workspace_id)
    finally:
        db.close()
