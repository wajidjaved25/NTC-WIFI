#!/usr/bin/env python3
"""
PakApp Security Key Generator

This script generates secure keys for PakApp API authentication.
Outputs are ready to copy into your .env file.
"""

import secrets
import sys


def generate_api_key(length=32):
    """Generate a secure API key"""
    return secrets.token_urlsafe(length)


def generate_signature_secret(length=32):
    """Generate a secure signature secret"""
    return secrets.token_hex(length)


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    print_header("PakApp Security Key Generator")
    
    print("\nGenerating secure keys for PakApp API authentication...")
    print("Copy these values into your .env file\n")
    
    # Generate API Key
    api_key = generate_api_key()
    print("1️⃣  API KEY (for X-API-Key header)")
    print("-" * 70)
    print(f"PAKAPP_API_KEY={api_key}")
    print(f"\n   Length: {len(api_key)} characters")
    print("   Usage: PakApp sends this in X-API-Key header")
    
    # Generate Signature Secret
    signature_secret = generate_signature_secret()
    print("\n2️⃣  SIGNATURE SECRET (for HMAC signing)")
    print("-" * 70)
    print(f"PAKAPP_SIGNATURE_SECRET={signature_secret}")
    print(f"\n   Length: {len(signature_secret)} characters")
    print("   Usage: Shared secret for signing requests (advanced)")
    
    # Configuration examples
    print_header("Configuration Examples")
    
    print("\n📝 BASIC SECURITY (API Key Only) - Recommended for most cases")
    print("-" * 70)
    print("""
# Add to .env file:
PAKAPP_ENABLE_API_KEY=true
PAKAPP_API_KEY={api_key}
PAKAPP_ALLOWED_IPS=
PAKAPP_ENABLE_SIGNATURE=false
PAKAPP_SIGNATURE_SECRET=
""".format(api_key=api_key))
    
    print("\n📝 STANDARD SECURITY (API Key + IP Whitelist) - Production")
    print("-" * 70)
    print("""
# Add to .env file:
PAKAPP_ENABLE_API_KEY=true
PAKAPP_API_KEY={api_key}
PAKAPP_ALLOWED_IPS=1.2.3.4,5.6.7.8  # Replace with PakApp's server IPs
PAKAPP_ENABLE_SIGNATURE=false
PAKAPP_SIGNATURE_SECRET=
""".format(api_key=api_key))
    
    print("\n📝 MAXIMUM SECURITY (All Layers) - High Security")
    print("-" * 70)
    print("""
# Add to .env file:
PAKAPP_ENABLE_API_KEY=true
PAKAPP_API_KEY={api_key}
PAKAPP_ALLOWED_IPS=1.2.3.4,5.6.7.8  # Replace with PakApp's server IPs
PAKAPP_ENABLE_SIGNATURE=true
PAKAPP_SIGNATURE_SECRET={signature_secret}
""".format(api_key=api_key, signature_secret=signature_secret))
    
    print_header("Next Steps")
    
    print("""
1. Copy the appropriate configuration to your .env file
2. Share the API key (and secret if using signatures) with PakApp team
3. Restart your backend service:
   
   Development:
   $ venv\\Scripts\\activate
   $ python -m uvicorn app.main:app --reload
   
   Production:
   $ sudo systemctl restart ntc-wifi-backend

4. Test with PakApp team:
   $ python test_pakapp_security.py

5. Share PAKAPP_SECURITY_GUIDE.md with PakApp developers

📚 Full documentation: PAKAPP_SECURITY_GUIDE.md
""")
    
    print_header("Security Reminders")
    print("""
⚠️  IMPORTANT:
- Never commit these keys to Git
- Use different keys for dev/staging/production
- Rotate keys every 3-6 months
- Always use HTTPS in production
- Share keys securely (encrypted email, password manager, etc.)
""")
    
    print("=" * 70)


def generate_test_curl():
    """Generate test curl command"""
    api_key = generate_api_key()
    
    print_header("Test cURL Command")
    print(f"""
# Test API authentication:
curl -X POST "http://localhost:8000/api/pakapp/register" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: {api_key}" \\
  -d '{{
    "name": "Test User",
    "cnic": "1234567890123",
    "phone": "03001234567",
    "email": "test@example.com"
  }}'

# Expected response (if successful):
# Status: 201 Created
# Body: User data JSON

# Expected response (if unauthorized):
# Status: 401 Unauthorized
# Body: {{"detail": "Missing X-API-Key header"}}
    """)


if __name__ == "__main__":
    try:
        # Check for command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == "--curl":
                generate_test_curl()
                sys.exit(0)
            elif sys.argv[1] == "--help":
                print("""
PakApp Security Key Generator

Usage:
    python generate_pakapp_keys.py          Generate API keys
    python generate_pakapp_keys.py --curl   Generate test curl command
    python generate_pakapp_keys.py --help   Show this help
""")
                sys.exit(0)
        
        main()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Key generation cancelled")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
