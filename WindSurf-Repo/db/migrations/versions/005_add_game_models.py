"""Add game models

Revision ID: 005_add_game_models
Revises: 004_add_clipcrafter_models
Create Date: 2025-02-04

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005_add_game_models"
down_revision = "004_add_clipcrafter_models"
branch_labels = None
depends_on = None


def upgrade():
    # Game profiles
    op.create_table(
        "game_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("current_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("player_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("coins", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("total_games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unlocked_particles", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("unlocked_themes", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("unlocked_powerups", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("sound_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("music_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("vibration_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_game_profiles_user_id", "game_profiles", ["user_id"], unique=True)
    op.create_index("ix_game_profiles_workspace_id", "game_profiles", ["workspace_id"])

    # Level progress
    op.create_table(
        "game_level_progress",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("level_number", sa.Integer(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_perfect", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("best_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_time", sa.Float(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hints_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coins_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xp_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_played_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["profile_id"], ["game_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_game_level_progress_profile_id", "game_level_progress", ["profile_id"])
    op.create_index("ix_game_level_progress_level_number", "game_level_progress", ["level_number"])

    # Purchases
    op.create_table(
        "game_purchases",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("product_id", sa.String(), nullable=False),
        sa.Column("product_type", sa.String(), nullable=False),
        sa.Column("amount_paid", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="USD"),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("transaction_id", sa.String(), nullable=False),
        sa.Column("receipt_data", sa.Text(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_consumed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("coins_granted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_granted", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["profile_id"], ["game_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_game_purchases_profile_id", "game_purchases", ["profile_id"])
    op.create_index("ix_game_purchases_product_id", "game_purchases", ["product_id"])
    op.create_index(
        "ix_game_purchases_transaction_id", "game_purchases", ["transaction_id"], unique=True
    )

    # Achievements
    op.create_table(
        "game_achievements",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("achievement_id", sa.String(), nullable=False),
        sa.Column("achievement_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target", sa.Integer(), nullable=False),
        sa.Column("is_unlocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("coins_reward", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_reward", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("unlocked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["profile_id"], ["game_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_game_achievements_profile_id", "game_achievements", ["profile_id"])
    op.create_index("ix_game_achievements_achievement_id", "game_achievements", ["achievement_id"])

    # Leaderboards
    op.create_table(
        "game_leaderboards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("leaderboard_type", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level_reached", sa.Integer(), nullable=False),
        sa.Column("total_xp", sa.Integer(), nullable=False),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["profile_id"], ["game_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_game_leaderboards_profile_id", "game_leaderboards", ["profile_id"])
    op.create_index(
        "ix_game_leaderboards_leaderboard_type", "game_leaderboards", ["leaderboard_type"]
    )
    op.create_index("ix_game_leaderboards_score", "game_leaderboards", ["score"])


def downgrade():
    op.drop_table("game_leaderboards")
    op.drop_table("game_achievements")
    op.drop_table("game_purchases")
    op.drop_table("game_level_progress")
    op.drop_table("game_profiles")
