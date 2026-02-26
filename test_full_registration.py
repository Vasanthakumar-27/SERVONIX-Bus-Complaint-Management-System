#!/usr/bin/env python
"""
Complete end-to-end registration test
"""
import requests
import sqlite3
import hashlib
import json

BASE_URL = 'http://localhost:5000'

def test_registration():
    print("=" * 60)
    print("TESTING COMPLETE REGISTRATION FLOW")
    print("=" * 60)
    
    # Step 1: Request OTP
    print("\n[STEP 1] Requesting OTP...")
    test_email = 'endtoendtest@example.com'
    test_name = 'E2E Test User'
    test_password = 'TestPass123@'
    
    response = requests.post(
        f'{BASE_URL}/api/register-request',
        json={
            'name': test_name,
            'email': test_email,
            'password': test_password
        }
    )
    print(f"  Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"  ERROR: {response.json()}")
        return False
    
    data = response.json()
    registration_token = data.get('registration_token', '')
    print(f"  Token received: {registration_token[:50]}...")
    print(f"  Message: {data.get('message', '')}")
    
    # Step 2: Get the OTP from database
    print("\n[STEP 2] Retrieving OTP from database...")
    conn = sqlite3.connect('data/servonix.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT otp_hash, expires_at FROM registration_otp WHERE email = ? ORDER BY created_at DESC LIMIT 1',
        (test_email,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("  ERROR: No OTP record found in database!")
        return False
    
    otp_hash, expires_at = row
    print(f"  OTP Hash: {otp_hash[:30]}...")
    print(f"  Expires: {expires_at}")
    
    # Step 3: Try to find the actual OTP by brute force (for testing)
    print("\n[STEP 3] Finding actual OTP...")
    found_otp = None
    
    # Try common test patterns first
    test_otps = []
    
    # Add numeric sequences
    for i in range(0, 1000000):
        otp_candidate = str(i).zfill(6)
        computed_hash = hashlib.sha256(otp_candidate.encode()).hexdigest()
        if computed_hash == otp_hash:
            found_otp = otp_candidate
            break
        
        # Only check first 100000 to avoid timeout
        if i >= 100000:
            print(f"  Checked 100,000 OTPs, still searching...")
            break
    
    if found_otp:
        print(f"  ✓ Found OTP: {found_otp}")
    else:
        print("  ✗ Could not find OTP by brute force (checked 100k combinations)")
        print("  This might indicate the OTP wasn't properly hashed or stored")
        return False
    
    # Step 4: Verify OTP
    print(f"\n[STEP 4] Verifying OTP ({found_otp})...")
    response = requests.post(
        f'{BASE_URL}/api/register-verify',
        json={
            'email': test_email,
            'otp': found_otp,
            'registration_token': registration_token
        }
    )
    print(f"  Status: {response.status_code}")
    response_data = response.json()
    print(f"  Response: {json.dumps(response_data, indent=2)}")
    
    if response.status_code == 201:
        print("\n✓ REGISTRATION SUCCESSFUL!")
        return True
    else:
        print(f"\n✗ REGISTRATION FAILED")
        print(f"  Error: {response_data.get('error', 'Unknown error')}")
        return False

if __name__ == '__main__':
    success = test_registration()
    exit(0 if success else 1)
