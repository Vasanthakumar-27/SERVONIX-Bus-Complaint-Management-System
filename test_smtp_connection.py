#!/usr/bin/env python3
"""
Test Gmail SMTP Connection - Verify Email Service is Working
Run: python test_smtp_connection.py
"""

import smtplib
import os
from dotenv import load_dotenv

# Load environment variables from backend/.env
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
load_dotenv(os.path.join(backend_dir, '.env'))

# Get credentials from environment
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', 'servonix79@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))

print("=" * 60)
print("SMTP Connection Test - Gmail")
print("=" * 60)
print(f"\nConfiguration:")
print(f"  SMTP Server: {SMTP_SERVER}")
print(f"  SMTP Port: {SMTP_PORT}")
print(f"  Email Sender: {EMAIL_SENDER}")
print(f"  Password: {'***' + EMAIL_PASSWORD[-4:] if EMAIL_PASSWORD else 'NOT SET'}")

if not EMAIL_PASSWORD:
    print("\n❌ ERROR: EMAIL_PASSWORD not set in backend/.env")
    print("Fix: Add EMAIL_PASSWORD to backend/.env file")
    exit(1)

# Test connection
print("\n" + "=" * 60)
print("Testing SMTP Connection...")
print("=" * 60)

try:
    print("\n1. Connecting to SMTP server...")
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
    print(f"   ✓ Connected to {SMTP_SERVER}:{SMTP_PORT}")
    
    print("\n2. Starting TLS (encryption)...")
    server.starttls()
    print("   ✓ TLS started")
    
    print("\n3. Authenticating...")
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    print(f"   ✓ Authenticated as {EMAIL_SENDER}")
    
    print("\n4. Checking connection...")
    server.noop()
    print("   ✓ Connection verified")
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS: Gmail SMTP is working!")
    print("=" * 60)
    print("\nThe email service should now:")
    print("  • Send OTP emails to users")
    print("  • NOT auto-fill OTP in registration form")
    print("  • Show this message: 'Verification code sent to your email'")
    
    server.quit()
    
except smtplib.SMTPAuthenticationError:
    print("\n❌ ERROR: Authentication failed")
    print("Fix: Check your Gmail app password")
    print("  1. Go to https://myaccount.google.com")
    print("  2. Security → App passwords")
    print("  3. Generate new password for Mail - Windows")
    print("  4. Update EMAIL_PASSWORD in backend/.env")
    
except smtplib.SMTPException as e:
    print(f"\n❌ SMTP Error: {str(e)}")
    print("\nCommon reasons:")
    print("  • Port 587 is blocked (use Resend API instead)")
    print("  • Gmail account locked (enable 2FA first)")
    print("  • Too many failed login attempts (try later)")
    
except Exception as e:
    print(f"\n❌ Connection Error: {str(e)}")
    print("\nCommon reasons:")
    print("  • Network timeout")
    print("  • Firewall blocking SMTP")
    print("  • Wrong SMTP server/port")

print("\n" + "=" * 60)
print("Next Steps:")
print("=" * 60)
print("1. If test passed: Restart backend and test registration")
print("2. If test failed: See 'Fix' suggestions above")
print("3. If port is blocked: Use Resend API with verified domain")
