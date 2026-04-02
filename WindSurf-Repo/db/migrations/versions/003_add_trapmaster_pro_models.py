"""Add TrapMaster Pro models

Revision ID: 003_add_trapmaster_pro_models
Revises: 002_add_app_models
Create Date: 2025-02-03 13:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003_add_trapmaster_pro_models"
down_revision = "002_add_app_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create trapmaster_projects table
    op.create_table(
        "trapmaster_projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bpm", sa.Integer(), nullable=True),
        sa.Column("key", sa.String(), nullable=True),
        sa.Column("time_signature", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trapmaster_projects_app_id", "trapmaster_projects", ["app_id"])
    op.create_index("ix_trapmaster_projects_workspace_id", "trapmaster_projects", ["workspace_id"])
    op.create_index(
        "idx_trapmaster_projects_app_workspace", "trapmaster_projects", ["app_id", "workspace_id"]
    )

    # Create trapmaster_tracks table
    op.create_table(
        "trapmaster_tracks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("track_type", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Numeric(10, 2), nullable=True),
        sa.Column("volume", sa.Numeric(5, 2), nullable=False, server_default="100.0"),
        sa.Column("pan", sa.Numeric(5, 2), nullable=False, server_default="0.0"),
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_solo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["trapmaster_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trapmaster_tracks_app_id", "trapmaster_tracks", ["app_id"])
    op.create_index("ix_trapmaster_tracks_workspace_id", "trapmaster_tracks", ["workspace_id"])
    op.create_index("ix_trapmaster_tracks_project_id", "trapmaster_tracks", ["project_id"])
    op.create_index(
        "idx_trapmaster_tracks_app_workspace", "trapmaster_tracks", ["app_id", "workspace_id"]
    )

    # Create trapmaster_samples table
    op.create_table(
        "trapmaster_samples",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Numeric(10, 2), nullable=True),
        sa.Column("bpm", sa.Integer(), nullable=True),
        sa.Column("key", sa.String(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["trapmaster_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trapmaster_samples_app_id", "trapmaster_samples", ["app_id"])
    op.create_index("ix_trapmaster_samples_workspace_id", "trapmaster_samples", ["workspace_id"])
    op.create_index("ix_trapmaster_samples_project_id", "trapmaster_samples", ["project_id"])
    op.create_index(
        "idx_trapmaster_samples_app_workspace", "trapmaster_samples", ["app_id", "workspace_id"]
    )

    # Create trapmaster_exports table
    op.create_table(
        "trapmaster_exports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(), nullable=False),
        sa.Column("quality", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["trapmaster_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trapmaster_exports_app_id", "trapmaster_exports", ["app_id"])
    op.create_index("ix_trapmaster_exports_workspace_id", "trapmaster_exports", ["workspace_id"])
    op.create_index("ix_trapmaster_exports_project_id", "trapmaster_exports", ["project_id"])
    op.create_index(
        "idx_trapmaster_exports_app_workspace", "trapmaster_exports", ["app_id", "workspace_id"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_trapmaster_exports_app_workspace", table_name="trapmaster_exports")
    op.drop_index("ix_trapmaster_exports_project_id", table_name="trapmaster_exports")
    op.drop_index("ix_trapmaster_exports_workspace_id", table_name="trapmaster_exports")
    op.drop_index("ix_trapmaster_exports_app_id", table_name="trapmaster_exports")
    op.drop_index("idx_trapmaster_samples_app_workspace", table_name="trapmaster_samples")
    op.drop_index("ix_trapmaster_samples_project_id", table_name="trapmaster_samples")
    op.drop_index("ix_trapmaster_samples_workspace_id", table_name="trapmaster_samples")
    op.drop_index("ix_trapmaster_samples_app_id", table_name="trapmaster_samples")
    op.drop_index("idx_trapmaster_tracks_app_workspace", table_name="trapmaster_tracks")
    op.drop_index("ix_trapmaster_tracks_project_id", table_name="trapmaster_tracks")
    op.drop_index("ix_trapmaster_tracks_workspace_id", table_name="trapmaster_tracks")
    op.drop_index("ix_trapmaster_tracks_app_id", table_name="trapmaster_tracks")
    op.drop_index("idx_trapmaster_projects_app_workspace", table_name="trapmaster_projects")
    op.drop_index("ix_trapmaster_projects_workspace_id", table_name="trapmaster_projects")
    op.drop_index("ix_trapmaster_projects_app_id", table_name="trapmaster_projects")

    # Drop tables
    op.drop_table("trapmaster_exports")
    op.drop_table("trapmaster_samples")
    op.drop_table("trapmaster_tracks")
    op.drop_table("trapmaster_projects")
