"""Add deployment orchestration status enum values.

Promote and rollback routes transition through PROMOTING and ROLLING_BACK.
Existing production databases may have the original enum with only
ACTIVE/INACTIVE/FAILED, so this migration expands the enum idempotently.
"""
from __future__ import annotations

from alembic import op


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE deploymentstatus ADD VALUE IF NOT EXISTS 'PROMOTING'")
    op.execute("ALTER TYPE deploymentstatus ADD VALUE IF NOT EXISTS 'ROLLING_BACK'")


def downgrade():
    # PostgreSQL cannot safely remove enum values without recreating the type.
    # Keeping this no-op preserves existing deployment rows and avoids data loss.
    pass
