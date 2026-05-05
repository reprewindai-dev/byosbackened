"""Add dashboard latency indexes.

Overview and workspace screens read recent request, audit, alert, and budget
rows on every load. These composite indexes keep those tenant-scoped reads fast
as production usage grows.
"""
from __future__ import annotations

from alembic import op


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_workspace_request_logs_workspace_created "
        "ON workspace_request_logs (workspace_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_audit_logs_workspace_created "
        "ON ai_audit_logs (workspace_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_budgets_workspace_period "
        "ON budgets (workspace_id, period_start, period_end)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_alerts_workspace_status_created "
        "ON alerts (workspace_id, status, created_at DESC)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_alerts_workspace_status_created")
    op.execute("DROP INDEX IF EXISTS idx_budgets_workspace_period")
    op.execute("DROP INDEX IF EXISTS idx_ai_audit_logs_workspace_created")
    op.execute("DROP INDEX IF EXISTS idx_workspace_request_logs_workspace_created")
