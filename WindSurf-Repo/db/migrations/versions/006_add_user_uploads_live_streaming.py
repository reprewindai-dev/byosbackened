"""Add user uploads and live streaming features.

Revision ID: 006b
Revises: 005
Create Date: 2026-02-04

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006b"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to content table
    op.add_column("content", sa.Column("uploaded_by_user_id", sa.String(), nullable=True))
    op.add_column("content", sa.Column("approved_by_admin_id", sa.String(), nullable=True))
    op.add_column("content", sa.Column("approval_notes", sa.Text(), nullable=True))
    op.add_column("content", sa.Column("approval_date", sa.DateTime(), nullable=True))
    op.add_column(
        "content", sa.Column("is_live", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "content", sa.Column("live_viewers_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("content", sa.Column("live_started_at", sa.DateTime(), nullable=True))
    op.add_column("content", sa.Column("live_ended_at", sa.DateTime(), nullable=True))
    op.add_column("content", sa.Column("live_stream_url", sa.String(), nullable=True))
    op.add_column(
        "content",
        sa.Column("live_chat_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )

    op.create_index("ix_content_uploaded_by_user_id", "content", ["uploaded_by_user_id"])
    op.create_index("ix_content_is_live", "content", ["is_live"])

    # Add foreign keys
    op.create_foreign_key(
        "fk_content_uploaded_by", "content", "users", ["uploaded_by_user_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_content_approved_by", "content", "users", ["approved_by_admin_id"], ["id"]
    )

    # Add columns to users table
    op.add_column("users", sa.Column("gems", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "users", sa.Column("total_live_sessions", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "users", sa.Column("total_live_minutes", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "users", sa.Column("total_live_viewers", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "users", sa.Column("monthly_live_score", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("users", sa.Column("last_month_rank", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column("free_month_earned", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_index("ix_users_monthly_live_score", "users", ["monthly_live_score"])

    # Create live_streams table
    op.create_table(
        "live_streams",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("content_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("rtmp_url", sa.String(), nullable=True),
        sa.Column("stream_key", sa.String(), nullable=True),
        sa.Column("playback_url", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("peak_viewers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_viewers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gifts_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gems_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduled_start", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chat_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("comments_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("gifts_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tags_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_live_streams_user_id", "live_streams", ["user_id"])
    op.create_index("ix_live_streams_workspace_id", "live_streams", ["workspace_id"])
    op.create_index("ix_live_streams_status", "live_streams", ["status"])
    op.create_foreign_key("fk_live_streams_user", "live_streams", "users", ["user_id"], ["id"])
    op.create_foreign_key(
        "fk_live_streams_workspace", "live_streams", "workspaces", ["workspace_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_live_streams_content", "live_streams", "content", ["content_id"], ["id"]
    )

    # Create live_stream_viewers table
    op.create_table(
        "live_stream_viewers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("stream_id", sa.String(), nullable=False),
        sa.Column("viewer_user_id", sa.String(), nullable=True),
        sa.Column("viewer_ip", sa.String(), nullable=True),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.Column("left_at", sa.DateTime(), nullable=True),
        sa.Column("watch_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_live_stream_viewers_stream_id", "live_stream_viewers", ["stream_id"])
    op.create_index(
        "ix_live_stream_viewers_viewer_user_id", "live_stream_viewers", ["viewer_user_id"]
    )
    op.create_foreign_key(
        "fk_live_stream_viewers_stream",
        "live_stream_viewers",
        "live_streams",
        ["stream_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_live_stream_viewers_user", "live_stream_viewers", "users", ["viewer_user_id"], ["id"]
    )

    # Create live_stream_gifts table
    op.create_table(
        "live_stream_gifts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("stream_id", sa.String(), nullable=False),
        sa.Column("sender_user_id", sa.String(), nullable=False),
        sa.Column("gift_type", sa.String(), nullable=False),
        sa.Column("gift_value", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_live_stream_gifts_stream_id", "live_stream_gifts", ["stream_id"])
    op.create_index("ix_live_stream_gifts_sender_user_id", "live_stream_gifts", ["sender_user_id"])
    op.create_foreign_key(
        "fk_live_stream_gifts_stream", "live_stream_gifts", "live_streams", ["stream_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_live_stream_gifts_sender", "live_stream_gifts", "users", ["sender_user_id"], ["id"]
    )

    # Create monthly_leaderboards table
    op.create_table(
        "monthly_leaderboards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("live_sessions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_live_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_viewers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_gems_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_gifts_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("reward_claimed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monthly_leaderboards_user_id", "monthly_leaderboards", ["user_id"])
    op.create_index(
        "ix_monthly_leaderboards_workspace_id", "monthly_leaderboards", ["workspace_id"]
    )
    op.create_index("ix_monthly_leaderboards_year", "monthly_leaderboards", ["year"])
    op.create_index("ix_monthly_leaderboards_month", "monthly_leaderboards", ["month"])
    op.create_index("ix_monthly_leaderboards_rank", "monthly_leaderboards", ["rank"])
    op.create_foreign_key(
        "fk_monthly_leaderboards_user", "monthly_leaderboards", "users", ["user_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_monthly_leaderboards_workspace",
        "monthly_leaderboards",
        "workspaces",
        ["workspace_id"],
        ["id"],
    )


def downgrade():
    # Drop tables
    op.drop_table("monthly_leaderboards")
    op.drop_table("live_stream_gifts")
    op.drop_table("live_stream_viewers")
    op.drop_table("live_streams")

    # Drop user columns
    op.drop_index("ix_users_monthly_live_score", "users")
    op.drop_column("users", "free_month_earned")
    op.drop_column("users", "last_month_rank")
    op.drop_column("users", "monthly_live_score")
    op.drop_column("users", "total_live_viewers")
    op.drop_column("users", "total_live_minutes")
    op.drop_column("users", "total_live_sessions")
    op.drop_column("users", "gems")

    # Drop content columns
    op.drop_constraint("fk_content_approved_by", "content", type_="foreignkey")
    op.drop_constraint("fk_content_uploaded_by", "content", type_="foreignkey")
    op.drop_index("ix_content_is_live", "content")
    op.drop_index("ix_content_uploaded_by_user_id", "content")
    op.drop_column("content", "live_chat_enabled")
    op.drop_column("content", "live_stream_url")
    op.drop_column("content", "live_ended_at")
    op.drop_column("content", "live_started_at")
    op.drop_column("content", "live_viewers_count")
    op.drop_column("content", "is_live")
    op.drop_column("content", "approval_date")
    op.drop_column("content", "approval_notes")
    op.drop_column("content", "approved_by_admin_id")
    op.drop_column("content", "uploaded_by_user_id")
