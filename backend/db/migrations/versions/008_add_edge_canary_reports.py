"""Add edge canary report storage."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "edge_canary_reports" not in inspector.get_table_names():
        op.create_table(
            "edge_canary_reports",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("generated_at", sa.DateTime(), nullable=False),
            sa.Column("report_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_edge_canary_reports_status", "edge_canary_reports", ["status"], unique=False)
        op.create_index("ix_edge_canary_reports_generated_at", "edge_canary_reports", ["generated_at"], unique=False)
        op.create_index("ix_edge_canary_reports_created_at", "edge_canary_reports", ["created_at"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "edge_canary_reports" in inspector.get_table_names():
        for idx in [
            "ix_edge_canary_reports_created_at",
            "ix_edge_canary_reports_generated_at",
            "ix_edge_canary_reports_status",
        ]:
            try:
                op.drop_index(idx, table_name="edge_canary_reports")
            except Exception:
                pass
        op.drop_table("edge_canary_reports")
