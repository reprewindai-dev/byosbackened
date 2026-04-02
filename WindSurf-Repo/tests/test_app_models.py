"""Test App and AppWorkspace models."""

import pytest
from sqlalchemy.orm import Session
from db.session import SessionLocal, engine, Base
from db.models import App, AppWorkspace, Workspace
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


class TestAppModel:
    """Test App model."""

    def test_create_app(self, db: Session):
        """Test creating an app."""
        app = App(
            id=str(uuid.uuid4()),
            name="Test App",
            slug="test-app",
            description="A test app",
            is_active=True,
        )
        db.add(app)
        db.commit()
        db.refresh(app)

        assert app.id is not None
        assert app.name == "Test App"
        assert app.slug == "test-app"
        assert app.description == "A test app"
        assert app.is_active is True

    def test_app_slug_unique(self, db: Session):
        """Test that app slugs must be unique."""
        app1 = App(
            id=str(uuid.uuid4()),
            name="App 1",
            slug="duplicate-slug",
            is_active=True,
        )
        db.add(app1)
        db.commit()

        app2 = App(
            id=str(uuid.uuid4()),
            name="App 2",
            slug="duplicate-slug",  # Same slug
            is_active=True,
        )
        db.add(app2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            db.commit()

    def test_app_relationships(self, db: Session, workspace: Workspace):
        """Test app relationships."""
        app = App(
            id=str(uuid.uuid4()),
            name="Test App",
            slug="test-app",
            is_active=True,
        )
        db.add(app)
        db.commit()

        app_workspace = AppWorkspace(
            id=str(uuid.uuid4()),
            app_id=app.id,
            workspace_id=workspace.id,
            is_active=True,
        )
        db.add(app_workspace)
        db.commit()
        db.refresh(app)

        # Test relationship
        assert len(app.app_workspaces) == 1
        assert app.app_workspaces[0].workspace_id == workspace.id


class TestAppWorkspaceModel:
    """Test AppWorkspace model."""

    def test_create_app_workspace(self, db: Session, workspace: Workspace):
        """Test creating an app-workspace link."""
        app = App(
            id=str(uuid.uuid4()),
            name="Test App",
            slug="test-app",
            is_active=True,
        )
        db.add(app)
        db.commit()

        app_workspace = AppWorkspace(
            id=str(uuid.uuid4()),
            app_id=app.id,
            workspace_id=workspace.id,
            is_active=True,
            config={"key": "value"},
        )
        db.add(app_workspace)
        db.commit()
        db.refresh(app_workspace)

        assert app_workspace.id is not None
        assert app_workspace.app_id == app.id
        assert app_workspace.workspace_id == workspace.id
        assert app_workspace.is_active is True
        assert app_workspace.config == {"key": "value"}

    def test_app_workspace_unique_constraint(self, db: Session, workspace: Workspace):
        """Test that app-workspace combination must be unique."""
        app = App(
            id=str(uuid.uuid4()),
            name="Test App",
            slug="test-app",
            is_active=True,
        )
        db.add(app)
        db.commit()

        app_workspace1 = AppWorkspace(
            id=str(uuid.uuid4()),
            app_id=app.id,
            workspace_id=workspace.id,
            is_active=True,
        )
        db.add(app_workspace1)
        db.commit()

        # Try to create duplicate
        app_workspace2 = AppWorkspace(
            id=str(uuid.uuid4()),
            app_id=app.id,
            workspace_id=workspace.id,  # Same combination
            is_active=True,
        )
        db.add(app_workspace2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            db.commit()

    def test_app_workspace_cascade_delete(self, db: Session, workspace: Workspace):
        """Test that deleting app cascades to app_workspaces."""
        app = App(
            id=str(uuid.uuid4()),
            name="Test App",
            slug="test-app",
            is_active=True,
        )
        db.add(app)
        db.commit()

        app_workspace = AppWorkspace(
            id=str(uuid.uuid4()),
            app_id=app.id,
            workspace_id=workspace.id,
            is_active=True,
        )
        db.add(app_workspace)
        db.commit()

        # Delete app
        db.delete(app)
        db.commit()

        # AppWorkspace should be deleted
        deleted = db.query(AppWorkspace).filter(AppWorkspace.id == app_workspace.id).first()
        assert deleted is None

    def test_workspace_app_workspaces_relationship(self, db: Session, workspace: Workspace):
        """Test workspace relationship to app_workspaces."""
        app1 = App(
            id=str(uuid.uuid4()),
            name="App 1",
            slug="app-1",
            is_active=True,
        )
        app2 = App(
            id=str(uuid.uuid4()),
            name="App 2",
            slug="app-2",
            is_active=True,
        )
        db.add_all([app1, app2])
        db.commit()

        aw1 = AppWorkspace(
            id=str(uuid.uuid4()),
            app_id=app1.id,
            workspace_id=workspace.id,
            is_active=True,
        )
        aw2 = AppWorkspace(
            id=str(uuid.uuid4()),
            app_id=app2.id,
            workspace_id=workspace.id,
            is_active=True,
        )
        db.add_all([aw1, aw2])
        db.commit()
        db.refresh(workspace)

        # Test relationship
        assert len(workspace.app_workspaces) == 2
        assert {aw.app_id for aw in workspace.app_workspaces} == {app1.id, app2.id}
