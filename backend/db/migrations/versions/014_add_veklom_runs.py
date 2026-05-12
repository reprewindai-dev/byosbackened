"""Add canonical VeklomRun table."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _has_index(inspector, table: str, name: str) -> bool:
    try:
        return any(index.get("name") == name for index in inspector.get_indexes(table))
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "veklom_runs"):
        op.create_table(
            "veklom_runs",
            sa.Column("run_id", sa.String(), nullable=False),
            sa.Column("workspace_id", sa.String(), nullable=False),
            sa.Column("tenant_id", sa.String(), nullable=False),
            sa.Column("actor_id", sa.String(), nullable=True),
            sa.Column("parent_run_id", sa.String(), nullable=True),
            sa.Column("delegation_depth", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("raw_intent", sa.Text(), nullable=False),
            sa.Column("compiled_plan_json", sa.Text(), nullable=True),
            sa.Column("task_graph_json", sa.Text(), nullable=True),
            sa.Column("human_attestation_json", sa.Text(), nullable=True),
            sa.Column("ai_attestation_json", sa.Text(), nullable=True),
            sa.Column("execution_attestation_json", sa.Text(), nullable=True),
            sa.Column("policy_version", sa.String(), nullable=False, server_default="uacp-v5"),
            sa.Column("constitution_hash", sa.String(), nullable=False, server_default="unsealed"),
            sa.Column("governance_decision", sa.String(), nullable=False, server_default="ALLOW"),
            sa.Column("risk_tier", sa.String(), nullable=False, server_default="LOW"),
            sa.Column("hitl_required", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("genome_hash", sa.String(), nullable=False),
            sa.Column("input_hash", sa.String(), nullable=False),
            sa.Column("output_hash", sa.String(), nullable=True),
            sa.Column("decision_frame_hash", sa.String(), nullable=True),
            sa.Column("provenance_json", sa.Text(), nullable=True),
            sa.Column("provider", sa.String(), nullable=True),
            sa.Column("model", sa.String(), nullable=True),
            sa.Column("route_json", sa.Text(), nullable=True),
            sa.Column("reserve_before_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("approved_budget_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("debit_cents", sa.Numeric(10, 6), nullable=False, server_default="0"),
            sa.Column("reserve_after_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("over_budget", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("evidence_json", sa.Text(), nullable=True),
            sa.Column("feedback_json", sa.Text(), nullable=True),
            sa.Column("source_table", sa.String(), nullable=False),
            sa.Column("source_id", sa.String(), nullable=False),
            sa.Column("request_log_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="SEALED"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("sealed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("run_id"),
        )

    indexes = [
        ("ix_veklom_runs_workspace_id", ["workspace_id"]),
        ("ix_veklom_runs_tenant_id", ["tenant_id"]),
        ("ix_veklom_runs_actor_id", ["actor_id"]),
        ("ix_veklom_runs_parent_run_id", ["parent_run_id"]),
        ("ix_veklom_runs_governance_decision", ["governance_decision"]),
        ("ix_veklom_runs_risk_tier", ["risk_tier"]),
        ("ix_veklom_runs_genome_hash", ["genome_hash"]),
        ("ix_veklom_runs_input_hash", ["input_hash"]),
        ("ix_veklom_runs_output_hash", ["output_hash"]),
        ("ix_veklom_runs_decision_frame_hash", ["decision_frame_hash"]),
        ("ix_veklom_runs_provider", ["provider"]),
        ("ix_veklom_runs_model", ["model"]),
        ("ix_veklom_runs_source_table", ["source_table"]),
        ("ix_veklom_runs_source_id", ["source_id"]),
        ("ix_veklom_runs_request_log_id", ["request_log_id"]),
        ("ix_veklom_runs_status", ["status"]),
        ("ix_veklom_runs_created_at", ["created_at"]),
        ("ix_veklom_runs_updated_at", ["updated_at"]),
        ("ix_veklom_runs_sealed_at", ["sealed_at"]),
    ]
    for index_name, columns in indexes:
        if not _has_index(inspector, "veklom_runs", index_name):
            op.create_index(index_name, "veklom_runs", columns)

    if not _has_index(inspector, "veklom_runs", "idx_veklom_runs_workspace_created"):
        op.create_index("idx_veklom_runs_workspace_created", "veklom_runs", ["workspace_id", "created_at"])
    if not _has_index(inspector, "veklom_runs", "idx_veklom_runs_source"):
        op.create_index("idx_veklom_runs_source", "veklom_runs", ["source_table", "source_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_table(inspector, "veklom_runs"):
        return
    op.drop_table("veklom_runs")
