-- TimescaleDB Firewall Logs Schema
-- Run on syslog server

-- Create database and user
CREATE DATABASE ntc_wifi_logs;
CREATE USER syslog_user WITH PASSWORD 'SecureLogPassword123';
GRANT ALL PRIVILEGES ON DATABASE ntc_wifi_logs TO syslog_user;

-- Connect to database
\c ntc_wifi_logs

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO syslog_user;

-- Create firewall_logs table
CREATE TABLE firewall_logs (
    id SERIAL,
    
    -- Timestamp (for partitioning)
    log_timestamp TIMESTAMPTZ NOT NULL,
    log_date DATE NOT NULL,
    log_time TIME NOT NULL,
    
    -- Session correlation (filled later)
    session_id INTEGER,
    user_id INTEGER,
    
    -- Network information
    source_ip VARCHAR(45) NOT NULL,
    source_port INTEGER NOT NULL,
    source_mac VARCHAR(17),
    source_interface VARCHAR(100),
    translated_ip VARCHAR(45),
    translated_port INTEGER,
    destination_ip VARCHAR(45) NOT NULL,
    destination_port INTEGER NOT NULL,
    destination_country VARCHAR(100),
    
    -- Protocol
    protocol INTEGER,
    protocol_name VARCHAR(20),
    service VARCHAR(100),
    app_name VARCHAR(100),
    app_category VARCHAR(100),
    
    -- Traffic statistics
    sent_bytes BIGINT DEFAULT 0,
    received_bytes BIGINT DEFAULT 0,
    sent_packets INTEGER DEFAULT 0,
    received_packets INTEGER DEFAULT 0,
    duration INTEGER,
    
    -- Action and policy
    action VARCHAR(50),
    policy_id INTEGER,
    
    -- Metadata
    url TEXT,
    domain_name VARCHAR(255),
    device_type VARCHAR(100),
    os_name VARCHAR(100),
    raw_log_data JSONB
);

-- Convert to TimescaleDB hypertable (1-day chunks)
SELECT create_hypertable(
    'firewall_logs', 
    'log_timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indices
CREATE INDEX idx_firewall_timestamp ON firewall_logs(log_timestamp DESC);
CREATE INDEX idx_firewall_source_ip ON firewall_logs(source_ip, log_timestamp DESC);
CREATE INDEX idx_firewall_session ON firewall_logs(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_firewall_user ON firewall_logs(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_firewall_action ON firewall_logs(action);

-- Composite index for IPDR queries
CREATE INDEX idx_firewall_ipdr ON firewall_logs(user_id, log_timestamp) WHERE user_id IS NOT NULL;

-- Enable compression (compress after 3 days)
ALTER TABLE firewall_logs SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'source_ip',
    timescaledb.compress_orderby = 'log_timestamp DESC'
);

SELECT add_compression_policy('firewall_logs', INTERVAL '3 days');

-- Auto-delete after 1 YEAR (365 days) - UPDATED for 1 year retention
SELECT add_retention_policy('firewall_logs', INTERVAL '365 days');

-- Grant permissions
GRANT ALL ON firewall_logs TO syslog_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO syslog_user;

-- Analyze table
ANALYZE firewall_logs;

-- Display retention policy info
SELECT * FROM timescaledb_information.jobs WHERE proc_name = 'policy_retention';
