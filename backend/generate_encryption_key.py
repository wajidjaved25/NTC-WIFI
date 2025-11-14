#!/usr/bin/env python3
"""
Generate a new Fernet encryption key for .env
"""

from cryptography.fernet import Fernet

print("=" * 60)
print("Fernet Encryption Key Generator")
print("=" * 60)
print()
print("Add this to your .env file as ENCRYPTION_KEY:")
print()
key = Fernet.generate_key().decode()
print(f"ENCRYPTION_KEY={key}")
print()
print("⚠️  WARNING: Changing this key will make existing encrypted")
print("   passwords unreadable. Use fix_encrypted_passwords.py to")
print("   re-encrypt existing passwords.")
print("=" * 60)
