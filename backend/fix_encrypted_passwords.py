#!/usr/bin/env python3
"""
Script to re-encrypt Omada passwords when ENCRYPTION_KEY changes
Usage: python fix_encrypted_passwords.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cryptography.fernet import Fernet
from app.database import SessionLocal
from app.models.omada_config import OmadaConfig

def fix_passwords():
    """Re-encrypt all passwords with current ENCRYPTION_KEY"""
    
    print("=" * 60)
    print("Omada Password Re-encryption Tool")
    print("=" * 60)
    print()
    
    # Get current key from .env
    from app.config import settings
    print(f"Current ENCRYPTION_KEY: {settings.ENCRYPTION_KEY[:20]}...")
    print()
    
    # Ask for old key
    print("Enter the OLD encryption key (or press Enter to skip decryption):")
    old_key_input = input("> ").strip()
    
    db = SessionLocal()
    try:
        configs = db.query(OmadaConfig).all()
        print(f"\nFound {len(configs)} Omada configuration(s)")
        
        for config in configs:
            print(f"\n--- Config ID: {config.id} - {config.config_name} ---")
            
            if old_key_input:
                # Try to decrypt with old key
                try:
                    old_cipher = Fernet(old_key_input.encode())
                    decrypted = old_cipher.decrypt(config.password_encrypted.encode()).decode()
                    print(f"✓ Decrypted with old key")
                    
                    # Re-encrypt with new key
                    new_cipher = Fernet(settings.ENCRYPTION_KEY.encode())
                    new_encrypted = new_cipher.encrypt(decrypted.encode()).decode()
                    
                    config.password_encrypted = new_encrypted
                    db.commit()
                    print(f"✓ Re-encrypted with new key")
                    
                except Exception as e:
                    print(f"✗ Failed to decrypt/re-encrypt: {e}")
            else:
                # Just prompt for new password
                print("Please enter the password for this controller:")
                new_password = input("> ").strip()
                
                if new_password:
                    from app.utils.helpers import encrypt_password
                    config.password_encrypted = encrypt_password(new_password)
                    db.commit()
                    print(f"✓ Password updated and encrypted")
                else:
                    print("✗ Skipped (no password entered)")
        
        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_passwords()
