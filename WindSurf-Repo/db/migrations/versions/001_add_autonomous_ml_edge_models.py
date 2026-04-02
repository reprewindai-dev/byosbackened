"""Add autonomous ML and edge architecture models

Revision ID: 001_autonomous_ml_edge
Revises:
Create Date: 2025-01-14 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_autonomous_ml_edge"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types for Anomaly model
    op.execute("CREATE TYPE anomalyseverity AS ENUM ('low', 'medium', 'high', 'critical')")
    op.execute(
        "CREATE TYPE anomalytype AS ENUM ('cost_spike', 'traffic_spike', 'quality_degradation', 'latency_spike', 'failure_rate_increase', 'unusual_pattern')"
    )
    op.execute(
        "CREATE TYPE anomalystatus AS ENUM ('detected', 'investigating', 'remediated', 'false_positive', 'resolved')"
    )

    # Create routing_strategies table
    op.create_table(
        "routing_strategies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("operation_type", sa.String(), nullable=False),
        sa.Column("preferred_provider", sa.String(), nullable=True),
        sa.Column("provider_weights", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("exploration_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("strategy_type", sa.String(), nullable=False),
        sa.Column("constraints_json", sa.Text(), nullable=True),
        sa.Column("total_samples", sa.Integer(), nullable=False),
        sa.Column("learning_samples", sa.Integer(), nullable=False),
        sa.Column("best_provider_reward", sa.Numeric(10, 6), nullable=True),
        sa.Column("avg_cost_saved", sa.Numeric(10, 6), nullable=True),
        sa.Column("avg_quality_improvement", sa.Numeric(5, 4), nullable=True),
        sa.Column("avg_latency_reduction_ms", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_routing_strategies_workspace_id", "routing_strategies", ["workspace_id"])
    op.create_index(
        "ix_routing_strategies_operation_type", "routing_strategies", ["operation_type"]
    )
    op.create_index(
        "idx_routing_strategies_workspace_op",
        "routing_strategies",
        ["workspace_id", "operation_type"],
    )

    # Create traffic_patterns table
    op.create_table(
        "traffic_patterns",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("pattern_type", sa.String(), nullable=False),
        sa.Column("operation_type", sa.String(), nullable=True),
        sa.Column("pattern_data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("avg_requests_per_hour", sa.Numeric(10, 2), nullable=True),
        sa.Column("peak_hour", sa.Integer(), nullable=True),
        sa.Column("peak_day", sa.Integer(), nullable=True),
        sa.Column("predicted_spike_time", sa.DateTime(), nullable=True),
        sa.Column("predicted_spike_multiplier", sa.Numeric(5, 2), nullable=True),
        sa.Column("predicted_requests", sa.Integer(), nullable=True),
        sa.Column("samples_used", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_traffic_patterns_workspace_id", "traffic_patterns", ["workspace_id"])
    op.create_index(
        "idx_traffic_patterns_workspace_op", "traffic_patterns", ["workspace_id", "operation_type"]
    )

    # Create anomalies table
    op.create_table(
        "anomalies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=True),
        sa.Column(
            "anomaly_type",
            postgresql.ENUM(
                "cost_spike",
                "traffic_spike",
                "quality_degradation",
                "latency_spike",
                "failure_rate_increase",
                "unusual_pattern",
                name="anomalytype",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            postgresql.ENUM("low", "medium", "high", "critical", name="anomalyseverity"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "detected",
                "investigating",
                "remediated",
                "false_positive",
                "resolved",
                name="anomalystatus",
            ),
            nullable=False,
        ),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("detected_by", sa.String(), nullable=False),
        sa.Column("confidence_score", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("baseline_value", sa.String(), nullable=True),
        sa.Column("actual_value", sa.String(), nullable=True),
        sa.Column("deviation_percent", sa.String(), nullable=True),
        sa.Column("remediated_at", sa.DateTime(), nullable=True),
        sa.Column("remediation_action", sa.Text(), nullable=True),
        sa.Column("remediation_result", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anomalies_workspace_id", "anomalies", ["workspace_id"])
    op.create_index("ix_anomalies_detected_at", "anomalies", ["detected_at"])
    op.create_index(
        "idx_anomalies_workspace_detected", "anomalies", ["workspace_id", "detected_at"]
    )

    # Create savings_reports table
    op.create_table(
        "savings_reports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("total_savings", sa.Numeric(10, 6), nullable=False),
        sa.Column("baseline_cost", sa.Numeric(10, 6), nullable=False),
        sa.Column("actual_cost", sa.Numeric(10, 6), nullable=False),
        sa.Column("savings_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("latency_reduction_ms", sa.Integer(), nullable=True),
        sa.Column("cache_hit_rate_improvement", sa.Numeric(5, 4), nullable=True),
        sa.Column("operations_count", sa.Integer(), nullable=False),
        sa.Column("breakdown_by_operation", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("breakdown_by_provider", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("projected_next_month_savings", sa.Numeric(10, 6), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("generated_by", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_savings_reports_workspace_id", "savings_reports", ["workspace_id"])
    op.create_index(
        "idx_savings_reports_workspace_period",
        "savings_reports",
        ["workspace_id", "period_start", "period_end"],
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index("idx_savings_reports_workspace_period", table_name="savings_reports")
    op.drop_index("ix_savings_reports_workspace_id", table_name="savings_reports")
    op.drop_table("savings_reports")

    op.drop_index("idx_anomalies_workspace_detected", table_name="anomalies")
    op.drop_index("ix_anomalies_detected_at", table_name="anomalies")
    op.drop_index("ix_anomalies_workspace_id", table_name="anomalies")
    op.drop_table("anomalies")

    op.drop_index("idx_traffic_patterns_workspace_op", table_name="traffic_patterns")
    op.drop_index("ix_traffic_patterns_workspace_id", table_name="traffic_patterns")
    op.drop_table("traffic_patterns")

    op.drop_index("idx_routing_strategies_workspace_op", table_name="routing_strategies")
    op.drop_index("ix_routing_strategies_operation_type", table_name="routing_strategies")
    op.drop_index("ix_routing_strategies_workspace_id", table_name="routing_strategies")
    op.drop_table("routing_strategies")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS anomalystatus")
    op.execute("DROP TYPE IF EXISTS anomalytype")
    op.execute("DROP TYPE IF EXISTS anomalyseverity")
