#!/usr/bin/env python
"""
Direct test of register-verify with real OTP
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

# Step 1: Create new registration
print("Step 1: Requesting OTP...")
response = requests.post(
    f'{BASE_URL}/api/register-request',
    json={
        'name': 'Direct Test User',
        'email': 'directtest@example.com',
        'password': 'DirectPass123@'
    }
)

print(f"Status: {response.status_code}")
data = response.json()
token = data.get('registration_token', '')
print(f"Got token: {token[:50]}...")

# Step 2: Attempt verification with wrong OTP
print("\nStep 2: Testing with WRONG OTP (to see validation flow)...")
response = requests.post(
    f'{BASE_URL}/api/register-verify',
    json={
        'email': 'directtest@example.com',
        'otp': '000000',
        'registration_token': token
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Look at the server logs to see what message was logged
print("\n⚠️  The server logs will show [register-verify] messages explaining the failure")
print("⚠️  Check terminal for [DEV-OTP] message with the actual OTP")
