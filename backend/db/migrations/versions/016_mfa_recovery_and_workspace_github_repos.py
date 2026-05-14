"""Add MFA recovery code storage and workspace-scoped GitHub repo selections."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return any(column["name"] == column_name for column in inspector.get_columns(table_name))
    except Exception:
        return False


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    try:
        return any(index["name"] == index_name for index in inspector.get_indexes(table_name))
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "users") and not _has_column(inspector, "users", "mfa_recovery_codes_json"):
        op.add_column("users", sa.Column("mfa_recovery_codes_json", sa.Text(), nullable=True))

    if not _has_table(inspector, "workspace_github_repo_selections"):
        op.create_table(
            "workspace_github_repo_selections",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("github_account_id", sa.String(), nullable=True),
            sa.Column("connected_account_id", sa.String(), nullable=True),
            sa.Column("repo_full_name", sa.String(), nullable=False),
            sa.Column("repo_id", sa.BigInteger(), nullable=True),
            sa.Column("default_branch", sa.String(), nullable=True),
            sa.Column("permissions_json", sa.Text(), nullable=True),
            sa.Column("visibility", sa.String(), nullable=True),
            sa.Column("repo_context_scope", sa.String(), nullable=False, server_default="metadata_only"),
            sa.Column("allowed_repo_actions_json", sa.Text(), nullable=True),
            sa.Column("restricted_repo_actions_json", sa.Text(), nullable=True),
            sa.Column("selected_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("selected_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    indexes = [
        ("ix_workspace_github_repo_selections_workspace_id", ["workspace_id"]),
        ("ix_workspace_github_repo_selections_user_id", ["user_id"]),
        ("ix_workspace_github_repo_selections_github_account_id", ["github_account_id"]),
        ("ix_workspace_github_repo_selections_connected_account_id", ["connected_account_id"]),
        ("ix_workspace_github_repo_selections_repo_full_name", ["repo_full_name"]),
        ("ix_workspace_github_repo_selections_repo_id", ["repo_id"]),
        ("ix_workspace_github_repo_selections_selected_at", ["selected_at"]),
    ]
    for index_name, columns in indexes:
        if not _has_index(inspector, "workspace_github_repo_selections", index_name):
            op.create_index(index_name, "workspace_github_repo_selections", columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "workspace_github_repo_selections"):
        op.drop_table("workspace_github_repo_selections")

    if _has_table(inspector, "users") and _has_column(inspector, "users", "mfa_recovery_codes_json"):
        op.drop_column("users", "mfa_recovery_codes_json")
