-- BYOS Backend - Multi-tenant Database Initialization
-- PostgreSQL RLS Setup

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create tenant table
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    api_key_hash VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    execution_limit INTEGER DEFAULT 1000,
    daily_execution_count INTEGER DEFAULT 0,
    last_execution_date DATE DEFAULT CURRENT_DATE
);

-- Create executions table
CREATE TABLE IF NOT EXISTS executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    model VARCHAR(100) NOT NULL,
    tokens_generated INTEGER DEFAULT 0,
    execution_time_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create tenant-specific settings table
CREATE TABLE IF NOT EXISTS tenant_settings (
    setting_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, setting_key)
);

-- Enable Row Level Security
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY;

-- RLS Policies for tenant isolation
CREATE POLICY tenant_isolation ON tenants
    USING (tenant_id = current_setting('request.tenant_id', true)::UUID);

CREATE POLICY execution_isolation ON executions
    USING (tenant_id = current_setting('request.tenant_id', true)::UUID);

CREATE POLICY tenant_settings_isolation ON tenant_settings
    USING (tenant_id = current_setting('request.tenant_id', true)::UUID);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_executions_tenant_id ON executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_executions_created_at ON executions(created_at);
CREATE INDEX IF NOT EXISTS idx_tenant_settings_tenant_id ON tenant_settings(tenant_id);

-- Insert default tenants with hashed API keys
-- Note: In production, these should be properly hashed using the application's hash_api_key function
INSERT INTO tenants (name, api_key_hash, execution_limit) VALUES
('AgencyOS', 'agencyos_key_123_hashed_placeholder', 1000),
('BattleArena', 'battlearena_key_456_hashed_placeholder', 2000),
('LumiNode', 'luminode_key_789_hashed_placeholder', 500)
ON CONFLICT (api_key_hash) DO NOTHING;

-- Create function to reset daily execution counts
CREATE OR REPLACE FUNCTION reset_daily_execution_counts()
RETURNS void AS $$
BEGIN
    UPDATE tenants 
    SET daily_execution_count = 0, last_execution_date = CURRENT_DATE
    WHERE last_execution_date < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for daily reset
CREATE OR REPLACE FUNCTION daily_reset_trigger()
RETURNS trigger AS $$
BEGIN
    PERFORM reset_daily_execution_counts();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to check and reset daily counts
CREATE OR REPLACE FUNCTION check_daily_limit()
RETURNS trigger AS $$
DECLARE
    current_count INTEGER;
    limit_count INTEGER;
BEGIN
    -- Reset daily count if needed
    PERFORM reset_daily_execution_counts();
    
    -- Get current count and limit
    SELECT daily_execution_count, execution_limit INTO current_count, limit_count
    FROM tenants
    WHERE tenant_id = NEW.tenant_id;
    
    -- Check limit
    IF current_count >= limit_count THEN
        RAISE EXCEPTION 'Daily execution limit exceeded for tenant %', NEW.tenant_id;
    END IF;
    
    -- Increment count
    UPDATE tenants
    SET daily_execution_count = daily_execution_count + 1
    WHERE tenant_id = NEW.tenant_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on executions table
CREATE TRIGGER enforce_daily_limit
    BEFORE INSERT ON executions
    FOR EACH ROW
    EXECUTE FUNCTION check_daily_limit();

-- Create view for tenant statistics
CREATE OR REPLACE VIEW tenant_stats AS
SELECT 
    t.tenant_id,
    t.name,
    t.is_active,
    t.execution_limit,
    t.daily_execution_count,
    COUNT(e.execution_id) as total_executions,
    AVG(e.execution_time_ms) as avg_execution_time_ms,
    SUM(e.tokens_generated) as total_tokens_generated,
    MAX(e.created_at) as last_execution
FROM tenants t
LEFT JOIN executions e ON t.tenant_id = e.tenant_id
GROUP BY t.tenant_id, t.name, t.is_active, t.execution_limit, t.daily_execution_count;

-- Grant permissions (adjust as needed)
GRANT USAGE ON SCHEMA public TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO PUBLIC;
GRANT INSERT, UPDATE ON tenants, executions, tenant_settings TO PUBLIC;
