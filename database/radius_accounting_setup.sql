-- RADIUS Accounting Database Setup Script
-- Run this on your PostgreSQL database

-- ===========================================
-- RADIUS Accounting Table (radacct)
-- This is the main table that stores session data
-- ===========================================
CREATE TABLE IF NOT EXISTS radacct (
    radacctid BIGSERIAL PRIMARY KEY,
    acctsessionid VARCHAR(64) NOT NULL,
    acctuniqueid VARCHAR(32) NOT NULL UNIQUE,
    username VARCHAR(64) NOT NULL,
    realm VARCHAR(64),
    nasipaddress INET NOT NULL,
    nasportid VARCHAR(32),
    nasporttype VARCHAR(32),
    acctstarttime TIMESTAMP WITH TIME ZONE,
    acctupdatetime TIMESTAMP WITH TIME ZONE,
    acctstoptime TIMESTAMP WITH TIME ZONE,
    acctinterval INTEGER,
    acctsessiontime INTEGER,
    acctauthentic VARCHAR(32),
    connectinfo_start VARCHAR(128),
    connectinfo_stop VARCHAR(128),
    acctinputoctets BIGINT DEFAULT 0,
    acctoutputoctets BIGINT DEFAULT 0,
    calledstationid VARCHAR(64),
    callingstationid VARCHAR(64),
    acctterminatecause VARCHAR(32),
    servicetype VARCHAR(32),
    framedprotocol VARCHAR(32),
    framedipaddress INET,
    framedipv6address VARCHAR(64),
    framedipv6prefix VARCHAR(64),
    framedinterfaceid VARCHAR(64),
    delegatedipv6prefix VARCHAR(64)
);

-- Indexes for radacct
CREATE INDEX IF NOT EXISTS radacct_username_idx ON radacct (username);
CREATE INDEX IF NOT EXISTS radacct_acctsessionid_idx ON radacct (acctsessionid);
CREATE INDEX IF NOT EXISTS radacct_acctsessiontime_idx ON radacct (acctsessiontime);
CREATE INDEX IF NOT EXISTS radacct_acctstarttime_idx ON radacct (acctstarttime);
CREATE INDEX IF NOT EXISTS radacct_acctuniqueid_idx ON radacct (acctuniqueid);
CREATE INDEX IF NOT EXISTS radacct_nasipaddress_idx ON radacct (nasipaddress);
CREATE INDEX IF NOT EXISTS radacct_callingstationid_idx ON radacct (callingstationid);

