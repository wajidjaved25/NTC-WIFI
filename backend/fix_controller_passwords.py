"""
Fix Omada Controller Password Encryption
This script re-encrypts controller passwords with the current encryption key
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.omada_config import OmadaConfig
from app.utils.helpers import encrypt_password, decrypt_password
from sqlalchemy import text
import getpass

def fix_passwords():
    """Re-encrypt controller passwords"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("OMADA CONTROLLER PASSWORD FIX")
        print("="*80)
        print("\nThis will re-encrypt your Omada controller passwords.")
        print("You'll need to enter the actual password for each controller.\n")
        
        # Get all controllers
        controllers = db.query(OmadaConfig).all()
        
        if not controllers:
            print("No controllers found.")
            return
        
        print(f"Found {len(controllers)} controller(s):\n")
        
        for controller in controllers:
            print("-" * 80)
            print(f"Controller: {controller.config_name}")
            print(f"URL: {controller.controller_url}")
            print(f"Username: {controller.username}")
            
            # Try to decrypt existing password
            try:
                existing_password = decrypt_password(controller.password_encrypted)
                print(f"✓ Current password decrypts successfully")
                print(f"  Password length: {len(existing_password)} characters")
                
                # Ask if they want to keep it or change it
                choice = input("\nKeep this password? (y/n): ").lower().strip()
                
                if choice == 'y':
                    # Re-encrypt with current key (fixes key mismatch issues)
                    new_encrypted = encrypt_password(existing_password)
                    controller.password_encrypted = new_encrypted
                    print("✓ Password re-encrypted with current key")
                else:
                    # Get new password
                    new_password = getpass.getpass("Enter new password: ")
                    confirm_password = getpass.getpass("Confirm password: ")
                    
                    if new_password != confirm_password:
                        print("✗ Passwords don't match. Skipping this controller.")
                        continue
                    
                    controller.password_encrypted = encrypt_password(new_password)
                    print("✓ New password encrypted and saved")
                
            except Exception as e:
                print(f"✗ Failed to decrypt existing password: {str(e)}")
                print("  You need to enter the password manually.")
                
                new_password = getpass.getpass("Enter password: ")
                confirm_password = getpass.getpass("Confirm password: ")
                
                if new_password != confirm_password:
                    print("✗ Passwords don't match. Skipping this controller.")
                    continue
                
                controller.password_encrypted = encrypt_password(new_password)
                print("✓ Password encrypted and saved")
            
            print()
        
        # Commit all changes
        db.commit()
        
        print("=" * 80)
        print("✓✓✓ PASSWORD FIX COMPLETED ✓✓✓")
        print("=" * 80)
        print("\nAll controller passwords have been re-encrypted.")
        print("You can now test connections in the admin panel.\n")
        
        # Test decryption
        print("Verifying all passwords decrypt correctly...")
        controllers = db.query(OmadaConfig).all()
        
        all_good = True
        for controller in controllers:
            try:
                pwd = decrypt_password(controller.password_encrypted)
                print(f"✓ {controller.config_name}: Decrypts successfully ({len(pwd)} chars)")
            except Exception as e:
                print(f"✗ {controller.config_name}: Failed to decrypt - {str(e)}")
                all_good = False
        
        if all_good:
            print("\n✓ All passwords are working correctly!\n")
        else:
            print("\n✗ Some passwords still have issues. Please re-save them via admin panel.\n")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_passwords()
