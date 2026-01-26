"""
Migration script to add multi-controller support fields to omada_config table
Run this script to update existing database schema
"""
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from sqlalchemy import text

def migrate():
    """Add multi-controller support columns to omada_config table"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("MULTI-CONTROLLER MIGRATION")
        print("="*80)
        print("\nThis will add the following fields to omada_config table:")
        print("  - priority (default: 1 for active, 2 for others)")
        print("  - is_healthy (default: TRUE)")
        print("  - last_health_check (default: NULL)")
        print("  - failure_count (default: 0)")
        print("\nExisting controller data will be preserved.\n")
        
        # Check if columns already exist
        print("[Step 1] Checking existing columns...")
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'omada_config' 
            AND column_name IN ('priority', 'is_healthy', 'last_health_check', 'failure_count')
        """))
        existing_columns = [row[0] for row in result]
        
        if existing_columns:
            print(f"  Found existing columns: {', '.join(existing_columns)}")
            print("  Skipping already migrated columns...\n")
        else:
            print("  No migration columns found. Proceeding with migration...\n")
        
        # Add columns if they don't exist
        migrations = [
            ("priority", "ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 1 NOT NULL"),
            ("is_healthy", "ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS is_healthy BOOLEAN DEFAULT TRUE"),
            ("last_health_check", "ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS last_health_check TIMESTAMP WITH TIME ZONE"),
            ("failure_count", "ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS failure_count INTEGER DEFAULT 0"),
        ]
        
        print("[Step 2] Adding new columns...")
        for field_name, sql in migrations:
            if field_name not in existing_columns:
                print(f"  Adding {field_name}...")
                db.execute(text(sql))
            else:
                print(f"  Skipping {field_name} (already exists)")
        
        db.commit()
        print("  ✓ Column creation complete\n")
        
        # Update existing records - set priority 1 for active config, 2 for others
        print("[Step 3] Updating existing controller priorities...")
        
        # Check if there are any existing controllers
        result = db.execute(text("SELECT COUNT(*) FROM omada_config"))
        count = result.scalar()
        
        if count > 0:
            print(f"  Found {count} existing controller(s)")
            
            # Set priority based on is_active status
            db.execute(text("""
                UPDATE omada_config 
                SET priority = CASE 
                    WHEN is_active = TRUE THEN 1 
                    ELSE 2 
                END
                WHERE priority IS NULL OR priority = 0 OR priority = 1
            """))
            
            # Ensure is_healthy is set to TRUE for all existing controllers
            db.execute(text("""
                UPDATE omada_config 
                SET is_healthy = TRUE,
                    failure_count = 0
                WHERE is_healthy IS NULL
            """))
            
            db.commit()
            print("  ✓ Priority assignment complete\n")
        else:
            print("  No existing controllers found\n")
        
        # Show current configs
        print("[Step 4] Current controller configuration:")
        print("-" * 80)
        result = db.execute(text("""
            SELECT 
                id, 
                config_name, 
                priority, 
                is_healthy, 
                failure_count,
                is_active,
                controller_url
            FROM omada_config 
            ORDER BY priority, id
        """))
        configs = result.fetchall()
        
        if configs:
            print(f"{'ID':<5} {'Name':<25} {'Priority':<10} {'Healthy':<10} {'Failures':<10} {'Active':<10}")
            print("-" * 80)
            for config in configs:
                config_id, name, priority, healthy, failures, active, url = config
                priority_label = 'Primary' if priority == 1 else f'Backup {priority-1}'
                print(f"{config_id:<5} {name:<25} {priority:<10} {str(healthy):<10} {failures:<10} {str(active):<10}")
            
            print("\n" + "="*80)
            print("✓✓✓ MIGRATION COMPLETED SUCCESSFULLY ✓✓✓")
            print("="*80)
            print("\nYour existing controller data has been preserved.")
            print("The active controller is set as Priority 1 (Primary).")
            print("Other controllers are set as Priority 2 (Backup 1).")
            print("\nYou can now:")
            print("  1. Add additional backup controllers via the admin panel")
            print("  2. Adjust priorities as needed (1=Primary, 2=Backup1, 3=Backup2, etc.)")
            print("  3. The system will automatically failover to backup controllers")
            print("\n")
        else:
            print("No controllers configured yet.")
            print("\n" + "="*80)
            print("✓ MIGRATION COMPLETED")
            print("="*80)
            print("\nYou can now add controllers via the admin panel.\n")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()
    
    return True

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
