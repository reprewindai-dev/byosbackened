"""Add public status update subscriptions."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _has_index(inspector, table: str, name: str) -> bool:
    try:
        return any(i.get("name") == name for i in inspector.get_indexes(table))
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "status_subscriptions"):
        op.create_table(
            "status_subscriptions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("channel", sa.String(), nullable=False),
            sa.Column("target_hash", sa.String(), nullable=False),
            sa.Column("target_encrypted", sa.Text(), nullable=False),
            sa.Column("target_label", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("verification_status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("last_delivery_status", sa.String(), nullable=True),
            sa.Column("last_delivery_at", sa.DateTime(), nullable=True),
            sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_ip", sa.String(), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("target_hash", name="uq_status_subscriptions_target_hash"),
        )

    for index_name, column_name in [
        ("ix_status_subscriptions_channel", "channel"),
        ("ix_status_subscriptions_target_hash", "target_hash"),
        ("ix_status_subscriptions_status", "status"),
        ("ix_status_subscriptions_verification_status", "verification_status"),
        ("ix_status_subscriptions_created_at", "created_at"),
    ]:
        if not _has_index(inspector, "status_subscriptions", index_name):
            op.create_index(index_name, "status_subscriptions", [column_name])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "status_subscriptions"):
        return

    for index_name in [
        "ix_status_subscriptions_created_at",
        "ix_status_subscriptions_verification_status",
        "ix_status_subscriptions_status",
        "ix_status_subscriptions_target_hash",
        "ix_status_subscriptions_channel",
    ]:
        if _has_index(inspector, "status_subscriptions", index_name):
            op.drop_index(index_name, table_name="status_subscriptions")

    op.drop_table("status_subscriptions")
