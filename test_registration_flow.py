#!/usr/bin/env python
import requests
import json
import sqlite3

API_URL = 'http://localhost:5000'

# Step 1: Request OTP
print('=== STEP 1: Register and Request OTP ===')
response = requests.post(
    f'{API_URL}/api/register-request',
    json={
        'name': 'Test Live User',
        'email': 'livetest@example.com',
        'password': 'LiveTest123@'
    }
)
print(f'Status: {response.status_code}')
data = response.json()
print(f'Registration Token received: {data.get("registration_token", "NONE")[:50]}...')
print(f'Message: {data.get("message", "")}')

reg_token = data.get('registration_token', '')

if response.status_code == 200:
    #  Get the OTP directly from the database for testing
    conn = sqlite3.connect('data/servonix.db')
    cursor = conn.cursor()
    cursor.execute('SELECT otp_hash FROM registration_otp WHERE email = ? ORDER BY created_at DESC LIMIT 1', ('livetest@example.com',))
    row = cursor.fetchone()
    
    if row:
        print('✓ Registration OTP record found in DB')
        print(f'  OTP Hash: {row[0][:20]}...')
    else:
        print('✗ No OTP record found in DB')
    
    # Now let's test verification with a mock OTP
    # For this test, we need to know what OTP was generated
    # Let me decode the JWT token to see the OTP hash
    import jwt
    try:
        payload = jwt.decode(reg_token, options={"verify_signature": False})
        print('\n=== JWT PAYLOAD ===')
        print(f'Type: {payload.get("type")}')
        print(f'Email: {payload.get("email")}')
        print(f'OTP Hash: {payload.get("otp_hash")[:20]}...')
        print(f'Expires: {payload.get("expires_at")}')
    except Exception as e:
        print(f'Failed to decode JWT: {e}')
    
    conn.close()

print('\n=== Now testing verification endpoint ===')
print('Note: We need the actual OTP to test - it was sent to the email')
print('For now, let\'s try with an invalid OTP to see the response format')

response = requests.post(
    f'{API_URL}/api/register-verify',
    json={
        'email': 'livetest@example.com',
        'otp': '000000',
        'registration_token': reg_token
    }
)
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
