-- RADIUS Settings Table
-- Run this on your PostgreSQL database

CREATE TABLE IF NOT EXISTS radius_settings (
    id SERIAL PRIMARY KEY,
    
    -- Session Settings
    default_session_timeout INTEGER DEFAULT 3600,
    max_session_timeout INTEGER DEFAULT 86400,
    
    -- Bandwidth Settings (in kbps, 0 = unlimited)
    default_bandwidth_down INTEGER DEFAULT 0,
    default_bandwidth_up INTEGER DEFAULT 0,
    
    -- Concurrent Sessions
    max_concurrent_sessions INTEGER DEFAULT 1,
    
    -- Idle Timeout
    idle_timeout INTEGER DEFAULT 600,
    
    -- Data Limits (in MB, 0 = unlimited)
    daily_data_limit INTEGER DEFAULT 0,
    monthly_data_limit INTEGER DEFAULT 0,
    
    -- Authentication Settings
    allow_multiple_devices BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Insert default settings if table is empty
INSERT INTO radius_settings (
    default_session_timeout,
    max_session_timeout,
    default_bandwidth_down,
    default_bandwidth_up,
    max_concurrent_sessions,
    idle_timeout,
    daily_data_limit,
    monthly_data_limit,
    allow_multiple_devices
)
SELECT 3600, 86400, 0, 0, 1, 600, 0, 0, FALSE
WHERE NOT EXISTS (SELECT 1 FROM radius_settings);

SELECT 'RADIUS Settings table created successfully!' as status;
