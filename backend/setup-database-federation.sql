-- Database Federation Setup for Main Server
-- This allows main server to query firewall logs from syslog server
-- Run on MAIN SERVER after syslog server is setup

-- Enable postgres_fdw extension
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- Create foreign server pointing to syslog server
-- UPDATE SYSLOG_SERVER_IP with actual IP
CREATE SERVER syslog_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'SYSLOG_SERVER_IP', 
        port '5432', 
        dbname 'ntc_wifi_logs',
        fetch_size '10000'
    );

-- Create user mapping
-- UPDATE with actual database user/password
CREATE USER MAPPING FOR ntc_admin
    SERVER syslog_server
    OPTIONS (
        user 'syslog_user', 
        password 'SecureLogPassword123'
    );

-- Import firewall_logs table schema
IMPORT FOREIGN SCHEMA public 
LIMIT TO (firewall_logs)
FROM SERVER syslog_server
INTO public;

-- Test connection
SELECT COUNT(*) FROM firewall_logs;

-- Create materialized view for fast IPDR queries
CREATE MATERIALIZED VIEW user_bandwidth_summary AS
SELECT 
    u.id as user_id,
    u.mobile,
    u.name as full_name,
    COUNT(DISTINCT fl.session_id) as session_count,
    SUM(fl.sent_bytes) as total_sent,
    SUM(fl.received_bytes) as total_received,
    SUM(fl.sent_bytes + fl.received_bytes) as total_bytes,
    COUNT(*) as log_count,
    MIN(fl.log_timestamp) as first_seen,
    MAX(fl.log_timestamp) as last_seen,
    DATE(MAX(fl.log_timestamp)) as last_activity_date
FROM users u
LEFT JOIN firewall_logs fl ON u.id = fl.user_id
WHERE fl.log_timestamp > NOW() - INTERVAL '30 days'
GROUP BY u.id, u.mobile, u.name;

-- Create indices on materialized view
CREATE INDEX idx_user_bw_summary_user ON user_bandwidth_summary(user_id);
CREATE INDEX idx_user_bw_summary_mobile ON user_bandwidth_summary(mobile);
CREATE INDEX idx_user_bw_summary_bytes ON user_bandwidth_summary(total_bytes DESC);

-- Grant permissions
GRANT SELECT ON user_bandwidth_summary TO ntc_admin;

-- Create refresh function
CREATE OR REPLACE FUNCTION refresh_user_bandwidth_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_bandwidth_summary;
END;
$$ LANGUAGE plpgsql;

-- Schedule auto-refresh (run every hour via cron)
-- Add to /etc/cron.d/ntc-wifi-refresh:
-- 0 * * * * postgres psql -d ntc_wifi_admin -c "SELECT refresh_user_bandwidth_summary();"

-- Verify setup
SELECT 
    'Foreign server setup complete' as status,
    COUNT(*) as firewall_logs_count
FROM firewall_logs;

SELECT 
    'Materialized view ready' as status,
    COUNT(*) as users_with_data
FROM user_bandwidth_summary;
