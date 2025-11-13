-- Update users table to add ID fields
ALTER TABLE users ADD COLUMN IF NOT EXISTS id_type VARCHAR(20) CHECK (id_type IN ('cnic', 'passport'));
ALTER TABLE users ADD COLUMN IF NOT EXISTS cnic VARCHAR(15); -- Format: XXXXX-XXXXXXX-X or 13 digits
ALTER TABLE users ADD COLUMN IF NOT EXISTS passport VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP;

-- Add indexes for faster lookup
CREATE INDEX IF NOT EXISTS idx_users_cnic ON users(cnic);
CREATE INDEX IF NOT EXISTS idx_users_passport ON users(passport);
CREATE INDEX IF NOT EXISTS idx_users_id_type ON users(id_type);

-- Update portal_design table to ensure terms checkbox text is stored
ALTER TABLE portal_design ADD COLUMN IF NOT EXISTS terms_checkbox_text TEXT DEFAULT 'I accept the terms and conditions';
