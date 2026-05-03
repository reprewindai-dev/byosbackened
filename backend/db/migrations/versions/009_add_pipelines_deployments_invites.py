"""Pipelines + extended deployments + workspace invites.

Adds:
  - pipelines, pipeline_versions, pipeline_runs
  - workspace_invites
  - new columns on deployments (name, slug, model_slug, version, traffic_percent, etc.)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _has_column(inspector, table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in inspector.get_columns(table))
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ── pipelines
    if not _has_table(inspector, "pipelines"):
        op.create_table(
            "pipelines",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("workspace_id", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="draft"),
            sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_pipelines_workspace_id", "pipelines", ["workspace_id"])
        op.create_index("ix_pipelines_slug", "pipelines", ["slug"])
        op.create_index("ix_pipelines_status", "pipelines", ["status"])

    # ── pipeline_versions
    if not _has_table(inspector, "pipeline_versions"):
        op.create_table(
            "pipeline_versions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("pipeline_id", sa.String(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("graph", sa.JSON(), nullable=False),
            sa.Column("policy_refs", sa.JSON(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_pipeline_versions_pipeline_id", "pipeline_versions", ["pipeline_id"])

    # ── pipeline_runs
    if not _has_table(inspector, "pipeline_runs"):
        op.create_table(
            "pipeline_runs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("pipeline_id", sa.String(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.String(), nullable=False),
            sa.Column("triggered_by", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("inputs", sa.JSON(), nullable=True),
            sa.Column("outputs", sa.JSON(), nullable=True),
            sa.Column("step_trace", sa.JSON(), nullable=True),
            sa.Column("total_cost_usd", sa.String(), nullable=True),
            sa.Column("total_latency_ms", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.ForeignKeyConstraint(["triggered_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_pipeline_runs_pipeline_id", "pipeline_runs", ["pipeline_id"])
        op.create_index("ix_pipeline_runs_workspace_id", "pipeline_runs", ["workspace_id"])
        op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])
        op.create_index("ix_pipeline_runs_created_at", "pipeline_runs", ["created_at"])

    # ── workspace_invites
    if not _has_table(inspector, "workspace_invites"):
        op.create_table(
            "workspace_invites",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("workspace_id", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False, server_default="user"),
            sa.Column("token", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("invited_by", sa.String(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("accepted_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.ForeignKeyConstraint(["invited_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token"),
        )
        op.create_index("ix_workspace_invites_workspace_id", "workspace_invites", ["workspace_id"])
        op.create_index("ix_workspace_invites_email", "workspace_invites", ["email"])
        op.create_index("ix_workspace_invites_status", "workspace_invites", ["status"])
        op.create_index("ix_workspace_invites_token", "workspace_invites", ["token"])

    # ── deployments column extensions (additive, idempotent)
    if _has_table(inspector, "deployments"):
        for col_name, col in [
            ("name", sa.Column("name", sa.String(), nullable=True)),
            ("slug", sa.Column("slug", sa.String(), nullable=True)),
            ("model_slug", sa.Column("model_slug", sa.String(), nullable=True)),
            ("provider", sa.Column("provider", sa.String(), nullable=True)),
            ("version", sa.Column("version", sa.String(), nullable=True)),
            ("previous_version", sa.Column("previous_version", sa.String(), nullable=True)),
            ("strategy", sa.Column("strategy", sa.String(), nullable=True, server_default="direct")),
            ("traffic_percent", sa.Column("traffic_percent", sa.Integer(), nullable=True, server_default="100")),
            ("is_primary", sa.Column("is_primary", sa.Boolean(), nullable=True, server_default=sa.text("1"))),
            ("health_metrics", sa.Column("health_metrics", sa.JSON(), nullable=True)),
            ("created_by", sa.Column("created_by", sa.String(), nullable=True)),
            ("promoted_at", sa.Column("promoted_at", sa.DateTime(), nullable=True)),
            ("rolled_back_at", sa.Column("rolled_back_at", sa.DateTime(), nullable=True)),
            ("updated_at", sa.Column("updated_at", sa.DateTime(), nullable=True)),
        ]:
            if not _has_column(inspector, "deployments", col_name):
                op.add_column("deployments", col)
        try:
            op.create_index("ix_deployments_slug", "deployments", ["slug"])
        except Exception:
            pass
        try:
            op.create_index("ix_deployments_model_slug", "deployments", ["model_slug"])
        except Exception:
            pass


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for tbl in ("pipeline_runs", "pipeline_versions", "pipelines", "workspace_invites"):
        if _has_table(inspector, tbl):
            try:
                op.drop_table(tbl)
            except Exception:
                pass

    if _has_table(inspector, "deployments"):
        for col_name in (
            "name", "slug", "model_slug", "provider", "version", "previous_version",
            "strategy", "traffic_percent", "is_primary", "health_metrics", "created_by",
            "promoted_at", "rolled_back_at", "updated_at",
        ):
            if _has_column(inspector, "deployments", col_name):
                try:
                    op.drop_column("deployments", col_name)
                except Exception:
                    pass
