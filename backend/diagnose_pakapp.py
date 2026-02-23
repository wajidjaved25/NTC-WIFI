#!/usr/bin/env python3
"""
PakApp Integration Diagnostic Tool
Checks if data is flowing correctly from PakApp to Admin Panel
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models.pakapp_user import PakAppUser
from sqlalchemy import text, func
from datetime import datetime, timedelta
import json


def print_section(title):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_database_connection():
    """Check if database is accessible"""
    print_section("1. Database Connection Check")
    
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).fetchone()
        print("✅ Database connection: OK")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection: FAILED")
        print(f"   Error: {str(e)}")
        return False


def check_table_exists():
    """Check if pakapp_users table exists"""
    print_section("2. Table Existence Check")
    
    try:
        db = SessionLocal()
        
        # Check if table exists
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pakapp_users'
            );
        """)).fetchone()
        
        if result[0]:
            print("✅ pakapp_users table: EXISTS")
            
            # Get table structure
            columns = db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'pakapp_users'
                ORDER BY ordinal_position;
            """)).fetchall()
            
            print("\n   Table Structure:")
            for col in columns:
                print(f"   - {col[0]}: {col[1]}")
            
            db.close()
            return True
        else:
            print("❌ pakapp_users table: DOES NOT EXIST")
            print("\n   ⚠️  Run migration:")
            print("   python migrate_pakapp_users.py")
            db.close()
            return False
            
    except Exception as e:
        print(f"❌ Error checking table: {str(e)}")
        return False


def check_total_records():
    """Check total number of records"""
    print_section("3. Record Count Check")
    
    try:
        db = SessionLocal()
        
        # Total count
        total = db.query(PakAppUser).count()
        print(f"📊 Total records in pakapp_users: {total}")
        
        if total == 0:
            print("\n   ⚠️  No records found!")
            print("   Possible reasons:")
            print("   1. PakApp hasn't sent any requests yet")
            print("   2. PakApp is hitting wrong endpoint")
            print("   3. API key authentication failing")
            print("   4. Data going to different database")
        else:
            print(f"\n   ✅ {total} record(s) found")
        
        db.close()
        return total
        
    except Exception as e:
        print(f"❌ Error counting records: {str(e)}")
        return 0


def check_recent_records():
    """Check for recent records (last 24 hours)"""
    print_section("4. Recent Records Check (Last 24 Hours)")
    
    try:
        db = SessionLocal()
        
        # Records in last 24 hours
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent = db.query(PakAppUser).filter(
            PakAppUser.created_at > yesterday
        ).count()
        
        print(f"📅 Records created in last 24 hours: {recent}")
        
        if recent > 0:
            print("\n   ✅ Recent activity detected!")
            
            # Show latest 3
            latest = db.query(PakAppUser).order_by(
                PakAppUser.created_at.desc()
            ).limit(3).all()
            
            print("\n   Latest 3 registrations:")
            for user in latest:
                age = datetime.utcnow() - user.created_at
                minutes_ago = int(age.total_seconds() / 60)
                print(f"   - {user.name} ({user.phone}) - {minutes_ago} min ago")
        else:
            print("\n   ⚠️  No recent records in last 24 hours")
            print("   PakApp may not be sending data")
        
        db.close()
        return recent
        
    except Exception as e:
        print(f"❌ Error checking recent records: {str(e)}")
        return 0


def check_sample_data():
    """Show sample of actual data"""
    print_section("5. Sample Data")
    
    try:
        db = SessionLocal()
        
        users = db.query(PakAppUser).order_by(
            PakAppUser.created_at.desc()
        ).limit(5).all()
        
        if users:
            print("\n   Latest 5 Users:")
            print(f"   {'ID':<6} {'Name':<20} {'CNIC':<15} {'Phone':<15} {'Created':<20}")
            print("   " + "-" * 80)
            
            for user in users:
                created_str = user.created_at.strftime("%Y-%m-%d %H:%M:%S")
                print(f"   {user.id:<6} {user.name[:19]:<20} {user.cnic:<15} {user.phone:<15} {created_str:<20}")
        else:
            print("\n   ⚠️  No data to display")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error fetching sample data: {str(e)}")


def check_database_config():
    """Check which database is configured"""
    print_section("6. Database Configuration Check")
    
    try:
        from app.config import settings
        
        print(f"📝 Database URL: {settings.DATABASE_URL}")
        
        # Extract database name
        if "postgresql" in settings.DATABASE_URL:
            # Parse database name from URL
            parts = settings.DATABASE_URL.split("/")
            if len(parts) > 3:
                db_name = parts[-1].split("?")[0]
                print(f"📁 Database name: {db_name}")
        
    except Exception as e:
        print(f"⚠️  Could not determine database config: {str(e)}")


def check_api_endpoints():
    """List available PakApp endpoints"""
    print_section("7. API Endpoints Check")
    
    print("\n   PakApp should be hitting:")
    print("   📍 POST http://your-server:8000/api/pakapp/register")
    print("\n   Admin panel reads from:")
    print("   📍 GET  http://your-server:8000/api/pakapp/stats")
    print("   📍 GET  http://your-server:8000/api/pakapp/users")
    
    print("\n   ✅ All endpoints use the SAME database")


def test_insert():
    """Test if we can insert data"""
    print_section("8. Write Test")
    
    try:
        db = SessionLocal()
        
        # Try to create a test user
        test_user = PakAppUser(
            name="Test Diagnostic User",
            cnic="9999999999999",
            phone="923000000000",
            email="diagnostic@test.com",
            source="diagnostic",
            is_active=True
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print(f"✅ Test write successful!")
        print(f"   Created user ID: {test_user.id}")
        
        # Clean up - delete test user
        db.delete(test_user)
        db.commit()
        print(f"   ✅ Test user deleted (cleanup)")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Write test failed: {str(e)}")
        return False


def check_by_source():
    """Check records by source"""
    print_section("9. Records by Source")
    
    try:
        db = SessionLocal()
        
        # Group by source
        sources = db.query(
            PakAppUser.source,
            func.count(PakAppUser.id)
        ).group_by(PakAppUser.source).all()
        
        if sources:
            print("\n   Records by source:")
            for source, count in sources:
                print(f"   - {source}: {count}")
        else:
            print("\n   ⚠️  No records found")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error checking sources: {str(e)}")


def provide_recommendations(total_records, recent_records):
    """Provide troubleshooting recommendations"""
    print_section("10. Recommendations")
    
    if total_records == 0:
        print("\n   🔍 NO DATA FOUND - Possible Issues:")
        print("\n   1️⃣  Migration Not Run")
        print("      → Run: python migrate_pakapp_users.py")
        
        print("\n   2️⃣  PakApp Using Wrong URL")
        print("      → Verify PakApp is hitting: http://your-server:8000/api/pakapp/register")
        
        print("\n   3️⃣  API Key Authentication Failing")
        print("      → Check PakApp has correct API key")
        print("      → Check PakApp is sending X-API-Key header")
        
        print("\n   4️⃣  Backend Not Running")
        print("      → Check: systemctl status ntc-wifi-backend")
        
        print("\n   5️⃣  Check Backend Logs")
        print("      → Run: journalctl -u ntc-wifi-backend -f")
        print("      → Look for 201 responses or errors")
        
    elif recent_records == 0:
        print("\n   ⚠️  OLD DATA FOUND - PakApp Not Sending Recently")
        print("\n   1️⃣  Check if PakApp is actually sending requests")
        print("   2️⃣  Check backend logs for recent activity:")
        print("      → journalctl -u ntc-wifi-backend -n 100")
        print("   3️⃣  Verify API key hasn't changed")
        
    else:
        print("\n   ✅ DATA FLOWING CORRECTLY!")
        print(f"   - Total records: {total_records}")
        print(f"   - Recent (24h): {recent_records}")
        print("\n   If admin panel not showing data:")
        print("   1️⃣  Clear browser cache")
        print("   2️⃣  Check browser console for errors")
        print("   3️⃣  Verify admin panel API calls are working")


def main():
    """Run all diagnostic checks"""
    print("\n" + "=" * 70)
    print("  PakApp Integration Diagnostic Tool")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)
    
    # Run checks
    db_ok = check_database_connection()
    if not db_ok:
        print("\n❌ Cannot proceed - database connection failed")
        return
    
    table_ok = check_table_exists()
    if not table_ok:
        print("\n❌ Cannot proceed - table does not exist")
        return
    
    check_database_config()
    total_records = check_total_records()
    recent_records = check_recent_records()
    
    check_by_source()
    check_sample_data()
    check_api_endpoints()
    
    if total_records > 0:
        test_insert()
    
    provide_recommendations(total_records, recent_records)
    
    print("\n" + "=" * 70)
    print("  Diagnostic Complete")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnostic interrupted")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
