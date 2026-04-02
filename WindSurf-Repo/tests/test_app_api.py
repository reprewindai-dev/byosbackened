"""Test App Management API endpoints."""

import pytest
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
        slug=f"test-workspace-{uuid.uuid4().hex[:8]}",
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
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
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
    existing = db.query(App).filter(App.slug == "trapmaster-pro").first()
    if existing:
        return existing
    app = App(
        id=str(uuid.uuid4()),
        name="TrapMaster Pro",
        slug="trapmaster-pro",
        description="Music production app",
        is_active=True,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@pytest.fixture
def app_clipcrafter(db: Session):
    """Create ClipCrafter app."""
    existing = db.query(App).filter(App.slug == "clipcrafter").first()
    if existing:
        return existing
    app = App(
        id=str(uuid.uuid4()),
        name="ClipCrafter",
        slug="clipcrafter",
        description="Video editing app",
        is_active=True,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


class TestAppAPI:
    """Test App Management API."""

    def test_list_apps(self, db: Session, app_trapmaster: App, app_clipcrafter: App, token: str):
        """Test listing all apps."""
        client = TestClient(app)

        response = client.get(
            "/api/v1/apps",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        apps = response.json()
        assert isinstance(apps, list)
        assert len(apps) >= 2

        # Check that both apps are in the list
        slugs = [app["slug"] for app in apps]
        assert "trapmaster-pro" in slugs
        assert "clipcrafter" in slugs

        # Check structure
        for app_data in apps:
            assert "id" in app_data
            assert "name" in app_data
            assert "slug" in app_data
            assert "is_active" in app_data
            assert "workspace_has_access" in app_data

    def test_get_app_details(self, db: Session, app_trapmaster: App, token: str):
        """Test getting app details."""
        client = TestClient(app)

        response = client.get(
            f"/api/v1/apps/{app_trapmaster.slug}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        app_data = response.json()
        assert app_data["id"] == app_trapmaster.id
        assert app_data["name"] == app_trapmaster.name
        assert app_data["slug"] == app_trapmaster.slug
        assert app_data["workspace_has_access"] is False  # Not enabled yet

    def test_get_nonexistent_app(self, token: str):
        """Test getting nonexistent app."""
        client = TestClient(app)

        response = client.get(
            "/api/v1/apps/nonexistent-app",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    def test_enable_app_for_workspace(
        self, db: Session, workspace: Workspace, app_trapmaster: App, token: str
    ):
        """Test enabling app for workspace."""
        client = TestClient(app)

        response = client.post(
            f"/api/v1/workspaces/{workspace.id}/apps/{app_trapmaster.slug}/enable",
            headers={"Authorization": f"Bearer {token}"},
            json={"config": {"key": "value"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "app_workspace_id" in data
        assert data["is_active"] is True

        # Verify in database
        aw = (
            db.query(AppWorkspace)
            .filter(
                AppWorkspace.app_id == app_trapmaster.id, AppWorkspace.workspace_id == workspace.id
            )
            .first()
        )
        assert aw is not None
        assert aw.is_active is True

    def test_enable_app_twice(
        self, db: Session, workspace: Workspace, app_trapmaster: App, token: str
    ):
        """Test enabling app twice (should update existing)."""
        client = TestClient(app)

        # Enable first time
        response1 = client.post(
            f"/api/v1/workspaces/{workspace.id}/apps/{app_trapmaster.slug}/enable",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert response1.status_code == 200

        # Enable second time
        response2 = client.post(
            f"/api/v1/workspaces/{workspace.id}/apps/{app_trapmaster.slug}/enable",
            headers={"Authorization": f"Bearer {token}"},
            json={"config": {"updated": True}},
        )
        if response2.status_code != 200:
            print(f"Error response: {response2.status_code} - {response2.text}")
        assert response2.status_code == 200
        data = response2.json()
        assert "already enabled" in data["message"].lower()

    def test_disable_app_for_workspace(
        self, db: Session, workspace: Workspace, app_trapmaster: App, token: str
    ):
        """Test disabling app for workspace."""
        client = TestClient(app)

        # First enable
        client.post(
            f"/api/v1/workspaces/{workspace.id}/apps/{app_trapmaster.slug}/enable",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )

        # Then disable
        response = client.post(
            f"/api/v1/workspaces/{workspace.id}/apps/{app_trapmaster.slug}/disable",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "disabled" in data["message"].lower()
        assert data["is_active"] is False

        # Verify in database
        aw = (
            db.query(AppWorkspace)
            .filter(
                AppWorkspace.app_id == app_trapmaster.id, AppWorkspace.workspace_id == workspace.id
            )
            .first()
        )
        assert aw.is_active is False

    def test_disable_nonexistent_app_workspace(
        self, db: Session, workspace: Workspace, app_trapmaster: App, token: str
    ):
        """Test disabling app that's not enabled."""
        client = TestClient(app)

        response = client.post(
            f"/api/v1/workspaces/{workspace.id}/apps/{app_trapmaster.slug}/disable",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    def test_list_workspace_apps(
        self,
        db: Session,
        workspace: Workspace,
        app_trapmaster: App,
        app_clipcrafter: App,
        token: str,
    ):
        """Test listing apps for a workspace."""
        client = TestClient(app)

        # Enable both apps
        client.post(
            f"/api/v1/workspaces/{workspace.id}/apps/{app_trapmaster.slug}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            f"/api/v1/workspaces/{workspace.id}/apps/{app_clipcrafter.slug}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )

        # List workspace apps
        response = client.get(
            f"/api/v1/workspaces/{workspace.id}/apps",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "workspace_id" in data
        assert "apps" in data
        assert len(data["apps"]) == 2

        slugs = [app["slug"] for app in data["apps"]]
        assert "trapmaster-pro" in slugs
        assert "clipcrafter" in slugs

    def test_cannot_access_other_workspace(
        self, db: Session, workspace: Workspace, app_trapmaster: App, token: str
    ):
        """Test that users cannot access other workspaces."""
        # Create another workspace
        other_workspace = Workspace(
            id=str(uuid.uuid4()),
            name="Other Workspace",
            slug="other-workspace",
            is_active=True,
        )
        db.add(other_workspace)
        db.commit()

        client = TestClient(app)

        # Try to enable app for other workspace
        response = client.post(
            f"/api/v1/workspaces/{other_workspace.id}/apps/{app_trapmaster.slug}/enable",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
