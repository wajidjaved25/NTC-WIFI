#!/usr/bin/env python3
"""
Test script for PakApp User Registration API

This script tests the PakApp registration endpoint with various scenarios.

Usage:
    python test_pakapp_api.py
"""

import requests
import json
from datetime import datetime


# Configuration
BASE_URL = "http://localhost:8000"  # Change to your server URL
API_URL = f"{BASE_URL}/api/pakapp"


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
        response = requests.post(f"{API_URL}/register", json=data, timeout=10)
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


def test_register_duplicate():
    """Test 2: Register duplicate CNIC (should update)"""
    print_header("Test 2: Register Duplicate CNIC (Update Existing)")
    
    data = {
        "name": "Muhammad Ahmed Updated",
        "cnic": "1234567890123",
        "phone": "03119876543",
        "email": "ahmed.updated@example.com"
    }
    
    print(f"Sending: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(f"{API_URL}/register", json=data, timeout=10)
        print_result(response, expected_status=201)
        
        if response.status_code == 201:
            print(f"\n✅ Existing user updated successfully!")
        
    except requests.RequestException as e:
        print(f"❌ Error: {str(e)}")


def test_invalid_cnic():
    """Test 3: Invalid CNIC format"""
    print_header("Test 3: Invalid CNIC Format (Validation Error)")
    
    data = {
        "name": "Invalid User",
        "cnic": "12345",  # Too short
        "phone": "03001234567",
        "email": "invalid@example.com"
    }
    
    print(f"Sending: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(f"{API_URL}/register", json=data, timeout=10)
        print_result(response, expected_status=422)
        
        if response.status_code == 422:
            print(f"\n✅ Validation error caught correctly!")
        
    except requests.RequestException as e:
        print(f"❌ Error: {str(e)}")


def test_invalid_phone():
    """Test 4: Invalid phone format"""
    print_header("Test 4: Invalid Phone Format (Validation Error)")
    
    data = {
        "name": "Invalid Phone User",
        "cnic": "9876543210987",
        "phone": "12345",  # Invalid format
        "email": "phone@example.com"
    }
    
    print(f"Sending: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(f"{API_URL}/register", json=data, timeout=10)
        print_result(response, expected_status=422)
        
        if response.status_code == 422:
            print(f"\n✅ Validation error caught correctly!")
        
    except requests.RequestException as e:
        print(f"❌ Error: {str(e)}")


def test_phone_format_conversion():
    """Test 5: Phone format conversion"""
    print_header("Test 5: Phone Format Conversion")
    
    test_phones = [
        ("03001234567", "923001234567"),  # 03XX -> 923XX
        ("3001234567", "923001234567"),   # 3XX -> 923XX
        ("923001234567", "923001234567"), # Already correct
    ]
    
    for idx, (input_phone, expected_output) in enumerate(test_phones, 1):
        print(f"\n--- Test 5.{idx}: {input_phone} -> {expected_output} ---")
        
        data = {
            "name": f"Phone Test User {idx}",
            "cnic": f"1111{idx:09d}",  # Unique CNIC for each test
            "phone": input_phone,
            "email": f"phone{idx}@example.com"
        }
        
        print(f"Input phone: {input_phone}")
        
        try:
            response = requests.post(f"{API_URL}/register", json=data, timeout=10)
            
            if response.status_code == 201:
                user_data = response.json()
                output_phone = user_data['phone']
                
                if output_phone == expected_output:
                    print(f"✅ Output phone: {output_phone} (Correct)")
                else:
                    print(f"❌ Output phone: {output_phone} (Expected: {expected_output})")
            else:
                print(f"❌ Failed with status {response.status_code}")
                
        except requests.RequestException as e:
            print(f"❌ Error: {str(e)}")


def test_optional_email():
    """Test 6: Registration without email"""
    print_header("Test 6: Registration Without Email (Optional Field)")
    
    data = {
        "name": "No Email User",
        "cnic": "5555555555555",
        "phone": "03009999999"
        # email is optional
    }
    
    print(f"Sending: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(f"{API_URL}/register", json=data, timeout=10)
        print_result(response, expected_status=201)
        
        if response.status_code == 201:
            print(f"\n✅ User registered without email!")
        
    except requests.RequestException as e:
        print(f"❌ Error: {str(e)}")


def test_rate_limiting():
    """Test 7: Rate limiting (10 requests per minute)"""
    print_header("Test 7: Rate Limiting (10 requests/minute)")
    
    print("Sending 12 rapid requests to test rate limit...")
    
    success_count = 0
    rate_limited_count = 0
    
    for i in range(12):
        data = {
            "name": f"Rate Test User {i}",
            "cnic": f"8888{i:09d}",
            "phone": "03001234567"
        }
        
        try:
            response = requests.post(f"{API_URL}/register", json=data, timeout=10)
            
            if response.status_code == 201:
                success_count += 1
                print(f"  Request {i+1}: ✅ Success")
            elif response.status_code == 429:
                rate_limited_count += 1
                print(f"  Request {i+1}: ⏱️  Rate limited")
            else:
                print(f"  Request {i+1}: ❌ Error {response.status_code}")
                
        except requests.RequestException as e:
            print(f"  Request {i+1}: ❌ Network error")
    
    print(f"\nResults:")
    print(f"  Successful: {success_count}")
    print(f"  Rate limited: {rate_limited_count}")
    
    if rate_limited_count > 0:
        print(f"✅ Rate limiting is working!")
    else:
        print(f"⚠️  Rate limiting may not be enabled")


def test_cnic_format_cleaning():
    """Test 8: CNIC format cleaning (dashes and spaces)"""
    print_header("Test 8: CNIC Format Cleaning")
    
    test_cnics = [
        "12345-6789012-3",  # With dashes
        "1234567890123",    # Clean
        "12345 67890 123",  # With spaces
    ]
    
    for idx, cnic in enumerate(test_cnics, 1):
        print(f"\n--- Test 8.{idx}: CNIC = {cnic} ---")
        
        data = {
            "name": f"CNIC Test User {idx}",
            "cnic": cnic,
            "phone": "03001234567",
            "email": f"cnic{idx}@example.com"
        }
        
        print(f"Input CNIC: '{cnic}'")
        
        try:
            response = requests.post(f"{API_URL}/register", json=data, timeout=10)
            
            if response.status_code == 201:
                user_data = response.json()
                output_cnic = user_data['cnic']
                expected = "1234567890123"
                
                if output_cnic == expected:
                    print(f"✅ Output CNIC: {output_cnic} (Cleaned correctly)")
                else:
                    print(f"❌ Output CNIC: {output_cnic} (Expected: {expected})")
            else:
                print(f"❌ Failed with status {response.status_code}")
                
        except requests.RequestException as e:
            print(f"❌ Error: {str(e)}")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  PakApp User Registration API - Test Suite")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)
    print(f"  API URL: {API_URL}")
    print("=" * 70)
    
    # Check if server is running
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
    
    # Run tests
    test_register_user()
    test_register_duplicate()
    test_invalid_cnic()
    test_invalid_phone()
    test_phone_format_conversion()
    test_optional_email()
    test_cnic_format_cleaning()
    test_rate_limiting()
    
    # Summary
    print_header("Test Suite Completed")
    print("✅ All tests finished!")
    print("\nNext steps:")
    print("1. Check the PAKAPP_API_DOCUMENTATION.md for full API details")
    print("2. Run migration: python migrate_pakapp_users.py")
    print("3. Integrate with PakApp using the registration endpoint")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
