-- IPDR (Internet Protocol Detail Record) Tables
-- For compliance with regulatory requirements

-- Firewall Logs Table
CREATE TABLE IF NOT EXISTS firewall_logs (
    id SERIAL PRIMARY KEY,
    
    -- Timestamp Information
    log_date DATE NOT NULL,
    log_time TIME NOT NULL,
    log_timestamp TIMESTAMP NOT NULL,
    
    -- User Session Correlation
    session_id INTEGER REFERENCES sessions(id),
    user_id INTEGER REFERENCES users(id),
    
    -- Network Information
    source_ip VARCHAR(45) NOT NULL,
    source_port INTEGER NOT NULL,
    source_mac VARCHAR(17),
    source_interface VARCHAR(100),
    
    translated_ip VARCHAR(45),
    translated_port INTEGER,
    
    destination_ip VARCHAR(45) NOT NULL,
    destination_port INTEGER NOT NULL,
    destination_country VARCHAR(100),
    
    -- Protocol & Application
    protocol INTEGER, -- 6=TCP, 17=UDP
    protocol_name VARCHAR(20),
    service VARCHAR(100),
    app_name VARCHAR(100),
    app_category VARCHAR(100),
    
    -- Traffic Data
    sent_bytes BIGINT DEFAULT 0,
    received_bytes BIGINT DEFAULT 0,
    sent_packets INTEGER DEFAULT 0,
    received_packets INTEGER DEFAULT 0,
    duration INTEGER, -- seconds
    
    -- Action & Policy
    action VARCHAR(50),
    policy_id INTEGER,
    policy_name VARCHAR(100),
    
    -- Additional Metadata
    url TEXT,
    domain_name VARCHAR(255),
    device_type VARCHAR(100),
    os_name VARCHAR(100),
    
    -- Import Information
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    csv_filename VARCHAR(255),
    raw_log_data JSONB,
    
    -- Indexes for fast queries
    CONSTRAINT fk_session FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for IPDR queries
CREATE INDEX IF NOT EXISTS idx_firewall_timestamp ON firewall_logs(log_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_firewall_date ON firewall_logs(log_date DESC);
CREATE INDEX IF NOT EXISTS idx_firewall_source_ip ON firewall_logs(source_ip);
CREATE INDEX IF NOT EXISTS idx_firewall_user ON firewall_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_firewall_session ON firewall_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_firewall_dest_ip ON firewall_logs(destination_ip);
CREATE INDEX IF NOT EXISTS idx_firewall_url ON firewall_logs USING gin(to_tsvector('english', url));

-- CSV Import Jobs Table
CREATE TABLE IF NOT EXISTS firewall_import_jobs (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT,
    total_rows INTEGER,
    processed_rows INTEGER DEFAULT 0,
    imported_rows INTEGER DEFAULT 0,
    failed_rows INTEGER DEFAULT 0,
    status VARCHAR(50) NOT NULL, -- pending, processing, completed, failed
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    imported_by INTEGER REFERENCES admins(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_import_status ON firewall_import_jobs(status, created_at DESC);

-- IPDR Search History (for audit)
CREATE TABLE IF NOT EXISTS ipdr_search_history (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admins(id),
    search_type VARCHAR(50), -- cnic, mobile, date_range, ip
    search_params JSONB,
    results_count INTEGER,
    exported BOOLEAN DEFAULT FALSE,
    search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

CREATE INDEX IF NOT EXISTS idx_search_history ON ipdr_search_history(admin_id, search_timestamp DESC);
