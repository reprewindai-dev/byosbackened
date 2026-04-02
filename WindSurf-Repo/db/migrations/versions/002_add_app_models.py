"""Add app models for unified backend

Revision ID: 002_add_app_models
Revises: 001_autonomous_ml_edge
Create Date: 2025-02-03 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002_add_app_models"
down_revision = "001_autonomous_ml_edge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create apps table
    op.create_table(
        "apps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("icon_url", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("config", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_apps_slug", "apps", ["slug"], unique=True)

    # Create app_workspaces table
    op.create_table(
        "app_workspaces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("config", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_id", "workspace_id", name="uq_app_workspace"),
    )
    op.create_index("ix_app_workspaces_app_id", "app_workspaces", ["app_id"])
    op.create_index("ix_app_workspaces_workspace_id", "app_workspaces", ["workspace_id"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_app_workspaces_workspace_id", table_name="app_workspaces")
    op.drop_index("ix_app_workspaces_app_id", table_name="app_workspaces")
    op.drop_index("ix_apps_slug", table_name="apps")

    # Drop tables
    op.drop_table("app_workspaces")
    op.drop_table("apps")
