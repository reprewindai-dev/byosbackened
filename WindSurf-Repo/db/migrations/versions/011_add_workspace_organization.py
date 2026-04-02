"""Add organization_id to workspaces table.

Revision ID: 011
Revises: 010
Create Date: 2026-02-18

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    # Add organization_id column to workspaces table
    op.add_column(
        "workspaces",
        sa.Column(
            "organization_id",
            sa.String(),
            nullable=True,
            index=True,
        ),
    )
    
    # Add foreign key constraint if organizations table exists
    # Note: This will be added in a subsequent migration after organizations table is created


def downgrade():
    # Remove organization_id column from workspaces table
    op.drop_column("workspaces", "organization_id")
