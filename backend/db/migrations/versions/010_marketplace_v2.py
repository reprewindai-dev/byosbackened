"""Marketplace v2 — categories, types, install payload, ratings, automation flags.

Adds a self-organizing listing schema so vendors can publish without admin curation:
- listing_type / category / tags / slug for discovery
- version + install_payload for one-click install into pipelines
- install_count + rating_avg + rating_count for trending/featured
- summary + compliance_badges (JSON) for auto-generated card UI
- predicted_cost_per_run cached from /cost/predict
- auto_classified / auto_validated / validation_report for the automation pipeline
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _has_column(inspector, table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in inspector.get_columns(table))
    except Exception:
        return False


def _has_index(inspector, table: str, name: str) -> bool:
    try:
        return any(i.get("name") == name for i in inspector.get_indexes(table))
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "listings"):
        return  # nothing to extend; bail

    cols = [
        ("listing_type", sa.Column("listing_type", sa.String(), nullable=True, server_default="pipeline")),
        ("category", sa.Column("category", sa.String(), nullable=True)),
        ("tags", sa.Column("tags", sa.JSON(), nullable=True)),
        ("slug", sa.Column("slug", sa.String(), nullable=True)),
        ("version", sa.Column("version", sa.String(), nullable=True, server_default="1.0.0")),
        ("install_payload", sa.Column("install_payload", sa.JSON(), nullable=True)),
        ("install_count", sa.Column("install_count", sa.Integer(), nullable=True, server_default="0")),
        ("rating_avg", sa.Column("rating_avg", sa.Float(), nullable=True, server_default="0")),
        ("rating_count", sa.Column("rating_count", sa.Integer(), nullable=True, server_default="0")),
        ("summary", sa.Column("summary", sa.Text(), nullable=True)),
        ("compliance_badges", sa.Column("compliance_badges", sa.JSON(), nullable=True)),
        ("predicted_cost_per_run", sa.Column("predicted_cost_per_run", sa.Numeric(10, 6), nullable=True)),
        ("auto_classified", sa.Column("auto_classified", sa.Boolean(), nullable=True, server_default=sa.text("false"))),
        ("auto_validated", sa.Column("auto_validated", sa.Boolean(), nullable=True, server_default=sa.text("false"))),
        ("validation_report", sa.Column("validation_report", sa.JSON(), nullable=True)),
        ("source_url", sa.Column("source_url", sa.String(), nullable=True)),
        ("is_featured", sa.Column("is_featured", sa.Boolean(), nullable=True, server_default=sa.text("false"))),
    ]

    for name, col in cols:
        if not _has_column(inspector, "listings", name):
            op.add_column("listings", col)

    for idx_name, col_name in [
        ("ix_listings_listing_type", "listing_type"),
        ("ix_listings_category", "category"),
        ("ix_listings_slug", "slug"),
        ("ix_listings_install_count", "install_count"),
        ("ix_listings_is_featured", "is_featured"),
    ]:
        if not _has_index(inspector, "listings", idx_name):
            try:
                op.create_index(idx_name, "listings", [col_name])
            except Exception:
                pass


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "listings"):
        return

    for idx_name in (
        "ix_listings_listing_type",
        "ix_listings_category",
        "ix_listings_slug",
        "ix_listings_install_count",
        "ix_listings_is_featured",
    ):
        if _has_index(inspector, "listings", idx_name):
            try:
                op.drop_index(idx_name, table_name="listings")
            except Exception:
                pass

    for col_name in (
        "listing_type", "category", "tags", "slug", "version",
        "install_payload", "install_count", "rating_avg", "rating_count",
        "summary", "compliance_badges", "predicted_cost_per_run",
        "auto_classified", "auto_validated", "validation_report",
        "source_url", "is_featured",
    ):
        if _has_column(inspector, "listings", col_name):
            try:
                op.drop_column("listings", col_name)
            except Exception:
                pass
