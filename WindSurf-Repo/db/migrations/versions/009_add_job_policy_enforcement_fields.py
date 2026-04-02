"""Add policy enforcement audit fields to jobs.

Revision ID: 009
Revises: 008
Create Date: 2026-02-13

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("requested_provider", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("resolved_provider", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("policy_id", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("policy_version", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("policy_enforcement", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("policy_reason", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("was_fallback", sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column("jobs", "was_fallback")
    op.drop_column("jobs", "policy_reason")
    op.drop_column("jobs", "policy_enforcement")
    op.drop_column("jobs", "policy_version")
    op.drop_column("jobs", "policy_id")
    op.drop_column("jobs", "resolved_provider")
    op.drop_column("jobs", "requested_provider")
