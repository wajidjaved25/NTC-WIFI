-- Database Federation Setup for Main Server
-- This allows main server to query firewall logs from syslog server
-- Run on MAIN SERVER after syslog server is setup

-- Enable postgres_fdw extension
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- Drop existing objects if they exist
DROP MATERIALIZED VIEW IF EXISTS user_bandwidth_summary CASCADE;
DROP FOREIGN TABLE IF EXISTS firewall_logs CASCADE;
DROP USER MAPPING IF EXISTS FOR ntc_admin SERVER syslog_server;
DROP USER MAPPING IF EXISTS FOR postgres SERVER syslog_server;
DROP SERVER IF EXISTS syslog_server CASCADE;

-- Create foreign server pointing to syslog server
CREATE SERVER syslog_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host '192.168.3.245', 
        port '5432', 
        dbname 'ntc_wifi_logs',
        fetch_size '10000'
    );

-- Create user mapping for ntc_admin
CREATE USER MAPPING FOR ntc_admin
    SERVER syslog_server
    OPTIONS (
        user 'syslog_user', 
        password 'NTCWifiLogs2024Secure'
    );

-- Create user mapping for postgres superuser
CREATE USER MAPPING FOR postgres
    SERVER syslog_server
    OPTIONS (
        user 'syslog_user', 
        password 'NTCWifiLogs2024Secure'
    );

-- Import firewall_logs table schema
IMPORT FOREIGN SCHEMA public 
LIMIT TO (firewall_logs)
FROM SERVER syslog_server
INTO public;

-- Test connection
SELECT 'Foreign table imported' as status, COUNT(*) as log_count FROM firewall_logs;

-- Create indices on foreign table for better query performance
-- Note: These are on the remote server, add them there if needed

-- Create materialized view for fast IPDR queries
-- This will only work after session correlation runs
CREATE MATERIALIZED VIEW IF NOT EXISTS user_bandwidth_summary AS
SELECT 
    u.id as user_id,
    u.mobile,
    u.name as full_name,
    COUNT(DISTINCT fl.session_id) as session_count,
    COALESCE(SUM(fl.sent_bytes), 0) as total_sent,
    COALESCE(SUM(fl.received_bytes), 0) as total_received,
    COALESCE(SUM(fl.sent_bytes + fl.received_bytes), 0) as total_bytes,
    COUNT(fl.id) as log_count,
    MIN(fl.log_timestamp) as first_seen,
    MAX(fl.log_timestamp) as last_seen
FROM users u
LEFT JOIN firewall_logs fl ON u.id = fl.user_id
WHERE fl.user_id IS NOT NULL
  AND fl.log_timestamp > NOW() - INTERVAL '30 days'
GROUP BY u.id, u.mobile, u.name;

-- Create indices on materialized view
CREATE INDEX IF NOT EXISTS idx_user_bw_summary_user ON user_bandwidth_summary(user_id);
CREATE INDEX IF NOT EXISTS idx_user_bw_summary_mobile ON user_bandwidth_summary(mobile);
CREATE INDEX IF NOT EXISTS idx_user_bw_summary_bytes ON user_bandwidth_summary(total_bytes DESC);

-- Grant permissions
GRANT SELECT ON firewall_logs TO ntc_admin;
GRANT SELECT ON user_bandwidth_summary TO ntc_admin;

-- Create refresh function
CREATE OR REPLACE FUNCTION refresh_user_bandwidth_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_bandwidth_summary;
EXCEPTION
    WHEN OTHERS THEN
        -- If concurrent refresh fails, do regular refresh
        REFRESH MATERIALIZED VIEW user_bandwidth_summary;
END;
$$ LANGUAGE plpgsql;

-- Grant execute on function
GRANT EXECUTE ON FUNCTION refresh_user_bandwidth_summary() TO ntc_admin;

-- Verify setup
SELECT 
    'Foreign server setup complete' as status,
    COUNT(*) as firewall_logs_count
FROM firewall_logs;

SELECT 
    'Materialized view created' as status,
    COUNT(*) as users_with_data
FROM user_bandwidth_summary;

-- Instructions for cron job (optional - run every hour)
-- Add to /etc/cron.d/ntc-wifi-refresh:
-- 0 * * * * postgres psql -d ntc_wifi_admin -c "SELECT refresh_user_bandwidth_summary();" >> /var/log/ntc-wifi-refresh.log 2>&1
