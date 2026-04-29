"""Add workspace trial license tracking fields.

Revision ID: 007
Revises: 006
Create Date: 2026-04-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "license_keys" not in inspector.get_table_names():
        op.create_table(
            "license_keys",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("key_hash", sa.String(), nullable=False),
            sa.Column("encrypted_key", sa.Text(), nullable=False),
            sa.Column("key_prefix", sa.String(), nullable=False),
            sa.Column("workspace_id", sa.String(), nullable=False),
            sa.Column("tier", sa.String(), nullable=False),
            sa.Column("machine_fingerprint", sa.String(), nullable=True),
            sa.Column("stripe_customer_id", sa.String(), nullable=True),
            sa.Column("stripe_subscription_id", sa.String(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("grace_until", sa.DateTime(), nullable=True),
            sa.Column("revoked_reason", sa.String(), nullable=True),
            sa.Column("activated_at", sa.DateTime(), nullable=True),
            sa.Column("deactivated_at", sa.DateTime(), nullable=True),
            sa.Column("last_verified_at", sa.DateTime(), nullable=True),
            sa.Column("license_metadata", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key_hash"),
        )
        op.create_index("ix_license_keys_key_hash", "license_keys", ["key_hash"], unique=True)
        op.create_index("ix_license_keys_key_prefix", "license_keys", ["key_prefix"], unique=False)
        op.create_index("ix_license_keys_workspace_id", "license_keys", ["workspace_id"], unique=False)
        op.create_index("ix_license_keys_tier", "license_keys", ["tier"], unique=False)
        op.create_index("ix_license_keys_active", "license_keys", ["active"], unique=False)

    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("workspaces")}
    columns = [
        ("license_key_id", sa.String(), True),
        ("license_key_prefix", sa.String(), True),
        ("license_tier", sa.String(), True),
        ("license_issued_at", sa.DateTime(), True),
        ("license_expires_at", sa.DateTime(), True),
        ("license_download_url", sa.String(), True),
    ]
    for name, col_type, nullable in columns:
        if name not in existing_cols:
            op.add_column("workspaces", sa.Column(name, col_type, nullable=nullable))

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("workspaces")}
    if "ix_workspaces_license_key_id" not in existing_indexes:
        op.create_index("ix_workspaces_license_key_id", "workspaces", ["license_key_id"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "ix_workspaces_license_key_id" in {ix["name"] for ix in inspector.get_indexes("workspaces")}:
        try:
            op.drop_index("ix_workspaces_license_key_id", table_name="workspaces")
        except Exception:
            pass

    for name in ["license_download_url", "license_expires_at", "license_issued_at", "license_tier", "license_key_prefix", "license_key_id"]:
        try:
            op.drop_column("workspaces", name)
        except Exception:
            pass

    if "license_keys" in inspector.get_table_names():
        for idx in [
            "ix_license_keys_active",
            "ix_license_keys_tier",
            "ix_license_keys_workspace_id",
            "ix_license_keys_key_prefix",
            "ix_license_keys_key_hash",
        ]:
            try:
                op.drop_index(idx, table_name="license_keys")
            except Exception:
                pass
        op.drop_table("license_keys")
