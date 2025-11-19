-- ============================================
-- RADIUS Data Limits Diagnostic Script
-- ============================================
-- Run this on your PostgreSQL database to verify data limits

-- 1. Check RADIUS settings in your portal
SELECT 
    id,
    daily_data_limit as "Daily Limit (MB)",
    monthly_data_limit as "Monthly Limit (MB)",
    default_session_timeout as "Session Timeout (s)",
    default_bandwidth_down as "Bandwidth Down (kbps)",
    default_bandwidth_up as "Bandwidth Up (kbps)"
FROM radius_settings;

-- 2. Check if Max-Daily-Data is set for any users
SELECT 
    username,
    attribute,
    value as "Limit (bytes)",
    ROUND(CAST(value AS NUMERIC) / 1048576, 2) as "Limit (MB)"
FROM radcheck 
WHERE attribute IN ('Max-Daily-Data', 'Max-Monthly-Data')
ORDER BY username, attribute;

-- 3. Check current data usage for users (today)
SELECT 
    username,
    SUM(acctinputoctets + acctoutputoctets) as "Total Bytes",
    ROUND(SUM(acctinputoctets + acctoutputoctets) / 1048576.0, 2) as "Total MB"
FROM radacct
WHERE acctstarttime >= date_trunc('day', CURRENT_TIMESTAMP)
GROUP BY username
ORDER BY "Total Bytes" DESC;

-- 4. Check current data usage for users (this month)
SELECT 
    username,
    SUM(acctinputoctets + acctoutputoctets) as "Total Bytes",
    ROUND(SUM(acctinputoctets + acctoutputoctets) / 1048576.0, 2) as "Total MB"
FROM radacct
WHERE acctstarttime >= date_trunc('month', CURRENT_TIMESTAMP)
GROUP BY username
ORDER BY "Total Bytes" DESC;

-- 5. Check active sessions
SELECT 
    username,
    acctstarttime as "Start Time",
    acctinputoctets as "Bytes In",
    acctoutputoctets as "Bytes Out",
    callingstationid as "MAC"
FROM radacct 
WHERE acctstoptime IS NULL
ORDER BY acctstarttime DESC;

-- 6. Show all radcheck entries for a specific user (change username)
-- SELECT * FROM radcheck WHERE username = '03001234567';
-- SELECT * FROM radreply WHERE username = '03001234567';
