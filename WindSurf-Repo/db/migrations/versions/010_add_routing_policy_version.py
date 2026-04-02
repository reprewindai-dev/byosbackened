"""Add version column to routing_policies for stable policy versioning.

Revision ID: 010
Revises: 009
Create Date: 2026-02-13

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "routing_policies",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    # remove server default so ORM/defaults own the value on new inserts
    op.alter_column("routing_policies", "version", server_default=None)


def downgrade():
    op.drop_column("routing_policies", "version")
