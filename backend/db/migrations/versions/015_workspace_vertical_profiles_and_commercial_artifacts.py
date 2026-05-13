"""Add workspace vertical profile fields and commercial artifacts."""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _has_column(inspector, table: str, column: str) -> bool:
    try:
        return any(col.get("name") == column for col in inspector.get_columns(table))
    except Exception:
        return False


def _has_index(inspector, table: str, name: str) -> bool:
    try:
        return any(index.get("name") == name for index in inspector.get_indexes(table))
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    workspace_columns = {
        "industry": sa.Column("industry", sa.String(), nullable=False, server_default="generic"),
        "playground_profile": sa.Column("playground_profile", sa.String(), nullable=False, server_default="generic"),
        "risk_tier": sa.Column("risk_tier", sa.String(), nullable=False, server_default="generic"),
        "default_policy_pack": sa.Column("default_policy_pack", sa.String(), nullable=True),
        "default_demo_scenarios": sa.Column("default_demo_scenarios", sa.Text(), nullable=True),
        "default_evidence_requirements": sa.Column("default_evidence_requirements", sa.Text(), nullable=True),
        "default_blocking_rules": sa.Column("default_blocking_rules", sa.Text(), nullable=True),
    }
    for name, column in workspace_columns.items():
        if not _has_column(inspector, "workspaces", name):
            op.add_column("workspaces", column)

    if not _has_index(inspector, "workspaces", "ix_workspaces_industry"):
        op.create_index("ix_workspaces_industry", "workspaces", ["industry"])

    demo_defaults = json.dumps(
        [
            {
                "scenario_id": "generic_support_triage",
                "title": "Support ticket triage",
                "prompt": "We want to use AI to triage support tickets, summarize the case, route it to the right team, and keep an audit trail.",
                "suggested_workflow": [
                    "Read inbound ticket",
                    "Classify urgency and sensitive content",
                    "Summarize the case",
                    "Route to the correct team",
                    "Write replayable evidence",
                ],
                "suggested_models_tools": ["approved_chat_model", "ticket_router", "audit_archive"],
                "evidence_emphasis": ["approval trail", "policy decision", "cost trace", "audit export"],
            }
        ],
        sort_keys=True,
    )
    evidence_defaults = json.dumps(
        ["workflow objective", "policy decision", "model and tool used", "cost trace", "audit export"],
        sort_keys=True,
    )
    blocking_defaults = json.dumps(
        ["Block unsupported compliance or regulatory claims.", "Escalate high-risk actions for human review."],
        sort_keys=True,
    )
    op.execute(
        sa.text(
            """
            UPDATE workspaces
            SET industry = COALESCE(NULLIF(industry, ''), 'generic'),
                playground_profile = COALESCE(NULLIF(playground_profile, ''), 'generic'),
                risk_tier = COALESCE(NULLIF(risk_tier, ''), 'generic'),
                default_policy_pack = COALESCE(NULLIF(default_policy_pack, ''), 'generic_foundation_v1'),
                default_demo_scenarios = COALESCE(default_demo_scenarios, :demo_defaults),
                default_evidence_requirements = COALESCE(default_evidence_requirements, :evidence_defaults),
                default_blocking_rules = COALESCE(default_blocking_rules, :blocking_defaults)
            """
        ).bindparams(
            demo_defaults=demo_defaults,
            evidence_defaults=evidence_defaults,
            blocking_defaults=blocking_defaults,
        )
    )

    if not _has_table(inspector, "commercial_artifacts"):
        op.create_table(
            "commercial_artifacts",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("workspace_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("artifact_type", sa.String(), nullable=False, server_default="community_awareness_run"),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("source_type", sa.String(), nullable=False, server_default="vertical_playground"),
            sa.Column("source_scenario_id", sa.String(), nullable=True),
            sa.Column("handoff_json", sa.Text(), nullable=False),
            sa.Column("artifact_json", sa.Text(), nullable=False),
            sa.Column("founder_review_status", sa.String(), nullable=False, server_default="pending_founder_review"),
            sa.Column("spam_risk", sa.String(), nullable=False, server_default="medium"),
            sa.Column("regulated_claim_risk", sa.String(), nullable=False, server_default="high"),
            sa.Column("competitor_claim_risk", sa.String(), nullable=False, server_default="medium"),
            sa.Column("archive_record_id", sa.String(), nullable=True),
            sa.Column("outcome", sa.String(), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    commercial_indexes = [
        ("ix_commercial_artifacts_workspace_id", ["workspace_id"]),
        ("ix_commercial_artifacts_user_id", ["user_id"]),
        ("ix_commercial_artifacts_artifact_type", ["artifact_type"]),
        ("ix_commercial_artifacts_source_type", ["source_type"]),
        ("ix_commercial_artifacts_source_scenario_id", ["source_scenario_id"]),
        ("ix_commercial_artifacts_founder_review_status", ["founder_review_status"]),
        ("ix_commercial_artifacts_archive_record_id", ["archive_record_id"]),
        ("ix_commercial_artifacts_created_at", ["created_at"]),
        ("ix_commercial_artifacts_updated_at", ["updated_at"]),
    ]
    for index_name, columns in commercial_indexes:
        if not _has_index(inspector, "commercial_artifacts", index_name):
            op.create_index(index_name, "commercial_artifacts", columns)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "commercial_artifacts"):
        op.drop_table("commercial_artifacts")

    for column in [
        "default_blocking_rules",
        "default_evidence_requirements",
        "default_demo_scenarios",
        "default_policy_pack",
        "risk_tier",
        "playground_profile",
        "industry",
    ]:
        if _has_column(inspector, "workspaces", column):
            op.drop_column("workspaces", column)
