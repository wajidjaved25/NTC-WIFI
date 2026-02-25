#!/usr/bin/env python3
"""
Migration: Add SMS Settings Table
Creates table for customizable SMS templates
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, SessionLocal
from app.models.sms_settings import SMSSettings
from sqlalchemy import text, inspect


def check_table_exists(table_name: str) -> bool:
    """Check if table already exists"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate():
    """Run migration"""
    print("=" * 70)
    print("  SMS Settings Migration")
    print("=" * 70)
    
    # Check if table exists
    if check_table_exists('sms_settings'):
        print("\n✅ sms_settings table already exists")
        print("   Skipping creation...")
    else:
        print("\n📝 Creating sms_settings table...")
        
        # Create table
        SMSSettings.__table__.create(engine)
        
        print("   ✅ Table created successfully")
    
    # Insert default settings
    print("\n📝 Checking for default settings...")
    
    db = SessionLocal()
    try:
        existing = db.query(SMSSettings).first()
        
        if existing:
            print(f"   ✅ Settings already exist (ID: {existing.id})")
            print(f"   Current template: {existing.otp_template[:50]}...")
        else:
            print("   📝 Creating default settings...")
            
            default_settings = SMSSettings(
                otp_template="Your NTC WiFi OTP: {otp}\nValid for {validity} minutes. Do not share.\n\n@{portal_url} #{otp}",
                sender_id="NTC",
                otp_validity_minutes=5,
                otp_length=6,
                max_otp_per_number_per_hour=3,
                max_otp_per_number_per_day=10,
                enable_primary_sms=True,
                enable_secondary_sms=True
            )
            
            db.add(default_settings)
            db.commit()
            db.refresh(default_settings)
            
            print(f"   ✅ Default settings created (ID: {default_settings.id})")
    
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
    
    print("\n" + "=" * 70)
    print("  Migration Complete!")
    print("=" * 70)
    print("\n✅ SMS Settings table ready")
    print("\nNext steps:")
    print("1. Restart backend: sudo systemctl restart ntc-wifi-backend")
    print("2. Access SMS Settings in admin panel (Superadmin only)")
    print("3. Customize OTP message template")
    print("\nAvailable placeholders:")
    print("  - {otp}: The OTP code")
    print("  - {validity}: Validity period in minutes")
    print("  - {portal_url}: Portal URL/domain")
    print("  - {sender}: Sender ID")
    print()


if __name__ == "__main__":
    try:
        migrate()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted")
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
