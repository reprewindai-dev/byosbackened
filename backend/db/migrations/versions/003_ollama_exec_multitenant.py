"""Ollama execution logs + multi-tenant RLS enforcement

Revision ID: 003_ollama_exec_multitenant
Revises: 002_security_suite
Create Date: 2026-04-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '003_ollama_exec_multitenant'
down_revision = '002_security_suite'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── execution_logs table ──────────────────────────────────────────────────
    op.create_table(
        'execution_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('workspace_id', sa.String(36), nullable=True),
        sa.Column('prompt', sa.Text, nullable=False),
        sa.Column('model', sa.String(128), nullable=False),
        sa.Column('response', sa.Text, nullable=True),
        sa.Column('prompt_tokens', sa.Integer, server_default='0'),
        sa.Column('completion_tokens', sa.Integer, server_default='0'),
        sa.Column('total_tokens', sa.Integer, server_default='0'),
        sa.Column('latency_ms', sa.Integer, server_default='0'),
        sa.Column('success', sa.Boolean, server_default='true'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('cost_usd', sa.Float, server_default='0.0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_execution_logs_tenant_id', 'execution_logs', ['tenant_id'])
    op.create_index(
        'ix_execution_logs_tenant_created',
        'execution_logs',
        ['tenant_id', 'created_at'],
    )

    # ── Postgres Row-Level Security (RLS) ─────────────────────────────────────
    # Enable RLS on all tenant tables
    tenant_tables = [
        'execution_logs',
        'jobs',
        'assets',
        'transcripts',
        'exports',
        'cost_predictions',
        'routing_decisions',
        'ai_audit_logs',
        'cost_allocations',
        'budgets',
        'security_audit_logs',
        'abuse_logs',
        'incident_logs',
        'security_events',
        'user_sessions',
        'api_keys',
        'subscriptions',
        'content_filter_logs',
        'age_verifications',
        'system_metrics',
        'alerts',
    ]

    for table in tenant_tables:
        try:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        except Exception:
            pass  # Table may not exist in all environments

    # execution_logs RLS policy — tenant isolation via request.tenant_id
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'execution_logs'
                AND policyname = 'tenant_isolation'
            ) THEN
                CREATE POLICY tenant_isolation ON execution_logs
                    USING (tenant_id = current_setting('request.tenant_id', true));
            END IF;
        END
        $$
    """)

    # ── Ensure tenant_id column exists on core tables ─────────────────────────
    # workspaces already serve as the tenant boundary — add tenant_id alias where missing
    for table, col in [
        ('jobs', 'workspace_id'),
        ('assets', 'workspace_id'),
    ]:
        try:
            op.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='{table}' AND column_name='tenant_id'
                    ) THEN
                        ALTER TABLE {table} ADD COLUMN tenant_id VARCHAR(36)
                            GENERATED ALWAYS AS ({col}) STORED;
                    END IF;
                END
                $$
            """)
        except Exception:
            pass

    # ── Redis key prefix enforcement note ────────────────────────────────────
    # Redis keys MUST use format: tenant:{tenant_id}:<key>
    # This is enforced at application layer (rate_limit.py, caching middleware).
    # No DB migration needed — documented here for architecture clarity.


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'execution_logs'
                AND policyname = 'tenant_isolation'
            ) THEN
                DROP POLICY tenant_isolation ON execution_logs;
            END IF;
        END
        $$
    """)

    op.execute("ALTER TABLE execution_logs DISABLE ROW LEVEL SECURITY")
    op.drop_index('ix_execution_logs_tenant_created', 'execution_logs')
    op.drop_index('ix_execution_logs_tenant_id', 'execution_logs')
    op.drop_table('execution_logs')
