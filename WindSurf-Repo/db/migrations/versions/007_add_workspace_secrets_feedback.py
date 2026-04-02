"""Add workspace BYOK secrets and AI feedback tables.

Revision ID: 007
Revises: 006
Create Date: 2026-02-13

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workspace_secrets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("secret_name", sa.String(), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id", "provider", "secret_name", name="uq_workspace_provider_secret"
        ),
    )
    op.create_index("ix_workspace_secrets_workspace_id", "workspace_secrets", ["workspace_id"])
    op.create_index("ix_workspace_secrets_provider", "workspace_secrets", ["provider"])

    op.create_table(
        "ai_feedback",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("audit_log_id", sa.String(), nullable=True),
        sa.Column("operation_id", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="user"),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("is_correct", sa.Integer(), nullable=True),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("feedback_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["audit_log_id"], ["ai_audit_logs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_feedback_workspace_id", "ai_feedback", ["workspace_id"])
    op.create_index("ix_ai_feedback_audit_log_id", "ai_feedback", ["audit_log_id"])
    op.create_index("ix_ai_feedback_operation_id", "ai_feedback", ["operation_id"])


def downgrade():
    op.drop_index("ix_ai_feedback_operation_id", table_name="ai_feedback")
    op.drop_index("ix_ai_feedback_audit_log_id", table_name="ai_feedback")
    op.drop_index("ix_ai_feedback_workspace_id", table_name="ai_feedback")
    op.drop_table("ai_feedback")

    op.drop_index("ix_workspace_secrets_provider", table_name="workspace_secrets")
    op.drop_index("ix_workspace_secrets_workspace_id", table_name="workspace_secrets")
    op.drop_table("workspace_secrets")
