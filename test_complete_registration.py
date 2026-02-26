#!/usr/bin/env python
import requests

# Step 1: Request OTP
print('=== Generating OTP ===')
response = requests.post(
    'http://localhost:5000/api/register-request',
    json={
        'name': 'Debug Test User',
        'email': 'debugtest@example.com',
        'password': 'DebugPass123@'
    }
)
print(f'Status: {response.status_code}')
data = response.json()
print(f'Message: {data.get("message", "")}')
token = data.get('registration_token', '')

# Step 2: Try to get the OTP
print('\n=== Getting OTP via debug endpoint ===')
response = requests.get('http://localhost:5000/api/debug-get-otp/debugtest@example.com')
print(f'Status: {response.status_code}')
otp_data = response.json()
print(f'Response: {otp_data}')

if 'otp' in otp_data:
    otp = otp_data['otp']
    print(f'\n=== Verifying registration with OTP: {otp} ===')
    response = requests.post(
        'http://localhost:5000/api/register-verify',
        json={
            'email': 'debugtest@example.com',
            'otp': otp,
            'registration_token': token
        }
    )
    print(f'Status: {response.status_code}')
    print(f'Response: {response.json()}')
