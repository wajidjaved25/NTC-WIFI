-- WiFi Admin Portal Database Schema
-- PostgreSQL 14+

-- Drop existing tables if any (for fresh setup)
DROP TABLE IF EXISTS backup_status CASCADE;
DROP TABLE IF EXISTS system_logs CASCADE;
DROP TABLE IF EXISTS daily_usage CASCADE;
DROP TABLE IF EXISTS ad_analytics CASCADE;
DROP TABLE IF EXISTS advertisements CASCADE;
DROP TABLE IF EXISTS portal_design CASCADE;
DROP TABLE IF EXISTS omada_config CASCADE;
DROP TABLE IF EXISTS otps CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS admins CASCADE;
DROP TABLE IF EXISTS portal_settings CASCADE;

-- Portal Settings (Domain configuration, branding, etc.)
CREATE TABLE portal_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(50) DEFAULT 'string', -- string, boolean, integer, json
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER
);

-- Insert default portal settings
INSERT INTO portal_settings (setting_key, setting_value, setting_type, description) VALUES
('portal_domain', 'admin.local', 'string', 'Custom domain for admin portal'),
('portal_url', 'http://10.2.49.27:3000', 'string', 'Full URL for admin portal access'),
('enable_ip_masking', 'true', 'boolean', 'Enable IP address masking'),
('company_name', 'NTC Public WiFi', 'string', 'Company/Organization name'),
('support_email', 'support@ntc.local', 'string', 'Support email address'),
('max_daily_connections', '3', 'integer', 'Maximum connections per user per day'),
('otp_expiry_minutes', '5', 'integer', 'OTP expiration time in minutes'),
('session_timeout_warning', '300', 'integer', 'Show warning before session timeout (seconds)');

-- Admins table with role-based access
CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255), -- NULL for OTP-only users
    role VARCHAR(50) NOT NULL CHECK (role IN ('superadmin', 'admin', 'reports_user', 'ads_user')),
    mobile VARCHAR(20), -- Required for OTP-based roles
    full_name VARCHAR(255),
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    requires_otp BOOLEAN DEFAULT FALSE, -- True for reports_user and ads_user
    created_by INTEGER REFERENCES admins(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    CONSTRAINT mobile_required_for_otp CHECK (
        (requires_otp = TRUE AND mobile IS NOT NULL) OR requires_otp = FALSE
    )
);

-- Create default superadmin (password: SuperAdmin@2025)
INSERT INTO admins (username, password_hash, role, full_name, requires_otp) VALUES
('superadmin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIr.5gixlO', 'superadmin', 'System Administrator', FALSE);

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    mobile VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255),
    is_blocked BOOLEAN DEFAULT FALSE,
    block_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    total_sessions INTEGER DEFAULT 0,
    total_data_usage BIGINT DEFAULT 0
);

-- OTP Management
CREATE TABLE otps (
    id SERIAL PRIMARY KEY,
    mobile VARCHAR(20) NOT NULL,
    otp VARCHAR(6) NOT NULL,
    otp_type VARCHAR(20) DEFAULT 'user_login', -- user_login, admin_login
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    attempts INTEGER DEFAULT 0,
    ip_address VARCHAR(45)
);

-- Create index for faster OTP lookup
CREATE INDEX idx_otps_mobile_verified ON otps(mobile, verified, expires_at);

-- Omada Controller Configuration
CREATE TABLE omada_config (
    id SERIAL PRIMARY KEY,
    config_name VARCHAR(100) NOT NULL DEFAULT 'Default',
    controller_url VARCHAR(255) NOT NULL,
    controller_id VARCHAR(100),
    username VARCHAR(100) NOT NULL,
    password_encrypted TEXT NOT NULL,
    site_id VARCHAR(100) DEFAULT 'Default',
    site_name VARCHAR(100),
    
    -- Authentication Settings
    auth_type VARCHAR(50) DEFAULT 'external',
    redirect_url VARCHAR(255),
    
    -- Session Control
    session_timeout INTEGER DEFAULT 3600, -- seconds (1 hour)
    idle_timeout INTEGER DEFAULT 600, -- seconds (10 minutes)
    daily_time_limit INTEGER DEFAULT 7200, -- seconds per day (2 hours)
    max_daily_sessions INTEGER DEFAULT 3,
    
    -- Bandwidth Control
    bandwidth_limit_up INTEGER, -- kbps
    bandwidth_limit_down INTEGER, -- kbps
    
    -- Advanced Settings
    enable_rate_limiting BOOLEAN DEFAULT TRUE,
    rate_limit_up INTEGER, -- kbps
    rate_limit_down INTEGER, -- kbps
    
    -- Data Limits
    daily_data_limit BIGINT, -- bytes per day
    session_data_limit BIGINT, -- bytes per session
    
    -- Access Control
    enable_mac_filtering BOOLEAN DEFAULT FALSE,
    allowed_mac_addresses TEXT[], -- array of MAC addresses
    blocked_mac_addresses TEXT[], -- array of MAC addresses
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES admins(id)
);

-- Insert default Omada config
INSERT INTO omada_config (config_name, controller_url, username, password_encrypted, site_id) VALUES
('Default Controller', 'https://10.2.49.26:8043', 'admin', 'ENCRYPTED_PASSWORD_HERE', 'Default');

