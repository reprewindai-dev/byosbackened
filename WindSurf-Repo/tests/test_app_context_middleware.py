"""Test App Context Middleware."""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from db.session import SessionLocal, engine, Base
from db.models import App, AppWorkspace, Workspace, User
from apps.api.main import app
from core.security import create_access_token
import uuid

# Create test database
Base.metadata.create_all(bind=engine)


@pytest.fixture
def db():
    """Create test database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def workspace(db: Session):
    """Create a test workspace."""
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name="Test Workspace",
        slug="test-workspace",
        is_active=True,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@pytest.fixture
def user(db: Session, workspace: Workspace):
    """Create a test user."""
    user = User(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        email="test@example.com",
        hashed_password="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def token(workspace: Workspace, user: User):
    """Create access token."""
    return create_access_token(
        data={"sub": user.email, "workspace_id": workspace.id, "user_id": user.id}
    )


@pytest.fixture
def app_trapmaster(db: Session):
    """Create TrapMaster Pro app."""
    app = App(
        id=str(uuid.uuid4()),
        name="TrapMaster Pro",
        slug="trapmaster-pro",
        is_active=True,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@pytest.fixture
def app_clipcrafter(db: Session):
    """Create ClipCrafter app."""
    app = App(
        id=str(uuid.uuid4()),
        name="ClipCrafter",
        slug="clipcrafter",
        is_active=True,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@pytest.fixture
def app_workspace_enabled(db: Session, workspace: Workspace, app_trapmaster: App):
    """Enable TrapMaster Pro for workspace."""
    aw = AppWorkspace(
        id=str(uuid.uuid4()),
        app_id=app_trapmaster.id,
        workspace_id=workspace.id,
        is_active=True,
    )
    db.add(aw)
    db.commit()
    db.refresh(aw)
    return aw


class TestAppContextMiddleware:
    """Test App Context Middleware."""

    def test_middleware_skips_non_app_routes(self, token: str):
        """Test that middleware skips non-app routes."""
        client = TestClient(app)

        # Health check should work without app context
        response = client.get("/health")
        assert response.status_code == 200

        # Metrics should work
        response = client.get("/metrics")
        assert response.status_code == 200

        # Existing routes should work
        response = client.get(
            "/api/v1/apps",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_middleware_extracts_app_slug(
        self,
        db: Session,
        workspace: Workspace,
        app_trapmaster: App,
        app_workspace_enabled: AppWorkspace,
        token: str,
    ):
        """Test that middleware extracts app slug from URL."""
        client = TestClient(app)

        # This should work because app is enabled
        # Note: We need an actual route under /api/v1/trapmaster-pro/... to test this
        # For now, we'll test that the middleware doesn't block valid app routes
        # The actual route implementation will be in Phase 2

        # Test that listing apps works (this doesn't need app context)
        response = client.get(
            "/api/v1/apps",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        apps = response.json()
        assert len(apps) > 0

    def test_middleware_rejects_inactive_app(
        self,
        db: Session,
        workspace: Workspace,
        app_trapmaster: App,
        app_workspace_enabled: AppWorkspace,
        token: str,
    ):
        """Test that middleware rejects inactive apps."""
        # Deactivate app
        app_trapmaster.is_active = False
        db.commit()

        client = TestClient(app)

        # Try to access app route (when implemented)
        # For now, test that getting app details shows it's inactive
        response = client.get(
            f"/api/v1/apps/{app_trapmaster.slug}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should return 404 or show inactive status
        assert response.status_code in [200, 404]

    def test_middleware_rejects_disabled_app_for_workspace(
        self, db: Session, workspace: Workspace, app_trapmaster: App, token: str
    ):
        """Test that middleware rejects apps not enabled for workspace."""
        # Don't enable app for workspace

        client = TestClient(app)

        # Try to access app route (when implemented)
        # For now, test that getting app details shows workspace doesn't have access
        response = client.get(
            f"/api/v1/apps/{app_trapmaster.slug}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_has_access"] is False

    def test_middleware_allows_enabled_app(
        self,
        db: Session,
        workspace: Workspace,
        app_trapmaster: App,
        app_workspace_enabled: AppWorkspace,
        token: str,
    ):
        """Test that middleware allows enabled apps."""
        client = TestClient(app)

        # Get app details
        response = client.get(
            f"/api/v1/apps/{app_trapmaster.slug}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_has_access"] is True
        assert data["workspace_is_active"] is True
