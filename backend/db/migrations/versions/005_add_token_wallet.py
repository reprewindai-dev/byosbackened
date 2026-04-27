"""Add token wallet and transaction tables.

Revision ID: 005
Revises: 004_add_routing_policy_and_missing_tables
Create Date: 2026-04-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004_add_routing_policy_and_missing_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create token_wallets table
    op.create_table(
        'token_wallets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('balance', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('monthly_credits_included', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('monthly_credits_used', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('monthly_period_start', sa.DateTime(), nullable=True),
        sa.Column('monthly_period_end', sa.DateTime(), nullable=True),
        sa.Column('total_credits_purchased', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_credits_used', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id')
    )
    op.create_index('ix_token_wallets_workspace_id', 'token_wallets', ['workspace_id'], unique=True)

    # Create token_transactions table
    op.create_table(
        'token_transactions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('wallet_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('transaction_type', sa.String(), nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('balance_before', sa.BigInteger(), nullable=False),
        sa.Column('balance_after', sa.BigInteger(), nullable=False),
        sa.Column('endpoint_path', sa.String(), nullable=True),
        sa.Column('endpoint_method', sa.String(), nullable=True),
        sa.Column('request_id', sa.String(), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(), nullable=True),
        sa.Column('stripe_checkout_session_id', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('metadata_json', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_token_transactions_wallet_id', 'token_transactions', ['wallet_id'])
    op.create_index('ix_token_transactions_workspace_id', 'token_transactions', ['workspace_id'])
    op.create_index('ix_token_transactions_transaction_type', 'token_transactions', ['transaction_type'])
    op.create_index('ix_token_transactions_request_id', 'token_transactions', ['request_id'])
    op.create_index('ix_token_transactions_stripe_payment_intent_id', 'token_transactions', ['stripe_payment_intent_id'])
    op.create_index('ix_token_transactions_created_at', 'token_transactions', ['created_at'])
    op.create_index('idx_token_transactions_workspace_created', 'token_transactions', ['workspace_id', sa.text('created_at DESC')])
    op.create_index('idx_token_transactions_type_created', 'token_transactions', ['transaction_type', sa.text('created_at DESC')])


def downgrade():
    op.drop_index('idx_token_transactions_type_created', table_name='token_transactions')
    op.drop_index('idx_token_transactions_workspace_created', table_name='token_transactions')
    op.drop_index('ix_token_transactions_created_at', table_name='token_transactions')
    op.drop_index('ix_token_transactions_stripe_payment_intent_id', table_name='token_transactions')
    op.drop_index('ix_token_transactions_request_id', table_name='token_transactions')
    op.drop_index('ix_token_transactions_transaction_type', table_name='token_transactions')
    op.drop_index('ix_token_transactions_workspace_id', table_name='token_transactions')
    op.drop_index('ix_token_transactions_wallet_id', table_name='token_transactions')
    op.drop_table('token_transactions')
    op.drop_index('ix_token_wallets_workspace_id', table_name='token_wallets')
    op.drop_table('token_wallets')
