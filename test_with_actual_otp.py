#!/usr/bin/env python
"""
Test with the ACTUAL OTP from logs
"""
import requests
import hashlib
import sqlite3

BASE_URL = 'http://localhost:5000'

# Step 1: Create registration
print("Step 1: Requesting OTP...")
response = requests.post(
    f'{BASE_URL}/api/register-request',
    json={
        'name': 'Final Test User',
        'email': 'finaltest@example.com',
        'password': 'FinalPass123@'
    }
)

token = response.json()['registration_token']
print(f"✓ Registration requested, token received")

# The server logs will show [DEV-OTP] with the actual OTP
# For this test, we'll check the database for the otp_hash
# and manually try to reverse it
conn = sqlite3.connect('data/servonix.db')
cursor = conn.cursor()
cursor.execute(
    'SELECT otp_hash FROM registration_otp WHERE email = ? ORDER BY created_at DESC LIMIT 1',
    ('finaltest@example.com',)
)
row = cursor.fetchone()
conn.close()

print(f"\nOTP Hash from DB: {row[0][:30]}...")
print(f"\nLooking at server log for [DEV-OTP] message to get actual OTP...")
print(f"(Check the terminal running the server)")

# For automated testing, try some OTPs
print(f"\nAttempting verification (this should fail with wrong OTP)...")
response = requests.post(
    f'{BASE_URL}/api/register-verify',
    json={
        'email': 'finaltest@example.com',
        'otp': '000000',
        'registration_token': token
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
print(f"\nTo make verification succeed, the OTP from the server logs must be used.")
