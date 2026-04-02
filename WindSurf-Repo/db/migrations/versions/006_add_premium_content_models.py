"""Add premium content platform models.

Revision ID: 006
Revises: 005
Create Date: 2026-02-04

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    # Create content_tags association table
    op.create_table(
        "content_tags",
        sa.Column("content_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("content_id", "tag_id"),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["content.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
        ),
    )

    # Create categories table
    op.create_table(
        "categories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.String(), nullable=True),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
        ),
    )
    op.create_index(
        op.f("ix_categories_workspace_id"), "categories", ["workspace_id"], unique=False
    )
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=False)
    op.create_index(op.f("ix_categories_slug"), "categories", ["slug"], unique=False)

    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
        ),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_tags_workspace_id"), "tags", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_tags_name"), "tags", ["name"], unique=False)
    op.create_index(op.f("ix_tags_slug"), "tags", ["slug"], unique=False)

    # Create content table
    op.create_table(
        "content",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("video_url", sa.String(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "content_type", sa.Enum("VIDEO", "LIVE", "PHOTO", name="contenttype"), nullable=False
        ),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "PUBLISHED", "ARCHIVED", "PROCESSING", name="contentstatus"),
            nullable=False,
        ),
        sa.Column("category_id", sa.String(), nullable=True),
        sa.Column("source_api", sa.String(), nullable=True),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False),
        sa.Column("favorite_count", sa.Integer(), nullable=False),
        sa.Column("quality", sa.String(), nullable=True),
        sa.Column("tags_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("performers_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
        ),
    )
    op.create_index(op.f("ix_content_workspace_id"), "content", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_content_title"), "content", ["title"], unique=False)
    op.create_index(op.f("ix_content_status"), "content", ["status"], unique=False)
    op.create_index(op.f("ix_content_category_id"), "content", ["category_id"], unique=False)
    op.create_index(op.f("ix_content_published_at"), "content", ["published_at"], unique=False)

    # Create subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column(
            "tier",
            sa.Enum("FREE", "BASIC", "PREMIUM", "VIP", name="subscriptiontier"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE", "CANCELLED", "EXPIRED", "PENDING", "TRIAL", name="subscriptionstatus"
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("price_period", sa.Float(), nullable=False),
        sa.Column("billing_period_days", sa.Integer(), nullable=False),
        sa.Column("auto_renew", sa.Boolean(), nullable=False),
        sa.Column("payment_provider", sa.String(), nullable=True),
        sa.Column("payment_provider_subscription_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
        ),
    )
    op.create_index(op.f("ix_subscriptions_user_id"), "subscriptions", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_subscriptions_workspace_id"), "subscriptions", ["workspace_id"], unique=False
    )
    op.create_index(op.f("ix_subscriptions_tier"), "subscriptions", ["tier"], unique=False)
    op.create_index(op.f("ix_subscriptions_status"), "subscriptions", ["status"], unique=False)
    op.create_index(
        op.f("ix_subscriptions_expires_at"), "subscriptions", ["expires_at"], unique=False
    )

    # Create payments table
    op.create_table(
        "payments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("subscription_id", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "COMPLETED", "FAILED", "REFUNDED", "CANCELLED", name="paymentstatus"
            ),
            nullable=False,
        ),
        sa.Column("payment_provider", sa.String(), nullable=False),
        sa.Column("provider_payment_id", sa.String(), nullable=True),
        sa.Column("provider_customer_id", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
        ),
    )
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_payments_subscription_id"), "payments", ["subscription_id"], unique=False
    )
    op.create_index(op.f("ix_payments_workspace_id"), "payments", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)
    op.create_index(
        op.f("ix_payments_provider_payment_id"), "payments", ["provider_payment_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_payments_provider_payment_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_status"), table_name="payments")
    op.drop_index(op.f("ix_payments_workspace_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_subscription_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_user_id"), table_name="payments")
    op.drop_table("payments")

    op.drop_index(op.f("ix_subscriptions_expires_at"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_status"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_tier"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_workspace_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_user_id"), table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index(op.f("ix_content_published_at"), table_name="content")
    op.drop_index(op.f("ix_content_category_id"), table_name="content")
    op.drop_index(op.f("ix_content_status"), table_name="content")
    op.drop_index(op.f("ix_content_title"), table_name="content")
    op.drop_index(op.f("ix_content_workspace_id"), table_name="content")
    op.drop_table("content")

    op.drop_index(op.f("ix_tags_slug"), table_name="tags")
    op.drop_index(op.f("ix_tags_name"), table_name="tags")
    op.drop_index(op.f("ix_tags_workspace_id"), table_name="tags")
    op.drop_table("tags")

    op.drop_index(op.f("ix_categories_slug"), table_name="categories")
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_workspace_id"), table_name="categories")
    op.drop_table("categories")

    op.drop_table("content_tags")
