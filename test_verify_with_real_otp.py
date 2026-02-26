#!/usr/bin/env python
"""
Test registration verification with known OTP
"""
import requests
import sqlite3
import hashlib

BASE_URL = 'http://localhost:5000'

# From logs: [DEV-OTP] Registration OTP for endtoendtest@example.com: 242038
test_otp = '242038'
test_email = 'endtoendtest@example.com'

# Get the registration token
conn = sqlite3.connect('data/servonix.db')
cursor = conn.cursor()
cursor.execute(
    'SELECT otp_hash FROM registration_otp WHERE email = ? ORDER BY created_at DESC LIMIT 1',
    (test_email,)
)
row = cursor.fetchone()
conn.close()

if not row:
    print("ERROR: No OTP record found")
    exit(1)

stored_hash = row[0]
computed_hash = hashlib.sha256(test_otp.encode()).hexdigest()

print("OTP Verification Debug")
print("=" * 60)
print(f"OTP: {test_otp}")
print(f"Computed Hash: {computed_hash}")
print(f"Stored Hash:   {stored_hash}")
print(f"Match: {computed_hash == stored_hash}")
print()

# Now test the full registration verification flow
# First, get the latest registration token
conn = sqlite3.connect('data/servonix.db')
cursor = conn.cursor()

# We need to extract the token from the last register-request call
# Since we don't have it stored, let's make a new registration request
conn.close()

print("Making new registration request to get token...")
response = requests.post(
    f'{BASE_URL}/api/register-request',
    json={
        'name': 'Verify Test',
        'email': 'verifytest@example.com',
        'password': 'VerifyPass123@'
    }
)

if response.status_code != 200:
    print(f"Registration request failed: {response.json()}")
    exit(1)

data = response.json()
registration_token = data['registration_token']

print(f"Token: {registration_token[:50]}...")

# Get the OTP from logs (we'd see it logged)
# For now, let's extract it from database
conn = sqlite3.connect('data/servonix.db')
cursor = conn.cursor()
cursor.execute(
    'SELECT otp_hash FROM registration_otp WHERE email = ? ORDER BY created_at DESC LIMIT 1',
    ('verifytest@example.com',)
)
row = cursor.fetchone()
conn.close()

if not row:
    print("ERROR: OTP not found in DB")
    exit(1)

# Since we can't easily get the actual OTP, let's test with wrong OTP first
print("\nTesting verification with WRONG OTP...")
response = requests.post(
    f'{BASE_URL}/api/register-verify',
    json={
        'email': 'verifytest@example.com',
        'otp': '000000',
        'registration_token': registration_token
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# The server logs should show us information about why it failed
print("\nCheck the server logs for [register-verify] messages to see validation steps")