-- WiFi Sessions
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    mac_address VARCHAR(17) NOT NULL,
    ip_address VARCHAR(45),
    ap_mac VARCHAR(17),
    ap_name VARCHAR(100),
    ssid VARCHAR(100),
    site VARCHAR(100),
    
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration INTEGER, -- in seconds
    
    data_upload BIGINT DEFAULT 0, -- bytes
    data_download BIGINT DEFAULT 0, -- bytes
    total_data BIGINT DEFAULT 0, -- bytes
    
    disconnect_reason VARCHAR(100), -- timeout, admin, user, limit_reached, error
    session_status VARCHAR(50) DEFAULT 'active', -- active, completed, terminated
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for session queries
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_mac ON sessions(mac_address);
CREATE INDEX idx_sessions_start ON sessions(start_time DESC);
CREATE INDEX idx_sessions_status ON sessions(session_status);

-- User Daily Usage Tracking
CREATE TABLE daily_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    usage_date DATE NOT NULL,
    total_duration INTEGER DEFAULT 0, -- seconds
    session_count INTEGER DEFAULT 0,
    data_upload BIGINT DEFAULT 0,
    data_download BIGINT DEFAULT 0,
    total_data BIGINT DEFAULT 0,
    last_session_at TIMESTAMP,
    UNIQUE(user_id, usage_date)
);

CREATE INDEX idx_daily_usage_user_date ON daily_usage(user_id, usage_date DESC);

-- Portal Design Configuration
CREATE TABLE portal_design (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL,
    
    -- Branding
    logo_path VARCHAR(255),
    favicon_path VARCHAR(255),
    background_image VARCHAR(255),
    background_type VARCHAR(20) DEFAULT 'image', -- image, color, gradient
    
    -- Colors
    primary_color VARCHAR(7) DEFAULT '#1890ff',
    secondary_color VARCHAR(7) DEFAULT '#ffffff',
    accent_color VARCHAR(7) DEFAULT '#52c41a',
    text_color VARCHAR(7) DEFAULT '#000000',
    background_color VARCHAR(7) DEFAULT '#f0f2f5',
    
    -- Content
    welcome_title VARCHAR(255) DEFAULT 'Welcome to Free WiFi',
    welcome_text TEXT DEFAULT 'Please register to connect to our WiFi network',
    terms_text TEXT,
    footer_text VARCHAR(255),
    
    -- Layout
    custom_css TEXT,
    custom_js TEXT,
    layout_type VARCHAR(50) DEFAULT 'centered', -- centered, split, fullscreen
    
    -- Status
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES admins(id)
);

-- Insert default portal design
INSERT INTO portal_design (template_name, welcome_title, welcome_text, is_active) VALUES
('Default Template', 'Welcome to NTC Public WiFi', 'Please enter your details to connect to free WiFi', TRUE);

-- Advertisement Management
CREATE TABLE advertisements (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- File Info
    ad_type VARCHAR(20) NOT NULL CHECK (ad_type IN ('video', 'image', 'download')),
    file_path VARCHAR(255) NOT NULL,
    file_name VARCHAR(255),
    file_size BIGINT,
    mime_type VARCHAR(100),
    
    -- Display Settings
    display_duration INTEGER DEFAULT 10, -- seconds (for video/image)
    display_order INTEGER DEFAULT 0, -- sequence order
    auto_skip BOOLEAN DEFAULT FALSE, -- allow user to skip
    skip_after INTEGER DEFAULT 5, -- seconds before skip button appears
    
    -- Scheduling
    is_active BOOLEAN DEFAULT TRUE,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    auto_disable BOOLEAN DEFAULT FALSE,
    
    -- Target Audience (future feature)
    target_audience JSONB, -- {"age_group": "18-35", "location": "city"}
    
    -- Analytics
    view_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    skip_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES admins(id)
);

-- Ad Analytics (detailed tracking)
CREATE TABLE ad_analytics (
    id SERIAL PRIMARY KEY,
    ad_id INTEGER REFERENCES advertisements(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    mac_address VARCHAR(17),
    
    event_type VARCHAR(50), -- view, click, skip, complete
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    watch_duration INTEGER, -- seconds watched
    
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ad_analytics_ad ON ad_analytics(ad_id, event_type);
CREATE INDEX idx_ad_analytics_timestamp ON ad_analytics(event_timestamp DESC);

-- System Logs
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    log_level VARCHAR(20) NOT NULL, -- INFO, WARNING, ERROR, CRITICAL
    module VARCHAR(100), -- auth, omada, session, ads, etc.
    action VARCHAR(100),
    message TEXT NOT NULL,
    details JSONB,
    user_id INTEGER REFERENCES admins(id),
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_logs_level_module ON system_logs(log_level, module);
CREATE INDEX idx_logs_created ON system_logs(created_at DESC);

-- Backup Status
CREATE TABLE backup_status (
    id SERIAL PRIMARY KEY,
    backup_type VARCHAR(50) NOT NULL, -- database, media, config, full
    backup_path VARCHAR(255),
    file_name VARCHAR(255),
    file_size BIGINT,
    status VARCHAR(50) NOT NULL, -- running, success, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    triggered_by VARCHAR(50), -- manual, scheduled, auto
    created_by INTEGER REFERENCES admins(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_backup_status ON backup_status(status, backup_type);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_omada_config_updated_at BEFORE UPDATE ON omada_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portal_design_updated_at BEFORE UPDATE ON portal_design
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_advertisements_updated_at BEFORE UPDATE ON advertisements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portal_settings_updated_at BEFORE UPDATE ON portal_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
