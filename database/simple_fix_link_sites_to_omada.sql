-- SIMPLE FIX: Link sites to existing omada_config
-- No new tables needed! Just add a foreign key.

-- Add foreign key to reference omada_config
ALTER TABLE sites ADD COLUMN IF NOT EXISTS omada_config_id INTEGER;
ALTER TABLE sites ADD CONSTRAINT fk_sites_omada_config 
    FOREIGN KEY (omada_config_id) REFERENCES omada_config(id) ON DELETE SET NULL;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_sites_omada_config ON sites(omada_config_id);

-- View to show sites with their omada config
CREATE OR REPLACE VIEW v_sites_with_omada AS
SELECT 
    s.id,
    s.site_name,
    s.site_code,
    s.location,
    s.omada_site_id,
    s.radius_nas_ip,
    s.radius_coa_port,
    s.is_active,
    -- If linked to omada_config, use that; otherwise use site's own fields
    COALESCE(oc.controller_url, 'http://' || s.omada_controller_ip || ':' || s.omada_controller_port) as controller_url,
    COALESCE(oc.username, s.omada_username) as controller_username,
    COALESCE(oc.site_id, s.omada_site_id) as controller_site_id,
    oc.config_name,
    oc.id as omada_config_id
FROM sites s
LEFT JOIN omada_config oc ON s.omada_config_id = oc.id
WHERE s.is_active = TRUE;

SELECT 'SIMPLE FIX: Sites can now optionally reference omada_config!' as status;
