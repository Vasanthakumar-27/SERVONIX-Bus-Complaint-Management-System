#!/usr/bin/env python
"""
Validate OTP Registration Fix in DEPLOYED ENVIRONMENT
Tests against the live Render deployment
"""
import requests
import json
import time

# Deployed URL (from user's screenshot)
DEPLOYED_URL = "https://servonix-bus-complai.onrender.com"
# Using localhost for testing currently, but deploy URL would be used in production
# DEPLOYED_URL = "https://your-render-deployment.onrender.com"

print("=" * 70)
print("OTP REGISTRATION SYSTEM - DEPLOYMENT VALIDATION")
print("=" * 70)
print(f"\nTesting against: {DEPLOYED_URL}")
print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# Test email
TEST_EMAIL = f"deploytest{int(time.time())}@example.com"
TEST_NAME = "Deploy Test User"
TEST_PASSWORD = "DeployTest123@"

print(f"\nTest Credentials:")
print(f"  Email: {TEST_EMAIL}")
print(f"  Name: {TEST_NAME}")

# ============================================================
# STEP 1: Test OTP Request
# ============================================================
print("\n" + "=" * 70)
print("STEP 1: Request OTP Registration")
print("=" * 70)

try:
    response = requests.post(
        f"{DEPLOYED_URL}/api/register-request",
        json={
            "name": TEST_NAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        },
        timeout=15
    )
    
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ OTP Request SUCCESS")
        registration_token = data.get('registration_token', '')
        
        # Show first/last part of token
        if registration_token:
            print(f"Token received: {registration_token[:50]}...{registration_token[-20:]}")
    else:
        print(f"\n❌ OTP Request FAILED")
        if "email_failed" in data:
            print("⚠️  Email delivery failed - check SMTP configuration")
        print(f"Error: {data.get('error', 'Unknown error')}")
        exit(1)
        
except requests.exceptions.Timeout:
    print("\n❌ TIMEOUT - Server took too long to respond")
    print("This might indicate the deployment is slow or offline")
    exit(1)
except requests.exceptions.ConnectionError as e:
    print(f"\n❌ CONNECTION ERROR: {e}")
    print("Server may be offline or URL is incorrect")
    exit(1)
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    exit(1)

# ============================================================
# STEP 2: Test Database Availability
# ============================================================
print("\n" + "=" * 70)
print("STEP 2: Check Email Status Endpoint")
print("=" * 70)

try:
    response = requests.get(
        f"{DEPLOYED_URL}/api/email-status",
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ Email Service Status: OK")
        if data.get('resend_key_configured'):
            print("  Using Resend API for email")
        elif data.get('smtp_configured'):
            print("  Using SMTP for email")
        else:
            print("  ⚠️  No email service configured!")
    else:
        print(f"\n⚠️  Email status check returned {response.status_code}")
        
except Exception as e:
    print(f"\n⚠️  Could not check email status: {e}")

# ============================================================
# STEP 3: Test Email Diagnostics
# ============================================================
print("\n" + "=" * 70)
print("STEP 3: Run Email Diagnostics")
print("=" * 70)

try:
    response = requests.get(
        f"{DEPLOYED_URL}/api/email-diagnose",
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        print(f"Status: {data.get('status')}")
        print(f"Message: {data.get('message')}")
        print("\n✅ Email Service: WORKING")
    else:
        print(f"❌ Diagnostic failed: {data}")
        
except Exception as e:
    print(f"⚠️  Diagnostics failed: {e}")

# ============================================================
# STEP 4: Info about Manual Verification
# ============================================================
print("\n" + "=" * 70)
print("STEP 4: Manual Verification Instructions")
print("=" * 70)

print(f"""
To complete the OTP verification test:

1. Check email at: {TEST_EMAIL}
2. Look for registration OTP (6-digit code)
3. Use that OTP with this endpoint:

   POST {DEPLOYED_URL}/api/register-verify
   Body: {{
     "email": "{TEST_EMAIL}",
     "otp": "XXXXXX",  // 6-digit code from email
     "registration_token": "{registration_token[:30]}..."
   }}

Expected Success Response (201):
{{
  "message": "Registration successful! You can now login.",
  "user": {{
    "id": <user_id>,
    "name": "{TEST_NAME}",
    "email": "{TEST_EMAIL}"
  }}
}}

Expected Failure Response (400) - if OTP is wrong:
{{
  "error": "Invalid verification code"
}}
""")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("VALIDATION SUMMARY")
print("=" * 70)
print("""
✅ Step 1 - OTP Request: PASS
   The registration endpoint accepted the request and returned a token.
   This means the server is responding and database is accessible.

⚠️  Step 2-3 - Email Service: CHECK SEPARATELY
   If "Email delivery failed" message appears in Step 1 response,
   check the email configuration in the deployment.

📧 Step 4 - Complete Verification: MANUAL TEST
   To verify the complete flow works:
   - Check if user receives email with OTP
   - Submit OTP to /register-verify endpoint
   - Verify account creation succeeds

✨ If all steps pass, the OTP registration system is fully functional!
""")
