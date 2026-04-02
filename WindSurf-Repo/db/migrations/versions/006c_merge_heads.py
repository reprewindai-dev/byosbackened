"""Merge heads 006 and 006b.

Revision ID: 006c
Revises: 006, 006b
Create Date: 2026-02-13

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "006c"
down_revision = ("006", "006b")
branch_labels = None
depends_on = None


def upgrade():
    # Merge revision - no schema changes.
    pass


def downgrade():
    # Merge revision - no schema changes.
    pass
