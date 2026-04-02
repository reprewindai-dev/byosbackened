"""Test app isolation - apps cannot access each other's data."""

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
def workspace_a(db: Session):
    """Create workspace A."""
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name="Workspace A",
        slug="workspace-a",
        is_active=True,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@pytest.fixture
def workspace_b(db: Session):
    """Create workspace B."""
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name="Workspace B",
        slug="workspace-b",
        is_active=True,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@pytest.fixture
def user_a(db: Session, workspace_a: Workspace):
    """Create user A."""
    user = User(
        id=str(uuid.uuid4()),
        workspace_id=workspace_a.id,
        email="user_a@test.com",
        hashed_password="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_b(db: Session, workspace_b: Workspace):
    """Create user B."""
    user = User(
        id=str(uuid.uuid4()),
        workspace_id=workspace_b.id,
        email="user_b@test.com",
        hashed_password="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def token_a(workspace_a: Workspace, user_a: User):
    """Create token for workspace A."""
    return create_access_token(
        data={"sub": user_a.email, "workspace_id": workspace_a.id, "user_id": user_a.id}
    )


@pytest.fixture
def token_b(workspace_b: Workspace, user_b: User):
    """Create token for workspace B."""
    return create_access_token(
        data={"sub": user_b.email, "workspace_id": workspace_b.id, "user_id": user_b.id}
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
def app_workspace_a_trapmaster(db: Session, workspace_a: Workspace, app_trapmaster: App):
    """Enable TrapMaster Pro for workspace A."""
    aw = AppWorkspace(
        id=str(uuid.uuid4()),
        app_id=app_trapmaster.id,
        workspace_id=workspace_a.id,
        is_active=True,
    )
    db.add(aw)
    db.commit()
    db.refresh(aw)
    return aw


@pytest.fixture
def app_workspace_b_clipcrafter(db: Session, workspace_b: Workspace, app_clipcrafter: App):
    """Enable ClipCrafter for workspace B."""
    aw = AppWorkspace(
        id=str(uuid.uuid4()),
        app_id=app_clipcrafter.id,
        workspace_id=workspace_b.id,
        is_active=True,
    )
    db.add(aw)
    db.commit()
    db.refresh(aw)
    return aw


class TestAppIsolation:
    """Test that apps and workspaces are properly isolated."""

    def test_workspace_a_cannot_enable_apps_for_workspace_b(
        self,
        db: Session,
        workspace_a: Workspace,
        workspace_b: Workspace,
        app_trapmaster: App,
        token_a: str,
    ):
        """Workspace A cannot enable apps for workspace B."""
        client = TestClient(app)

        response = client.post(
            f"/api/v1/workspaces/{workspace_b.id}/apps/{app_trapmaster.slug}/enable",
            headers={"Authorization": f"Bearer {token_a}"},
        )

        assert response.status_code == 403

    def test_workspace_a_cannot_list_workspace_b_apps(
        self,
        db: Session,
        workspace_a: Workspace,
        workspace_b: Workspace,
        app_clipcrafter: App,
        app_workspace_b_clipcrafter: AppWorkspace,
        token_a: str,
    ):
        """Workspace A cannot list workspace B's apps."""
        client = TestClient(app)

        response = client.get(
            f"/api/v1/workspaces/{workspace_b.id}/apps",
            headers={"Authorization": f"Bearer {token_a}"},
        )

        assert response.status_code == 403

    def test_workspace_a_only_sees_own_apps(
        self,
        db: Session,
        workspace_a: Workspace,
        workspace_b: Workspace,
        app_trapmaster: App,
        app_clipcrafter: App,
        app_workspace_a_trapmaster: AppWorkspace,
        app_workspace_b_clipcrafter: AppWorkspace,
        token_a: str,
    ):
        """Workspace A only sees apps enabled for workspace A."""
        client = TestClient(app)

        response = client.get(
            f"/api/v1/workspaces/{workspace_a.id}/apps",
            headers={"Authorization": f"Bearer {token_a}"},
        )

        assert response.status_code == 200
        data = response.json()
        apps = data["apps"]

        # Should only see TrapMaster Pro
        slugs = [app["slug"] for app in apps]
        assert "trapmaster-pro" in slugs
        assert "clipcrafter" not in slugs

    def test_database_query_isolation(
        self,
        db: Session,
        workspace_a: Workspace,
        workspace_b: Workspace,
        app_trapmaster: App,
        app_clipcrafter: App,
        app_workspace_a_trapmaster: AppWorkspace,
        app_workspace_b_clipcrafter: AppWorkspace,
    ):
        """Test that database queries respect workspace isolation."""
        # Query app_workspaces for workspace A
        aws_a = db.query(AppWorkspace).filter(AppWorkspace.workspace_id == workspace_a.id).all()

        assert len(aws_a) == 1
        assert aws_a[0].app_id == app_trapmaster.id

        # Query app_workspaces for workspace B
        aws_b = db.query(AppWorkspace).filter(AppWorkspace.workspace_id == workspace_b.id).all()

        assert len(aws_b) == 1
        assert aws_b[0].app_id == app_clipcrafter.id

        # Verify no cross-contamination
        assert app_workspace_a_trapmaster.id not in [aw.id for aw in aws_b]
        assert app_workspace_b_clipcrafter.id not in [aw.id for aw in aws_a]

    def test_app_access_status_isolation(
        self,
        db: Session,
        workspace_a: Workspace,
        workspace_b: Workspace,
        app_trapmaster: App,
        app_clipcrafter: App,
        app_workspace_a_trapmaster: AppWorkspace,
        app_workspace_b_clipcrafter: AppWorkspace,
        token_a: str,
        token_b: str,
    ):
        """Test that app access status is isolated per workspace."""
        client = TestClient(app)

        # Workspace A checks TrapMaster Pro
        response_a = client.get(
            f"/api/v1/apps/{app_trapmaster.slug}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response_a.status_code == 200
        data_a = response_a.json()
        assert data_a["workspace_has_access"] is True

        # Workspace B checks TrapMaster Pro
        response_b = client.get(
            f"/api/v1/apps/{app_trapmaster.slug}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response_b.status_code == 200
        data_b = response_b.json()
        assert data_b["workspace_has_access"] is False  # Not enabled for workspace B
