-- Multi-Site Management Schema
-- Run this to add site management capabilities

-- Sites/Locations Table
CREATE TABLE IF NOT EXISTS sites (
    id SERIAL PRIMARY KEY,
    site_name VARCHAR(100) NOT NULL UNIQUE,
    site_code VARCHAR(20) NOT NULL UNIQUE,
    location VARCHAR(255),
    
    -- Omada Controller Details
    omada_controller_ip VARCHAR(45) NOT NULL,
    omada_controller_port INTEGER DEFAULT 8043,
    omada_site_id VARCHAR(100) DEFAULT 'Default',
    omada_username VARCHAR(100),
    omada_password_encrypted TEXT,
    
    -- RADIUS Configuration
    radius_nas_ip VARCHAR(45) NOT NULL, -- Usually same as omada_controller_ip
    radius_secret VARCHAR(100) NOT NULL,
    radius_coa_port INTEGER NOT NULL UNIQUE, -- Must be unique per site (3799, 3800, 3801...)
    
    -- Portal Settings
    portal_url VARCHAR(255), -- Custom portal URL if needed
    custom_branding JSONB, -- Site-specific branding
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES admins(id)
);

-- Add indexes
CREATE INDEX idx_sites_site_code ON sites(site_code);
CREATE INDEX idx_sites_active ON sites(is_active);
CREATE INDEX idx_sites_coa_port ON sites(radius_coa_port);

-- Update omada_config to reference sites
ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS site_ref_id INTEGER REFERENCES sites(id);

-- Add site reference to sessions
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS site_id INTEGER REFERENCES sites(id);

-- Add site reference to users (optional - for site-specific user management)
ALTER TABLE users ADD COLUMN IF NOT EXISTS registered_site_id INTEGER REFERENCES sites(id);

-- NAS Clients Table (RADIUS clients per site)
CREATE TABLE IF NOT EXISTS nas_clients (
    id SERIAL PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id) ON DELETE CASCADE,
    nasname VARCHAR(128) NOT NULL, -- IP address of NAS (Omada controller)
    shortname VARCHAR(32),
    type VARCHAR(30) DEFAULT 'other',
    secret VARCHAR(60) NOT NULL,
    coa_port INTEGER NOT NULL,
    description VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, nasname)
);

CREATE INDEX idx_nas_clients_site ON nas_clients(site_id);
CREATE INDEX idx_nas_clients_nasname ON nas_clients(nasname);

-- Insert example sites
INSERT INTO sites (
    site_name, site_code, location,
    omada_controller_ip, omada_site_id,
    radius_nas_ip, radius_secret, radius_coa_port,
    created_by
) VALUES
('Main Office', 'MAIN', 'Islamabad HQ',
 '192.168.1.50', 'Default', '192.168.1.50', 'testing123', 3799, 1),
 
('Branch Office', 'BRANCH', 'Rawalpindi Branch',
 '192.168.2.50', 'Branch', '192.168.2.50', 'testing456', 3800, 1),
 
('Remote Site', 'REMOTE', 'Lahore Office',
 '192.168.3.50', 'Remote', '192.168.3.50', 'testing789', 3801, 1);

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

-- Update trigger for sites
CREATE OR REPLACE FUNCTION update_sites_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sites_updated_at 
BEFORE UPDATE ON sites
FOR EACH ROW EXECUTE FUNCTION update_sites_timestamp();

-- View for active sites with NAS info
CREATE OR REPLACE VIEW v_sites_with_nas AS
SELECT 
    s.id,
    s.site_name,
    s.site_code,
    s.location,
    s.omada_controller_ip,
    s.omada_site_id,
    s.radius_nas_ip,
    s.radius_coa_port,
    s.is_active,
    nc.nasname,
    nc.shortname as nas_shortname,
    nc.secret as nas_secret
FROM sites s
LEFT JOIN nas_clients nc ON s.id = nc.site_id
WHERE s.is_active = TRUE;

SELECT 'Multi-site management tables created successfully!' as status;
