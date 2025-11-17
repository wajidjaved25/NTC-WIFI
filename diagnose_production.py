#!/usr/bin/env python3
"""
Production Diagnostics Script
Run this on your production server to identify issues
"""

import sys
import os

# Add the backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import SessionLocal
from sqlalchemy import text


def check_radius_server():
    """Check if RADIUS server is running and accessible"""
    print("\n" + "="*60)
    print("CHECKING RADIUS SERVER")
    print("="*60)
    
    import subprocess
    try:
        # Check if FreeRADIUS is running
        result = subprocess.run(
            ['systemctl', 'is-active', 'freeradius'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ FreeRADIUS service is RUNNING")
        else:
            print("✗ FreeRADIUS service is NOT running")
            print("  Fix: sudo systemctl start freeradius")
            return False
    except Exception as e:
        print(f"✗ Cannot check FreeRADIUS status: {e}")
        return False
    
    # Test RADIUS authentication
    try:
        print("\nTesting RADIUS authentication...")
        result = subprocess.run(
            ['echo', 'User-Name=test,User-Password=test', '|', 
             'radclient', '-x', '127.0.0.1:1812', 'auth', 'testing123'],
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "Access-Accept" in result.stdout or "Access-Reject" in result.stdout:
            print("✓ RADIUS server is responding")
            return True
        else:
            print("✗ RADIUS server not responding properly")
            print(f"  Output: {result.stdout}")
            return False
    except Exception as e:
        print(f"✗ RADIUS test failed: {e}")
        return False


def check_radius_database():
    """Check RADIUS database tables"""
    print("\n" + "="*60)
    print("CHECKING RADIUS DATABASE")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Check radcheck table
        result = db.execute(text("SELECT COUNT(*) FROM radcheck")).scalar()
        print(f"✓ radcheck table: {result} users")
        
        # Check radreply table
        result = db.execute(text("SELECT COUNT(*) FROM radreply")).scalar()
        print(f"✓ radreply table: {result} entries")
        
        # Check radacct table
        result = db.execute(text("SELECT COUNT(*) FROM radacct")).scalar()
        print(f"✓ radacct table: {result} sessions")
        
        # Check active sessions
        result = db.execute(text("SELECT COUNT(*) FROM radacct WHERE acctstoptime IS NULL")).scalar()
        print(f"✓ Active RADIUS sessions: {result}")
        
        return True
    except Exception as e:
        print(f"✗ Database check failed: {e}")
        return False
    finally:
        db.close()


def check_omada_config():
    """Check Omada configuration"""
    print("\n" + "="*60)
    print("CHECKING OMADA CONFIGURATION")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT controller_url, username, controller_id, site_name, is_active FROM omada_configs WHERE is_active = true")
        ).fetchone()
        
        if result:
            print(f"✓ Omada Config Found:")
            print(f"  Controller URL: {result[0]}")
            print(f"  Username: {result[1]}")
            print(f"  Controller ID: {result[2]}")
            print(f"  Site: {result[3] or 'Default'}")
            print(f"  Active: {result[4]}")
            
            # Test connection
            from app.services.omada_service import OmadaService
            from app.models.omada_config import OmadaConfig
            
            config = db.query(OmadaConfig).filter(OmadaConfig.is_active == True).first()
            if config:
                omada = OmadaService(
                    controller_url=config.controller_url,
                    username=config.username,
                    encrypted_password=config.password,
                    controller_id=config.controller_id,
                    site_id=config.site_name or "Default"
                )
                
                print("\nTesting Omada connection...")
                test_result = omada.test_connection()
                
                if test_result.get('success'):
                    print("✓ Omada connection successful!")
                    return True
                else:
                    print(f"✗ Omada connection failed: {test_result.get('message')}")
                    return False
            else:
                print("✗ No active Omada config found")
                return False
        else:
            print("✗ No Omada configuration found in database")
            return False
    except Exception as e:
        print(f"✗ Error checking Omada: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def check_recent_sessions():
    """Check recent WiFi sessions"""
    print("\n" + "="*60)
    print("CHECKING RECENT SESSIONS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT s.id, u.mobile, s.mac_address, s.session_status, s.start_time
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                ORDER BY s.start_time DESC
                LIMIT 5
            """)
        ).fetchall()
        
        if result:
            print(f"Last 5 sessions:")
            for row in result:
                print(f"  ID: {row[0]}, Mobile: {row[1]}, MAC: {row[2]}, Status: {row[3]}, Time: {row[4]}")
        else:
            print("No sessions found")
        
        # Count by status
        result = db.execute(
            text("SELECT session_status, COUNT(*) FROM sessions GROUP BY session_status")
        ).fetchall()
        
        print(f"\nSession counts by status:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")
        
        return True
    except Exception as e:
        print(f"✗ Error checking sessions: {e}")
        return False
    finally:
        db.close()


def check_test_user():
    """Check if test user exists and can authenticate"""
    print("\n" + "="*60)
    print("CHECKING TEST USER (03323055053)")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Check in app database
        result = db.execute(
            text("SELECT mobile, name, id_type, cnic FROM users WHERE mobile = '03323055053'")
        ).fetchone()
        
        if result:
            print(f"✓ User found in app database:")
            print(f"  Mobile: {result[0]}")
            print(f"  Name: {result[1]}")
            print(f"  ID Type: {result[2]}")
            print(f"  CNIC: {result[3]}")
        else:
            print("✗ User NOT found in app database")
        
        # Check in RADIUS
        result = db.execute(
            text("SELECT username, value FROM radcheck WHERE username = '03323055053' AND attribute = 'Cleartext-Password'")
        ).fetchone()
        
        if result:
            print(f"✓ User found in RADIUS database:")
            print(f"  Username: {result[0]}")
            print(f"  Password: {result[1]}")
            
            # Test RADIUS authentication
            from app.services.radius_auth_client import RadiusAuthClient
            
            print("\nTesting RADIUS authentication for this user...")
            radius_client = RadiusAuthClient(
                radius_server="127.0.0.1",
                radius_secret="testing123"
            )
            
            auth_result = radius_client.authenticate(
                username="03323055053",
                password=result[1],
                nas_ip="192.168.3.254"
            )
            
            if auth_result.get('success'):
                print(f"✓ RADIUS authentication SUCCESSFUL")
                print(f"  Session timeout: {auth_result.get('session_timeout')} seconds")
                return True
            else:
                print(f"✗ RADIUS authentication FAILED: {auth_result.get('message')}")
                return False
        else:
            print("✗ User NOT found in RADIUS database")
            return False
            
    except Exception as e:
        print(f"✗ Error checking test user: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Run all diagnostics"""
    print("\n" + "="*60)
    print("NTC WIFI PORTAL - PRODUCTION DIAGNOSTICS")
    print("="*60)
    
    results = {
        "RADIUS Server": check_radius_server(),
        "RADIUS Database": check_radius_database(),
        "Omada Configuration": check_omada_config(),
        "Recent Sessions": check_recent_sessions(),
        "Test User Authentication": check_test_user()
    }
    
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    for check, status in results.items():
        icon = "✓" if status else "✗"
        print(f"{icon} {check}: {'PASS' if status else 'FAIL'}")
    
    all_pass = all(results.values())
    
    print("\n" + "="*60)
    if all_pass:
        print("✓ ALL CHECKS PASSED - System ready for production")
    else:
        print("✗ SOME CHECKS FAILED - Review errors above")
    print("="*60 + "\n")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
