"""Add ClipCrafter models

Revision ID: 004_add_clipcrafter_models
Revises: 003_add_trapmaster_pro_models
Create Date: 2025-02-03 14:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004_add_clipcrafter_models"
down_revision = "003_add_trapmaster_pro_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create clipcrafter_projects table
    op.create_table(
        "clipcrafter_projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("aspect_ratio", sa.String(), nullable=True),
        sa.Column("resolution", sa.String(), nullable=True),
        sa.Column("frame_rate", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clipcrafter_projects_app_id", "clipcrafter_projects", ["app_id"])
    op.create_index(
        "ix_clipcrafter_projects_workspace_id", "clipcrafter_projects", ["workspace_id"]
    )
    op.create_index(
        "idx_clipcrafter_projects_app_workspace", "clipcrafter_projects", ["app_id", "workspace_id"]
    )

    # Create clipcrafter_clips table
    op.create_table(
        "clipcrafter_clips",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("clip_type", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Numeric(10, 2), nullable=True),
        sa.Column("start_time", sa.Numeric(10, 2), nullable=True),
        sa.Column("end_time", sa.Numeric(10, 2), nullable=True),
        sa.Column("position_x", sa.Integer(), nullable=True),
        sa.Column("position_y", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("opacity", sa.Numeric(5, 2), nullable=False, server_default="100.0"),
        sa.Column("volume", sa.Numeric(5, 2), nullable=False, server_default="100.0"),
        sa.Column("effects", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("transitions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["clipcrafter_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clipcrafter_clips_app_id", "clipcrafter_clips", ["app_id"])
    op.create_index("ix_clipcrafter_clips_workspace_id", "clipcrafter_clips", ["workspace_id"])
    op.create_index("ix_clipcrafter_clips_project_id", "clipcrafter_clips", ["project_id"])
    op.create_index(
        "idx_clipcrafter_clips_app_workspace", "clipcrafter_clips", ["app_id", "workspace_id"]
    )

    # Create clipcrafter_templates table
    op.create_table(
        "clipcrafter_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("thumbnail_path", sa.String(), nullable=True),
        sa.Column("template_data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("aspect_ratio", sa.String(), nullable=True),
        sa.Column("duration", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["clipcrafter_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clipcrafter_templates_app_id", "clipcrafter_templates", ["app_id"])
    op.create_index(
        "ix_clipcrafter_templates_workspace_id", "clipcrafter_templates", ["workspace_id"]
    )
    op.create_index("ix_clipcrafter_templates_project_id", "clipcrafter_templates", ["project_id"])
    op.create_index(
        "idx_clipcrafter_templates_app_workspace",
        "clipcrafter_templates",
        ["app_id", "workspace_id"],
    )

    # Create clipcrafter_renders table
    op.create_table(
        "clipcrafter_renders",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(), nullable=False),
        sa.Column("resolution", sa.String(), nullable=False),
        sa.Column("frame_rate", sa.Integer(), nullable=True),
        sa.Column("quality", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("render_settings", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["app_id"], ["apps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["clipcrafter_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clipcrafter_renders_app_id", "clipcrafter_renders", ["app_id"])
    op.create_index("ix_clipcrafter_renders_workspace_id", "clipcrafter_renders", ["workspace_id"])
    op.create_index("ix_clipcrafter_renders_project_id", "clipcrafter_renders", ["project_id"])
    op.create_index(
        "idx_clipcrafter_renders_app_workspace", "clipcrafter_renders", ["app_id", "workspace_id"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_clipcrafter_renders_app_workspace", table_name="clipcrafter_renders")
    op.drop_index("ix_clipcrafter_renders_project_id", table_name="clipcrafter_renders")
    op.drop_index("ix_clipcrafter_renders_workspace_id", table_name="clipcrafter_renders")
    op.drop_index("ix_clipcrafter_renders_app_id", table_name="clipcrafter_renders")
    op.drop_index("idx_clipcrafter_templates_app_workspace", table_name="clipcrafter_templates")
    op.drop_index("ix_clipcrafter_templates_project_id", table_name="clipcrafter_templates")
    op.drop_index("ix_clipcrafter_templates_workspace_id", table_name="clipcrafter_templates")
    op.drop_index("ix_clipcrafter_templates_app_id", table_name="clipcrafter_templates")
    op.drop_index("idx_clipcrafter_clips_app_workspace", table_name="clipcrafter_clips")
    op.drop_index("ix_clipcrafter_clips_project_id", table_name="clipcrafter_clips")
    op.drop_index("ix_clipcrafter_clips_workspace_id", table_name="clipcrafter_clips")
    op.drop_index("ix_clipcrafter_clips_app_id", table_name="clipcrafter_clips")
    op.drop_index("idx_clipcrafter_projects_app_workspace", table_name="clipcrafter_projects")
    op.drop_index("ix_clipcrafter_projects_workspace_id", table_name="clipcrafter_projects")
    op.drop_index("ix_clipcrafter_projects_app_id", table_name="clipcrafter_projects")

    # Drop tables
    op.drop_table("clipcrafter_renders")
    op.drop_table("clipcrafter_templates")
    op.drop_table("clipcrafter_clips")
    op.drop_table("clipcrafter_projects")
