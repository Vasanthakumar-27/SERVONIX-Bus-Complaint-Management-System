#!/usr/bin/env python
"""Test registration endpoint with the development mode fix"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"
TEST_EMAIL = f"test_{int(time.time())}@example.com"

print("=" * 60)
print("TESTING REGISTRATION FIX FOR DEVELOPMENT MODE")
print("=" * 60)
print()

# Start server in background first
print("Testing registration request endpoint...")
print(f"Email: {TEST_EMAIL}")
print()

try:
    response = requests.post(
        f"{BASE_URL}/api/register-request",
        json={
            "name": "Test User",
            "email": TEST_EMAIL,
            "password": "TestPass123!"
        },
        timeout=10
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Body:")
    data = response.json()
    print(json.dumps(data, indent=2))
    print()
    
    if response.status_code == 200:
        print("✅ SUCCESS - Registration request returned 200 OK")
        print("✅ This means:")
        print("   - OTP was generated and stored")
        print("   - User can proceed to verification step")
        print("   - In development mode, OTP is logged to console")
        if data.get('development_mode'):
            print("   - 🔍 Check server logs for: [DEV-OTP] Registration OTP...")
    elif response.status_code == 400:
        if data.get('email_failed'):
            print("❌ FAILED - Email sending failed (check SMTP credentials)")
        else:
            print("❌ FAILED - Input validation error")
    else:
        print(f"⚠️ UNEXPECTED - Got status code {response.status_code}")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()
    print("Make sure backend server is running:")
    print("  python -m backend.app")
