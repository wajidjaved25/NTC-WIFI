"""
Migration script to add permission columns to admins table
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, SessionLocal
from sqlalchemy import text

def migrate():
    """Add permission columns to admins table"""
    db = SessionLocal()
    
    try:
        print("Starting migration...")
        
        # Add permission columns if they don't exist
        columns_to_add = [
            ("can_manage_portal", "BOOLEAN DEFAULT FALSE"),
            ("can_manage_sessions", "BOOLEAN DEFAULT FALSE"),
            ("can_view_records", "BOOLEAN DEFAULT TRUE"),
            ("can_view_ipdr", "BOOLEAN DEFAULT TRUE"),
            ("can_manage_radius", "BOOLEAN DEFAULT FALSE"),
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                db.execute(text(f"ALTER TABLE admins ADD COLUMN {column_name} {column_type}"))
                print(f"✓ Added column: {column_name}")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"  Column {column_name} already exists, skipping")
                else:
                    raise
        
        # Update existing roles with appropriate permissions
        print("\nUpdating permissions for existing admins...")
        
        # Superadmin gets all permissions
        db.execute(text("""
            UPDATE admins 
            SET can_manage_portal = TRUE,
                can_manage_sessions = TRUE,
                can_view_records = TRUE,
                can_view_ipdr = TRUE,
                can_manage_radius = TRUE
            WHERE role = 'superadmin'
        """))
        print("✓ Updated superadmin permissions")
        
        # Admin gets most permissions
        db.execute(text("""
            UPDATE admins 
            SET can_manage_portal = TRUE,
                can_manage_sessions = TRUE,
                can_view_records = TRUE,
                can_view_ipdr = TRUE,
                can_manage_radius = TRUE
            WHERE role = 'admin'
        """))
        print("✓ Updated admin permissions")
        
        # reports_user gets view permissions only
        db.execute(text("""
            UPDATE admins 
            SET can_manage_portal = FALSE,
                can_manage_sessions = FALSE,
                can_view_records = TRUE,
                can_view_ipdr = TRUE,
                can_manage_radius = FALSE
            WHERE role = 'reports_user'
        """))
        print("✓ Updated reports_user permissions")
        
        # ads_user gets limited permissions
        db.execute(text("""
            UPDATE admins 
            SET can_manage_portal = FALSE,
                can_manage_sessions = FALSE,
                can_view_records = FALSE,
                can_view_ipdr = FALSE,
                can_manage_radius = FALSE
            WHERE role = 'ads_user'
        """))
        print("✓ Updated ads_user permissions")
        
        db.commit()
        
        # Drop and recreate the check constraint to include ipdr_viewer
        print("\nUpdating role constraint...")
        try:
            db.execute(text("ALTER TABLE admins DROP CONSTRAINT check_admin_role"))
            print("✓ Dropped old constraint")
        except Exception as e:
            print(f"  Could not drop constraint (may not exist): {e}")
        
        try:
            db.execute(text("""
                ALTER TABLE admins ADD CONSTRAINT check_admin_role 
                CHECK (role IN ('superadmin', 'admin', 'reports_user', 'ads_user', 'ipdr_viewer'))
            """))
            print("✓ Added new constraint with ipdr_viewer role")
        except Exception as e:
            print(f"  Could not add constraint: {e}")
        
        db.commit()
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
