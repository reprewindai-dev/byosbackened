"""Add routing_policy and missing tables

Revision ID: 004_routing_policy_missing
Revises: 003_ollama_exec_multitenant
Create Date: 2025-04-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_routing_policy_missing'
down_revision = '003_ollama_exec_multitenant'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create routing_policies table
    op.create_table(
        'routing_policies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False, unique=True),
        sa.Column('strategy', sa.String(), nullable=False),
        sa.Column('constraints_json', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_routing_policies_workspace_id', 'routing_policies', ['workspace_id'])
    
    # Create ml_models table (if not exists)
    op.create_table(
        'ml_models',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('model_type', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('status', sa.String(), default='training', nullable=False),
        sa.Column('accuracy', sa.Numeric(5, 4), nullable=True),
        sa.Column('training_samples', sa.Integer(), default=0, nullable=False),
        sa.Column('feature_importance', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('model_path', sa.String(), nullable=True),
        sa.Column('is_production', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ml_models_workspace_id', 'ml_models', ['workspace_id'])
    op.create_index('ix_ml_models_model_type', 'ml_models', ['model_type'])
    op.create_index('idx_ml_models_workspace_type', 'ml_models', ['workspace_id', 'model_type'])
    
    # Create deployments table (if not exists)
    op.create_table(
        'deployments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('deployed_at', sa.DateTime(), nullable=True),
        sa.Column('rolled_back_at', sa.DateTime(), nullable=True),
        sa.Column('metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['ml_models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_deployments_workspace_id', 'deployments', ['workspace_id'])
    
    # Create execution_logs table (if not exists)
    op.create_table(
        'execution_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('completion_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('total_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('latency_ms', sa.Integer(), default=0, nullable=False),
        sa.Column('success', sa.Boolean(), default=True, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 6), default=0, nullable=False),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_execution_logs_workspace_id', 'execution_logs', ['workspace_id'])
    op.create_index('ix_execution_logs_tenant_id', 'execution_logs', ['tenant_id'])
    op.create_index('ix_execution_logs_created_at', 'execution_logs', ['created_at'])
    op.create_index('idx_execution_logs_workspace_created', 'execution_logs', ['workspace_id', 'created_at'])
    
    # Create security_events table (if not exists)
    op.create_table(
        'security_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_category', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('source_ip', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('request_path', sa.String(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('signature_matched', sa.String(), nullable=True),
        sa.Column('is_blocked', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_events_workspace_id', 'security_events', ['workspace_id'])
    op.create_index('ix_security_events_event_type', 'security_events', ['event_type'])
    op.create_index('ix_security_events_created_at', 'security_events', ['created_at'])
    op.create_index('idx_security_events_workspace_type', 'security_events', ['workspace_id', 'event_type'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_security_events_workspace_type', table_name='security_events')
    op.drop_index('ix_security_events_created_at', table_name='security_events')
    op.drop_index('ix_security_events_event_type', table_name='security_events')
    op.drop_index('ix_security_events_workspace_id', table_name='security_events')
    op.drop_table('security_events')
    
    op.drop_index('idx_execution_logs_workspace_created', table_name='execution_logs')
    op.drop_index('ix_execution_logs_created_at', table_name='execution_logs')
    op.drop_index('ix_execution_logs_tenant_id', table_name='execution_logs')
    op.drop_index('ix_execution_logs_workspace_id', table_name='execution_logs')
    op.drop_table('execution_logs')
    
    op.drop_index('ix_deployments_workspace_id', table_name='deployments')
    op.drop_table('deployments')
    
    op.drop_index('idx_ml_models_workspace_type', table_name='ml_models')
    op.drop_index('ix_ml_models_model_type', table_name='ml_models')
    op.drop_index('ix_ml_models_workspace_id', table_name='ml_models')
    op.drop_table('ml_models')
    
    op.drop_index('ix_routing_policies_workspace_id', table_name='routing_policies')
    op.drop_table('routing_policies')
