"""App context middleware - extracts and validates app context from URL."""

from fastapi import Request, HTTPException, status
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models.app import App
from db.models.app_workspace import AppWorkspace
from db.models.workspace import Workspace
from core.config import get_settings
import logging
import re

logger = logging.getLogger(__name__)
settings = get_settings()


class AppContextMiddleware(BaseHTTPMiddleware):
    """Extract app context from URL and validate app access."""

    async def dispatch(self, request: Request, call_next):
        """Extract app slug from URL and validate access."""
        # Skip for non-app routes
        # Routes that don't need app context:
        # - /health, /, /metrics
        # - /api/v1/apps/* (app management)
        # - /api/v1/workspaces/* (workspace management)
        # - /api/v1/shared/* (shared services)
        # - /api/v1/auth/* (authentication)

        path = request.url.path

        # Skip app context for these paths
        skip_paths = [
            "/health",
            "/",
            "/metrics",
            f"{settings.api_prefix}/apps",
            f"{settings.api_prefix}/workspaces",
            f"{settings.api_prefix}/shared",
            f"{settings.api_prefix}/auth",
        ]

        # Check if path starts with any skip path
        should_skip = any(path.startswith(skip_path) for skip_path in skip_paths)

        if should_skip:
            return await call_next(request)

        # Extract app slug from URL pattern: /api/v1/{app_slug}/...
        # Examples:
        # - /api/v1/trapmaster-pro/projects -> "trapmaster-pro"
        # - /api/v1/clipcrafter/clips -> "clipcrafter"
        app_slug = None
        pattern = rf"^{re.escape(settings.api_prefix)}/([^/]+)"
        match = re.match(pattern, path)

        if match:
            potential_slug = match.group(1)
            # Validate it's not a known non-app route
            non_app_routes = [
                "upload",
                "transcribe",
                "extract",
                "export",
                "search",
                "job",
                "privacy",
                "cost",
                "routing",
                "budget",
                "audit",
                "billing",
                "plugins",
                "explainability",
                "compliance",
                "autonomous",
                "insights",
                "suggestions",
            ]
            if potential_slug not in non_app_routes:
                app_slug = potential_slug

        # If no app slug found, continue (might be a shared route)
        if not app_slug:
            return await call_next(request)

        # Get workspace_id from request state (set by ZeroTrustMiddleware)
        workspace_id = getattr(request.state, "workspace_id", None)
        if not workspace_id:
            # This shouldn't happen if ZeroTrustMiddleware runs first
            logger.warning(f"Workspace ID not found in request state for path: {path}")
            return await call_next(request)

        # Get database session
        db: Session = SessionLocal()
        try:
            # Get app by slug
            app = db.query(App).filter(App.slug == app_slug, App.is_active == True).first()

            if not app:
                db.close()
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": f"App '{app_slug}' not found or inactive"},
                )

            # Get workspace
            workspace = (
                db.query(Workspace)
                .filter(Workspace.id == workspace_id, Workspace.is_active == True)
                .first()
            )

            if not workspace:
                db.close()
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": f"Workspace '{workspace_id}' not found or inactive"},
                )

            # Check if workspace has access to app
            app_workspace = (
                db.query(AppWorkspace)
                .filter(
                    AppWorkspace.app_id == app.id,
                    AppWorkspace.workspace_id == workspace.id,
                    AppWorkspace.is_active == True,
                )
                .first()
            )

            if not app_workspace:
                db.close()
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": f"Workspace does not have access to app '{app_slug}'"},
                )

            # Set app and workspace in request state
            request.state.app = app
            request.state.workspace = workspace
            request.state.app_workspace = app_workspace

            logger.debug(
                f"App context set: app={app.slug}, workspace={workspace.slug}, path={path}"
            )

        finally:
            db.close()

        return await call_next(request)
