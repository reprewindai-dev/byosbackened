"""Add quality and latency fields to AI audit log.

Revision ID: 008
Revises: 007
Create Date: 2026-02-13

"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ai_audit_logs", sa.Column("actual_quality", sa.Numeric(5, 2), nullable=True))
    op.add_column("ai_audit_logs", sa.Column("actual_latency_ms", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("ai_audit_logs", "actual_latency_ms")
    op.drop_column("ai_audit_logs", "actual_quality")
