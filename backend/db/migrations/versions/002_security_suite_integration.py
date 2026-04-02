"""Security Suite integration: auth, security events, subscriptions, content safety

Revision ID: 002_security_suite
Revises: 001_autonomous_ml_edge
Create Date: 2025-03-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_security_suite'
down_revision = '001_autonomous_ml_edge'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────────

    op.execute("CREATE TYPE userrole AS ENUM ('owner','admin','analyst','user','readonly')")
    op.execute("CREATE TYPE userstatus AS ENUM ('active','inactive','suspended','locked')")
    op.execute("CREATE TYPE threattype AS ENUM ('malware','phishing','ddos','intrusion','data_breach','anomaly','brute_force','unauthorized_access','content_violation','api_abuse')")
    op.execute("CREATE TYPE securitylevel AS ENUM ('low','medium','high','critical')")
    op.execute("CREATE TYPE plantier AS ENUM ('starter','pro','enterprise')")
    op.execute("CREATE TYPE subscriptionstatus AS ENUM ('active','trialing','past_due','canceled','incomplete','paused')")
    op.execute("CREATE TYPE contentcategory AS ENUM ('safe','adult','restricted','blocked')")
    op.execute("CREATE TYPE ageverificationstatus AS ENUM ('unverified','pending','verified','rejected')")
    op.execute("CREATE TYPE alertseverity AS ENUM ('info','low','medium','high','critical')")

    # ── Upgrade users table ───────────────────────────────────────────────────

    op.add_column('users', sa.Column('role', sa.Enum('owner','admin','analyst','user','readonly', name='userrole'), nullable=False, server_default='user'))
    op.add_column('users', sa.Column('status', sa.Enum('active','inactive','suspended','locked', name='userstatus'), nullable=False, server_default='active'))
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('mfa_secret', sa.String(), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('account_locked_until', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_activity', sa.DateTime(), nullable=True))

    # ── user_sessions ─────────────────────────────────────────────────────────

    op.create_table(
        'user_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('session_token', sa.String(), nullable=False, unique=True),
        sa.Column('refresh_token', sa.String(), nullable=True, unique=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('device_fingerprint', sa.String(), nullable=True),
        sa.Column('location', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_accessed', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_session_token', 'user_sessions', ['session_token'])
    op.create_index('ix_user_sessions_is_active', 'user_sessions', ['is_active'])

    # ── api_keys ──────────────────────────────────────────────────────────────

    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=False),
        sa.Column('rate_limit_per_minute', sa.String(), nullable=False, server_default='60'),
        sa.Column('allowed_ips', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_keys_workspace_id', 'api_keys', ['workspace_id'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('ix_api_keys_is_active', 'api_keys', ['is_active'])

    # ── security_events ───────────────────────────────────────────────────────

    op.create_table(
        'security_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), sa.ForeignKey('workspaces.id'), nullable=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('threat_type', sa.Enum('malware','phishing','ddos','intrusion','data_breach','anomaly','brute_force','unauthorized_access','content_violation','api_abuse', name='threattype'), nullable=True),
        sa.Column('security_level', sa.Enum('low','medium','high','critical', name='securitylevel'), nullable=False, server_default='medium'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('ai_analysis', sa.JSON(), nullable=True),
        sa.Column('ai_recommendations', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='open'),
        sa.Column('assigned_to', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_security_events_workspace_id', 'security_events', ['workspace_id'])
    op.create_index('ix_security_events_event_type', 'security_events', ['event_type'])
    op.create_index('ix_security_events_status', 'security_events', ['status'])
    op.create_index('ix_security_events_created_at', 'security_events', ['created_at'])

    # ── subscriptions ─────────────────────────────────────────────────────────

    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), sa.ForeignKey('workspaces.id'), nullable=False, unique=True),
        sa.Column('stripe_customer_id', sa.String(), nullable=True, unique=True),
        sa.Column('stripe_subscription_id', sa.String(), nullable=True, unique=True),
        sa.Column('stripe_product_id', sa.String(), nullable=True),
        sa.Column('stripe_price_id', sa.String(), nullable=True),
        sa.Column('plan', sa.Enum('starter','pro','enterprise', name='plantier'), nullable=False, server_default='starter'),
        sa.Column('status', sa.Enum('active','trialing','past_due','canceled','incomplete','paused', name='subscriptionstatus'), nullable=False, server_default='trialing'),
        sa.Column('billing_cycle', sa.String(), nullable=False, server_default='monthly'),
        sa.Column('amount_cents', sa.String(), nullable=False, server_default='2900'),
        sa.Column('currency', sa.String(), nullable=False, server_default='usd'),
        sa.Column('trial_end', sa.DateTime(), nullable=True),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_subscriptions_workspace_id', 'subscriptions', ['workspace_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])

    # ── content_filter_logs ───────────────────────────────────────────────────

    op.create_table(
        'content_filter_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('asset_id', sa.String(), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=True),
        sa.Column('category', sa.Enum('safe','adult','restricted','blocked', name='contentcategory'), nullable=False, server_default='safe'),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('flags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('action_taken', sa.String(), nullable=False, server_default='allow'),
        sa.Column('blocked_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_content_filter_logs_workspace_id', 'content_filter_logs', ['workspace_id'])
    op.create_index('ix_content_filter_logs_created_at', 'content_filter_logs', ['created_at'])

    # ── age_verifications ─────────────────────────────────────────────────────

    op.create_table(
        'age_verifications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('status', sa.Enum('unverified','pending','verified','rejected', name='ageverificationstatus'), nullable=False, server_default='unverified'),
        sa.Column('verification_method', sa.String(), nullable=True),
        sa.Column('verification_token', sa.String(), nullable=True, unique=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_age_verifications_user_id', 'age_verifications', ['user_id'])
    op.create_index('ix_age_verifications_status', 'age_verifications', ['status'])

    # ── system_metrics ────────────────────────────────────────────────────────

    op.create_table(
        'system_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metric_unit', sa.String(), nullable=True),
        sa.Column('service', sa.String(), nullable=True),
        sa.Column('environment', sa.String(), nullable=True),
        sa.Column('region', sa.String(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_system_metrics_metric_name', 'system_metrics', ['metric_name'])
    op.create_index('ix_system_metrics_timestamp', 'system_metrics', ['timestamp'])
    op.create_index('ix_system_metrics_service', 'system_metrics', ['service'])

    # ── alerts ────────────────────────────────────────────────────────────────

    op.create_table(
        'alerts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), sa.ForeignKey('workspaces.id'), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.Enum('info','low','medium','high','critical', name='alertseverity'), nullable=False, server_default='medium'),
        sa.Column('alert_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='open'),
        sa.Column('assigned_to', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alerts_workspace_id', 'alerts', ['workspace_id'])
    op.create_index('ix_alerts_severity', 'alerts', ['severity'])
    op.create_index('ix_alerts_status', 'alerts', ['status'])
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'])


def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_table('system_metrics')
    op.drop_table('age_verifications')
    op.drop_table('content_filter_logs')
    op.drop_table('subscriptions')
    op.drop_table('security_events')
    op.drop_table('api_keys')
    op.drop_table('user_sessions')

    op.drop_column('users', 'last_activity')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'account_locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'mfa_secret')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'status')
    op.drop_column('users', 'role')

    op.execute("DROP TYPE IF EXISTS alertseverity")
    op.execute("DROP TYPE IF EXISTS ageverificationstatus")
    op.execute("DROP TYPE IF EXISTS contentcategory")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
    op.execute("DROP TYPE IF EXISTS plantier")
    op.execute("DROP TYPE IF EXISTS securitylevel")
    op.execute("DROP TYPE IF EXISTS threattype")
    op.execute("DROP TYPE IF EXISTS userstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
