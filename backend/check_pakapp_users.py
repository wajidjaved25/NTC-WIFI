#!/usr/bin/env python3
"""
Quick script to check PakApp user registrations
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models.pakapp_user import PakAppUser
from sqlalchemy import func, desc
from datetime import datetime, timedelta


def check_pakapp_users():
    """Check PakApp user registrations"""
    db = SessionLocal()
    
    try:
        print("\n" + "=" * 70)
        print("  PakApp User Registration Check")
        print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 70)
        
        # Total count
        total = db.query(PakAppUser).count()
        print(f"\n📊 Total Users: {total}")
        
        # Count by source
        pakapp_count = db.query(PakAppUser).filter(PakAppUser.source == 'pakapp').count()
        print(f"   From PakApp: {pakapp_count}")
        
        # Active users
        active = db.query(PakAppUser).filter(PakAppUser.is_active == True).count()
        print(f"   Active Users: {active}")
        
        # Recent registrations (last 5 minutes)
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        recent = db.query(PakAppUser).filter(PakAppUser.created_at > five_min_ago).count()
        print(f"\n🕐 Last 5 Minutes: {recent} registrations")
        
        # Recent registrations (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        last_hour = db.query(PakAppUser).filter(PakAppUser.created_at > one_hour_ago).count()
        print(f"🕐 Last Hour: {last_hour} registrations")
        
        # Recent registrations (today)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today = db.query(PakAppUser).filter(PakAppUser.created_at > today_start).count()
        print(f"📅 Today: {today} registrations")
        
        # Latest 5 entries
        print("\n" + "=" * 70)
        print("  Latest 5 Registrations")
        print("=" * 70)
        
        latest = db.query(PakAppUser).order_by(desc(PakAppUser.created_at)).limit(5).all()
        
        if latest:
            print(f"\n{'ID':<6} {'Name':<25} {'CNIC':<15} {'Phone':<15} {'Created':<20}")
            print("-" * 70)
            
            for user in latest:
                created = user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "N/A"
                print(f"{user.id:<6} {user.name[:24]:<25} {user.cnic:<15} {user.phone:<15} {created:<20}")
        else:
            print("\n⚠️  No users found in database")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()


if __name__ == "__main__":
    check_pakapp_users()