-- ===========================================
-- RADIUS Check Table (radcheck)
-- Stores user credentials for authentication
-- ===========================================
CREATE TABLE IF NOT EXISTS radcheck (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL DEFAULT '',
    attribute VARCHAR(64) NOT NULL DEFAULT '',
    op CHAR(2) NOT NULL DEFAULT ':=',
    value VARCHAR(253) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS radcheck_username_idx ON radcheck (username);

-- ===========================================
-- RADIUS Reply Table (radreply)
-- Stores attributes to send back to NAS (timeout, bandwidth, etc.)
-- ===========================================
CREATE TABLE IF NOT EXISTS radreply (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL DEFAULT '',
    attribute VARCHAR(64) NOT NULL DEFAULT '',
    op CHAR(2) NOT NULL DEFAULT '=',
    value VARCHAR(253) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS radreply_username_idx ON radreply (username);

-- ===========================================
-- RADIUS Group Tables
-- ===========================================
CREATE TABLE IF NOT EXISTS radgroupcheck (
    id SERIAL PRIMARY KEY,
    groupname VARCHAR(64) NOT NULL DEFAULT '',
    attribute VARCHAR(64) NOT NULL DEFAULT '',
    op CHAR(2) NOT NULL DEFAULT ':=',
    value VARCHAR(253) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS radgroupcheck_groupname_idx ON radgroupcheck (groupname);

CREATE TABLE IF NOT EXISTS radgroupreply (
    id SERIAL PRIMARY KEY,
    groupname VARCHAR(64) NOT NULL DEFAULT '',
    attribute VARCHAR(64) NOT NULL DEFAULT '',
    op CHAR(2) NOT NULL DEFAULT '=',
    value VARCHAR(253) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS radgroupreply_groupname_idx ON radgroupreply (groupname);

CREATE TABLE IF NOT EXISTS radusergroup (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL DEFAULT '',
    groupname VARCHAR(64) NOT NULL DEFAULT '',
    priority INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS radusergroup_username_idx ON radusergroup (username);

-- ===========================================
-- NAS (Network Access Server) Table
-- Stores RADIUS clients (like Omada controller)
-- ===========================================
CREATE TABLE IF NOT EXISTS nas (
    id SERIAL PRIMARY KEY,
    nasname VARCHAR(128) NOT NULL,
    shortname VARCHAR(32),
    type VARCHAR(30) DEFAULT 'other',
    ports INTEGER,
    secret VARCHAR(60) NOT NULL DEFAULT 'testing123',
    server VARCHAR(64),
    community VARCHAR(50),
    description VARCHAR(200) DEFAULT 'RADIUS Client'
);
CREATE INDEX IF NOT EXISTS nas_nasname_idx ON nas (nasname);

-- ===========================================
-- Post-Auth Logging Table
-- ===========================================
CREATE TABLE IF NOT EXISTS radpostauth (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    pass VARCHAR(64),
    reply VARCHAR(32),
    authdate TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS radpostauth_username_idx ON radpostauth (username);
CREATE INDEX IF NOT EXISTS radpostauth_authdate_idx ON radpostauth (authdate);

-- ===========================================
-- Add Omada Controller as NAS Client
-- Update the IP and secret as needed
-- ===========================================
INSERT INTO nas (nasname, shortname, type, secret, description)
VALUES ('192.168.3.50', 'omada', 'other', 'testing123', 'TP-Link Omada Controller')
ON CONFLICT DO NOTHING;

-- ===========================================
-- Create default user group with settings
-- ===========================================
INSERT INTO radgroupreply (groupname, attribute, op, value)
VALUES 
    ('default', 'Session-Timeout', '=', '3600'),
    ('default', 'Idle-Timeout', '=', '600')
ON CONFLICT DO NOTHING;

-- ===========================================
-- Useful Views for Reporting
-- ===========================================

-- Active sessions view
CREATE OR REPLACE VIEW active_sessions AS
SELECT 
    username,
    callingstationid as mac_address,
    framedipaddress as ip_address,
    acctstarttime as start_time,
    EXTRACT(EPOCH FROM (NOW() - acctstarttime))::INTEGER as duration_seconds,
    acctinputoctets as bytes_in,
    acctoutputoctets as bytes_out,
    (acctinputoctets + acctoutputoctets) as total_bytes
FROM radacct
WHERE acctstoptime IS NULL
ORDER BY acctstarttime DESC;

-- Daily usage summary view
CREATE OR REPLACE VIEW daily_usage_summary AS
SELECT 
    DATE(acctstarttime) as usage_date,
    COUNT(*) as total_sessions,
    COUNT(DISTINCT username) as unique_users,
    SUM(acctinputoctets) as total_bytes_in,
    SUM(acctoutputoctets) as total_bytes_out,
    SUM(acctinputoctets + acctoutputoctets) as total_bytes,
    AVG(acctsessiontime) as avg_session_duration
FROM radacct
WHERE acctstarttime IS NOT NULL
GROUP BY DATE(acctstarttime)
ORDER BY usage_date DESC;

-- User usage summary view
CREATE OR REPLACE VIEW user_usage_summary AS
SELECT 
    username,
    COUNT(*) as total_sessions,
    SUM(acctsessiontime) as total_session_time,
    SUM(acctinputoctets) as total_bytes_in,
    SUM(acctoutputoctets) as total_bytes_out,
    SUM(acctinputoctets + acctoutputoctets) as total_bytes,
    MAX(acctstarttime) as last_session
FROM radacct
GROUP BY username
ORDER BY total_bytes DESC;

-- ===========================================
-- Grant permissions to your app user
-- Replace 'ntc_wifi_user' with your actual database user
-- ===========================================
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ntc_wifi_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ntc_wifi_user;

SELECT 'RADIUS Accounting tables created successfully!' as status;
