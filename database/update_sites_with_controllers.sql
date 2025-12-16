-- UPDATED Multi-Site Management Schema
-- One Controller can manage Multiple Sites

-- Drop existing tables
DROP TABLE IF EXISTS nas_clients CASCADE;
DROP TABLE IF EXISTS sites CASCADE;
DROP TABLE IF EXISTS omada_controllers CASCADE;

-- Omada Controllers Table (One controller can manage many sites)
CREATE TABLE IF NOT EXISTS omada_controllers (
    id SERIAL PRIMARY KEY,
    controller_name VARCHAR(100) NOT NULL UNIQUE,
    controller_type VARCHAR(20) DEFAULT 'cloud', -- 'cloud' or 'on-premise'
    
    -- Controller Access
    controller_url VARCHAR(255) NOT NULL, -- https://omada.tplinkcloud.com or local IP
    controller_port INTEGER DEFAULT 8043,
    username VARCHAR(100),
    password_encrypted TEXT,
    
    -- Controller Info
    controller_id VARCHAR(100), -- For cloud controllers
    api_key TEXT, -- If using API key auth
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_connected TIMESTAMP,
    connection_status VARCHAR(20) DEFAULT 'unknown', -- online, offline, unknown
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES admins(id)
);

-- Sites Table (Many sites can belong to one controller)
CREATE TABLE IF NOT EXISTS sites (
    id SERIAL PRIMARY KEY,
    
    -- Basic Info
    site_name VARCHAR(100) NOT NULL UNIQUE,
    site_code VARCHAR(20) NOT NULL UNIQUE,
    location VARCHAR(255),
    
    -- Controller Reference
    controller_id INTEGER NOT NULL REFERENCES omada_controllers(id) ON DELETE RESTRICT,
    omada_site_id VARCHAR(100) DEFAULT 'Default', -- Site ID within Omada controller
    
    -- RADIUS Configuration (Each site needs unique CoA port)
    radius_nas_ip VARCHAR(45) NOT NULL, -- Usually the AP/gateway IP at this site
    radius_secret VARCHAR(100) NOT NULL,
    radius_coa_port INTEGER NOT NULL UNIQUE, -- Must be unique per site
    
    -- Portal Settings
    portal_url VARCHAR(255), -- Custom portal URL if needed
    custom_branding JSONB, -- Site-specific branding
    
    -- Network Info
    network_subnet VARCHAR(50), -- e.g., 192.168.1.0/24
    gateway_ip VARCHAR(45),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES admins(id)
);

-- NAS Clients Table (RADIUS clients per site)
CREATE TABLE IF NOT EXISTS nas_clients (
    id SERIAL PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id) ON DELETE CASCADE,
    nasname VARCHAR(128) NOT NULL, -- IP address of NAS (AP/Gateway at site)
    shortname VARCHAR(32),
    type VARCHAR(30) DEFAULT 'other',
    secret VARCHAR(60) NOT NULL,
    coa_port INTEGER NOT NULL,
    description VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, nasname)
);

-- Add indexes
CREATE INDEX idx_sites_controller ON sites(controller_id);
CREATE INDEX idx_sites_site_code ON sites(site_code);
CREATE INDEX idx_sites_active ON sites(is_active);
CREATE INDEX idx_sites_coa_port ON sites(radius_coa_port);
CREATE INDEX idx_nas_clients_site ON nas_clients(site_id);
CREATE INDEX idx_nas_clients_nasname ON nas_clients(nasname);
CREATE INDEX idx_controllers_active ON omada_controllers(is_active);

-- Update existing tables to reference sites
ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS site_ref_id INTEGER REFERENCES sites(id);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS site_id INTEGER REFERENCES sites(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS registered_site_id INTEGER REFERENCES sites(id);

-- Update triggers
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_controllers_timestamp 
BEFORE UPDATE ON omada_controllers
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_sites_timestamp 
BEFORE UPDATE ON sites
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Example Data: One Controller managing multiple sites

-- Insert Omada Controller (only once!)
INSERT INTO omada_controllers (
    controller_name, 
    controller_type,
    controller_url, 
    controller_port,
    username,
    password_encrypted,
    controller_id,
    created_by
) VALUES
('Main Omada Cloud', 'cloud', 'https://omada.tplinkcloud.com', 8043, 'admin', 'ENCRYPTED_PASS', 'cloud_controller_123', 1),
('Local Controller', 'on-premise', 'https://192.168.1.100', 8043, 'admin', 'ENCRYPTED_PASS', NULL, 1);

-- Insert Multiple Sites (all using same controller)
INSERT INTO sites (
    site_name, 
    site_code, 
    location,
    controller_id, -- Reference to controller
    omada_site_id, -- Site ID within Omada
    radius_nas_ip, 
    radius_secret, 
    radius_coa_port,
    created_by
) VALUES
-- All sites use controller_id = 1 (Main Omada Cloud)
('Main Office', 'MAIN', 'Islamabad HQ', 1, 'Default', '192.168.1.50', 'testing123', 3799, 1),
('Branch Office', 'BRANCH', 'Rawalpindi Branch', 1, 'Branch', '192.168.2.50', 'testing123', 3800, 1),
('Remote Site', 'REMOTE', 'Lahore Office', 1, 'Remote', '192.168.3.50', 'testing123', 3801, 1),
('Mall Kiosk', 'MALL', 'Centaurus Mall', 1, 'Mall', '192.168.4.50', 'testing123', 3802, 1);

-- Create corresponding NAS clients
INSERT INTO nas_clients (site_id, nasname, shortname, secret, coa_port, description)
SELECT 
    id,
    radius_nas_ip,
    LOWER(site_code),
    radius_secret,
    radius_coa_port,
    'NAS for ' || site_name
FROM sites;

-- Useful Views
CREATE OR REPLACE VIEW v_sites_with_controller AS
SELECT 
    s.id,
    s.site_name,
    s.site_code,
    s.location,
    s.omada_site_id,
    s.radius_nas_ip,
    s.radius_coa_port,
    s.is_active as site_active,
    c.id as controller_id,
    c.controller_name,
    c.controller_type,
    c.controller_url,
    c.controller_port,
    c.is_active as controller_active,
    nc.nasname,
    nc.secret as nas_secret
FROM sites s
JOIN omada_controllers c ON s.controller_id = c.id
LEFT JOIN nas_clients nc ON s.id = nc.site_id
WHERE s.is_active = TRUE;

-- View for active sessions by site and controller
CREATE OR REPLACE VIEW v_active_sessions_by_site AS
SELECT 
    s.site_name,
    s.site_code,
    c.controller_name,
    COUNT(*) as active_sessions,
    SUM(r.acctinputoctets + r.acctoutputoctets) / 1048576.0 as total_mb
FROM sites s
JOIN omada_controllers c ON s.controller_id = c.id
JOIN radacct r ON r.nasipaddress = s.radius_nas_ip
WHERE r.acctstoptime IS NULL
GROUP BY s.site_name, s.site_code, c.controller_name;

SELECT 'Updated multi-site schema with controller relationship created successfully!' as status;
