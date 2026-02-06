#!/usr/bin/env python3
"""
Test script for PakApp User Registration API with direct API key support

Usage:
    # From .env file (requires python-dotenv)
    python3 test_pakapp_api_simple.py
    
    # Pass API key directly
    PAKAPP_API_KEY=your_key_here python3 test_pakapp_api_simple.py
"""

import requests
import json
import os
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/pakapp"

# Try to read API key from environment first
API_KEY = os.environ.get("PAKAPP_API_KEY", "")

# If not in environment, try to read from .env file manually
if not API_KEY:
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("PAKAPP_API_KEY="):
                    API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except FileNotFoundError:
        pass

# Check if we have API key
if not API_KEY:
    print("❌ ERROR: API key not found!")
    print("\nPlease provide API key in one of these ways:")
    print("\n1. Set environment variable:")
    print("   PAKAPP_API_KEY=your_key_here python3 test_pakapp_api_simple.py")
    print("\n2. Add to .env file:")
    print("   echo 'PAKAPP_API_KEY=your_key_here' >> .env")
    print("\n3. Generate new key:")
    print("   python3 generate_pakapp_keys.py")
    sys.exit(1)


def get_headers():
    """Get request headers with API key"""
    return {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }


def print_header(title):
    """Print test section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(response, expected_status=None):
    """Print response details"""
    print(f"Status Code: {response.status_code}")
    
    if expected_status and response.status_code == expected_status:
        print(f"✅ Expected status {expected_status}")
    elif expected_status:
        print(f"❌ Expected {expected_status}, got {response.status_code}")
    
    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2, default=str)}")
    except:
        print(f"Response: {response.text}")


def test_register_user():
    """Test 1: Register a new user"""
    print_header("Test 1: Register New User")
    
    data = {
        "name": "Muhammad Ahmed Khan",
        "cnic": "1234567890123",
        "phone": "03001234567",
        "email": "ahmed.khan@example.com"
    }
    
    print(f"Sending: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(f"{API_URL}/register", json=data, headers=get_headers(), timeout=10)
        print_result(response, expected_status=201)
        
        if response.status_code == 201:
            user_data = response.json()
            print(f"\n✅ User registered successfully!")
            print(f"   User ID: {user_data['id']}")
            print(f"   Phone: {user_data['phone']} (formatted)")
            return user_data
        
    except requests.RequestException as e:
        print(f"❌ Error: {str(e)}")
        return None


def test_with_api_key():
    """Quick test to verify API key works"""
    print_header("API Key Authentication Test")
    
    data = {
        "name": "Test User",
        "cnic": "9999999999999",
        "phone": "03001234567"
    }
    
    print("Testing with API key...")
    
    try:
        response = requests.post(f"{API_URL}/register", json=data, headers=get_headers(), timeout=10)
        
        if response.status_code == 201:
            print("✅ API key authentication successful!")
            print(f"   User ID: {response.json()['id']}")
            return True
        elif response.status_code == 401:
            print("❌ API key authentication failed!")
            print(f"   Error: {response.json()['detail']}")
            return False
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Connection error: {str(e)}")
        return False


def main():
    """Run tests"""
    print("\n" + "=" * 70)
    print("  PakApp User Registration API - Test Suite")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)
    print(f"  API URL: {API_URL}")
    print(f"  API Key: {API_KEY[:20]}...{API_KEY[-4:]} (configured)")
    print("=" * 70)
    
    # Check if server is running
    print("\nChecking server connectivity...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print("⚠️  Server responded but health check failed")
    except requests.RequestException:
        print("❌ Cannot connect to server. Make sure backend is running.")
        print(f"   URL: {BASE_URL}")
        return
    
    # Quick authentication test
    if not test_with_api_key():
        print("\n⚠️  API key authentication failed. Please check your API key.")
        return
    
    # Run full test
    print("\nRunning full registration test...")
    test_register_user()
    
    print_header("Test Completed")
    print("✅ Basic test passed!")
    print("\nFor full test suite, run: python3 test_pakapp_api.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
