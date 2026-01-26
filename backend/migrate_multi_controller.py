"""
Migration script to add multi-controller support fields to omada_config table
Run this script to update existing database schema
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'ntc_wifi')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

def migrate():
    """Add multi-controller support columns to omada_config table"""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        print("Adding multi-controller support columns...")
        
        # Add columns if they don't exist
        migrations = [
            ("priority", "ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 1 NOT NULL"),
            ("is_healthy", "ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS is_healthy BOOLEAN DEFAULT TRUE"),
            ("last_health_check", "ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS last_health_check TIMESTAMP WITH TIME ZONE"),
            ("failure_count", "ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS failure_count INTEGER DEFAULT 0"),
        ]
        
        for field_name, sql in migrations:
            print(f"  Adding {field_name}...")
            cursor.execute(sql)
        
        # Update existing records - set priority 1 for active config, 2 for others
        cursor.execute("""
            UPDATE omada_config 
            SET priority = CASE 
                WHEN is_active = TRUE THEN 1 
                ELSE 2 
            END
            WHERE priority IS NULL OR priority = 0
        """)
        
        conn.commit()
        print("✓ Migration completed successfully!")
        
        # Show current configs
        cursor.execute("SELECT id, config_name, priority, is_healthy, is_active FROM omada_config ORDER BY priority")
        configs = cursor.fetchall()
        
        if configs:
            print("\nCurrent controller configurations:")
            print("-" * 80)
            print(f"{'ID':<5} {'Name':<20} {'Priority':<10} {'Healthy':<10} {'Active':<10}")
            print("-" * 80)
            for config in configs:
                print(f"{config[0]:<5} {config[1]:<20} {config[2]:<10} {config[3]!s:<10} {config[4]!s:<10}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()
