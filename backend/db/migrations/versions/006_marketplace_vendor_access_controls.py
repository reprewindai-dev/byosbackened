"""Add marketplace vendor/listing tables with paid-plan fields.

Revision ID: 006
Revises: 005
Create Date: 2026-04-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def _ensure_vendors_table(bind) -> None:
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "vendors" not in tables:
        op.create_table(
            "vendors",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("workspace_id", sa.String(), nullable=False),
            sa.Column("display_name", sa.String(), nullable=False),
            sa.Column("plan", sa.String(), nullable=False, server_default="verified"),
            sa.Column("subscription_status", sa.String(), nullable=False, server_default="inactive"),
            sa.Column("stripe_account_id", sa.String(), nullable=True),
            sa.Column("is_onboarded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.UniqueConstraint("user_id"),
        )
        op.create_index("ix_vendors_user_id", "vendors", ["user_id"], unique=True)
        op.create_index("ix_vendors_workspace_id", "vendors", ["workspace_id"], unique=False)
        op.create_index("ix_vendors_plan", "vendors", ["plan"], unique=False)
        op.create_index("ix_vendors_subscription_status", "vendors", ["subscription_status"], unique=False)
        op.create_index("ix_vendors_stripe_account_id", "vendors", ["stripe_account_id"], unique=False)
        return

    existing_cols = {c["name"] for c in inspector.get_columns("vendors")}
    if "plan" not in existing_cols:
        op.add_column("vendors", sa.Column("plan", sa.String(), nullable=False, server_default="verified"))
    if "subscription_status" not in existing_cols:
        op.add_column(
            "vendors", sa.Column("subscription_status", sa.String(), nullable=False, server_default="inactive")
        )

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("vendors")}
    if "ix_vendors_plan" not in existing_indexes:
        op.create_index("ix_vendors_plan", "vendors", ["plan"], unique=False)
    if "ix_vendors_subscription_status" not in existing_indexes:
        op.create_index("ix_vendors_subscription_status", "vendors", ["subscription_status"], unique=False)


def _ensure_listings_table(bind) -> None:
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "listings" in tables:
        return

    op.create_table(
        "listings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("vendor_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(), nullable=False, server_default="usd"),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
    )
    op.create_index("ix_listings_vendor_id", "listings", ["vendor_id"], unique=False)
    op.create_index("ix_listings_workspace_id", "listings", ["workspace_id"], unique=False)
    op.create_index("ix_listings_status", "listings", ["status"], unique=False)
    op.create_index("ix_listings_created_at", "listings", ["created_at"], unique=False)


def upgrade():
    bind = op.get_bind()
    _ensure_vendors_table(bind)
    _ensure_listings_table(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "listings" in tables:
        for idx in ["ix_listings_created_at", "ix_listings_status", "ix_listings_workspace_id", "ix_listings_vendor_id"]:
            try:
                op.drop_index(idx, table_name="listings")
            except Exception:
                pass
        op.drop_table("listings")

    if "vendors" in tables:
        cols = {c["name"] for c in inspector.get_columns("vendors")}
        # If table pre-existed, remove only added indexes/columns when possible.
        if "plan" in cols and "subscription_status" in cols:
            for idx in ["ix_vendors_subscription_status", "ix_vendors_plan"]:
                try:
                    op.drop_index(idx, table_name="vendors")
                except Exception:
                    pass
            try:
                op.drop_column("vendors", "subscription_status")
            except Exception:
                pass
            try:
                op.drop_column("vendors", "plan")
            except Exception:
                pass
