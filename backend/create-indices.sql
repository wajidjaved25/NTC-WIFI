-- CRITICAL PERFORMANCE INDICES
-- Run on main server database

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_mobile ON users(mobile);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_active ON sessions(user_id) WHERE end_time IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_ip_mac ON sessions(ip_address, mac_address);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_time_range ON sessions(start_time, end_time);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_status ON sessions(session_status) WHERE session_status = 'active';
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_otp_mobile_exp ON otps(mobile, expires_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_admins_username ON admins(username);

ANALYZE users;
ANALYZE sessions;
ANALYZE otps;
ANALYZE admins;
