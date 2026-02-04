#!/usr/bin/env python3
"""
Migration script to create pakapp_users table
This table stores user information received from PakApp

Run with:
    python migrate_pakapp_users.py
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models.pakapp_user import PakAppUser
from sqlalchemy import text, inspect


def check_table_exists(table_name):
    """Check if table exists in database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate():
    """Create pakapp_users table if it doesn't exist"""
    
    print("=" * 70)
    print("PakApp Users Table Migration")
    print("=" * 70)
    
    # Check if table already exists
    if check_table_exists('pakapp_users'):
        print("✅ Table 'pakapp_users' already exists")
        print("   Checking structure...")
        
        # Get existing columns
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('pakapp_users')]
        
        print(f"   Existing columns: {', '.join(columns)}")
        
        # Check if all required columns exist
        required_columns = ['id', 'name', 'cnic', 'phone', 'email', 'is_active', 
                          'created_at', 'updated_at', 'source', 'ip_address']
        
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"⚠️  Missing columns: {', '.join(missing_columns)}")
            print("   You may need to add these columns manually:")
            for col in missing_columns:
                if col == 'source':
                    print(f"   ALTER TABLE pakapp_users ADD COLUMN {col} VARCHAR(50) DEFAULT 'pakapp';")
                elif col == 'ip_address':
                    print(f"   ALTER TABLE pakapp_users ADD COLUMN {col} VARCHAR(45);")
        else:
            print("✅ All required columns exist")
        
        print("\n✅ Migration completed - No changes needed")
        return
    
    # Create the table
    print("📝 Creating 'pakapp_users' table...")
    
    try:
        # Create only the pakapp_users table
        PakAppUser.__table__.create(engine, checkfirst=True)
        
        print("✅ Table 'pakapp_users' created successfully")
        
        # Verify table creation
        if check_table_exists('pakapp_users'):
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('pakapp_users')]
            print(f"   Columns: {', '.join(columns)}")
            
            # Show indexes
            indexes = inspector.get_indexes('pakapp_users')
            if indexes:
                print(f"   Indexes: {len(indexes)} created")
                for idx in indexes:
                    print(f"      - {idx['name']}: {', '.join(idx['column_names'])}")
        
        print("\n✅ Migration completed successfully!")
        print("\n📊 You can now use the PakApp API:")
        print("   POST /api/pakapp/register - Register new user from PakApp")
        print("   GET  /api/pakapp/users - List all users (admin)")
        print("   GET  /api/pakapp/users/cnic/{cnic} - Get user by CNIC (admin)")
        print("   GET  /api/pakapp/users/phone/{phone} - Get user by phone (admin)")
        print("   GET  /api/pakapp/stats - Get statistics (admin)")
        
    except Exception as e:
        print(f"❌ Error creating table: {str(e)}")
        print("\n⚠️  You may need to create the table manually using SQL:")
        print_manual_sql()
        return


def print_manual_sql():
    """Print manual SQL for table creation"""
    print("\n" + "=" * 70)
    print("Manual SQL (if automatic creation fails):")
    print("=" * 70)
    print("""
CREATE TABLE pakapp_users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cnic VARCHAR(15) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) DEFAULT 'pakapp',
    ip_address VARCHAR(45)
);

-- Create indexes for better query performance
CREATE INDEX idx_pakapp_users_cnic ON pakapp_users(cnic);
CREATE INDEX idx_pakapp_users_phone ON pakapp_users(phone);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_pakapp_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_pakapp_users_updated_at
    BEFORE UPDATE ON pakapp_users
    FOR EACH ROW
    EXECUTE FUNCTION update_pakapp_users_updated_at();
""")


def rollback():
    """Drop pakapp_users table"""
    print("=" * 70)
    print("Rolling back pakapp_users table")
    print("=" * 70)
    
    if not check_table_exists('pakapp_users'):
        print("⚠️  Table 'pakapp_users' does not exist. Nothing to rollback.")
        return
    
    confirm = input("Are you sure you want to DROP the pakapp_users table? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Rollback cancelled")
        return
    
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS pakapp_users CASCADE"))
            conn.commit()
        
        print("✅ Table 'pakapp_users' dropped successfully")
        
    except Exception as e:
        print(f"❌ Error dropping table: {str(e)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate PakApp Users table')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration (drop table)')
    
    args = parser.parse_args()
    
    try:
        if args.rollback:
            rollback()
        else:
            migrate()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
