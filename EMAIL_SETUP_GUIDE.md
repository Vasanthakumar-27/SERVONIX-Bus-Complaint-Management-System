# SERVONIX Email OTP Configuration Guide

## Issue: OTP Emails Not Arriving

If users are not receiving OTP (One-Time Password) emails for registration or password reset, follow this guide to diagnose and fix the issue.

---

## Quick Diagnostic Test

### Step 1: Test Email Service
Open this URL in your browser: **`http://localhost:5000/test-email.html`**

This page provides:
- ✅ Email service status check
- ✅ Comprehensive diagnostics
- ✅ Test email sending
- ✅ Troubleshooting solutions

---

## Common Issues & Solutions

### Issue 1: Email Service in Development Mode

**Problem:** You see `"Development mode - no email credentials configured"`

**Solution:**
1. Open `backend/.env`
2. Set your email credentials:
   ```
   EMAIL_SENDER=your_gmail@gmail.com
   EMAIL_PASSWORD=your_app_password
   ```
3. Restart the backend server

---

### Issue 2: Gmail Authentication Failed

**Problem:** You see `"SMTP authentication failed"`

**Solution:**
Gmail requires an App Password (not your account password):

1. Go to https://myaccount.google.com/
2. Click **Security** (left sidebar)
3. Enable **2-Step Verification** (if not already enabled)
4. Go back to Security and click **App passwords**
5. Select "Mail" and "Windows Computer"
6. Copy the generated 16-character password
7. Update `backend/.env`:
   ```
   EMAIL_PASSWORD=paste_the_16_char_password_here
   ```
8. Restart the backend server

---

### Issue 3: Port 587 is Blocked (Common on Render, Heroku, etc.)

**Problem:** You see `"Cannot connect to SMTP server (port blocked)"`

**Solution:** Use Resend API instead (works on all cloud platforms):

1. Sign up for free at https://resend.com
2. Add and verify a domain (or use their sandbox)
3. Create an API key in the Resend dashboard
4. Update `backend/.env`:
   ```
   RESEND_API_KEY=re_your_api_key_here
   RESEND_FROM=SERVONIX <noreply@your-domain.com>
   ```
5. Restart the backend server

**Note:** If using sandbox (onboarding@resend.dev), emails only go to the Resend account owner.

---

### Issue 4: Email Not Configured in Production

**Problem:** OTP is not being sent and you see an error

**Solution:**
Ensure your production environment has email credentials set:

```bash
# For Render deployment:
# Set these environment variables in Render dashboard:
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# OR use Resend:
RESEND_API_KEY=re_your_api_key
RESEND_FROM=SERVONIX <noreply@yourdomain.com>
```

---

## Email Configuration Priority

The system tries email services in this order:

1. **Resend API** (fastest, Render-compatible) - if `RESEND_API_KEY` is set
2. **SMTP/Gmail** - if `EMAIL_PASSWORD` is set
3. **Development Mode** (logs only, no emails sent) - if neither above are configured

---

## Testing Endpoints

### Check Email Status
```
GET http://localhost:5000/api/email-status
```
Returns current email configuration mode.

### Run Full Diagnostics
```
GET http://localhost:5000/api/email-diagnose
```
Returns detailed diagnostics with troubleshooting steps.

### Send Test Email
```
POST http://localhost:5000/api/email-test
Body: { "to": "test@example.com" }
```
Sends a test email to verify configuration.

---

## OTP Email Message Flow

1. **User Registers** → Backend generates OTP → OTP sent to email
2. **User enters OTP** from email → OTP verified → Account created
3. **User Forgotten Password** → Backend generates OTP → OTP sent to email
4. **User enters OTP** from email → Password reset allowed

**Important:** OTP codes are **NEVER** shown on screen - they MUST be sent via email.

---

## Verifying Setup Works

1. Go to **`http://localhost:5000/test-email.html`**
2. Click "**Check Status**" - should show your email configuration
3. Click "**Run Diagnostics**" - should show all services as OK
4. Enter your email in the test section
5. Click "**Send Test Email**"
6. Check your inbox - you should receive a test email

If you receive the test email → your email is configured correctly.

---

## Debugging Tips

### Check Server Logs
```bash
# Watch the application logs
tail -f backend/logs/app.log

# Look for [OTP] messages to see what happened
```

### Email Development Log (if in dev mode)
```bash
# Check what emails were generated
cat backend/logs/email_dev.log
```

### Common Error Messages
- `"SMTP authentication failed"` → Wrong email or password
- `"Cannot connect to SMTP server"` → Port blocked, use Resend
- `"Resend sandbox"` → Only delivers to Resend account owner
- `"Development mode"` → Email credentials not set

---

## Still Having Issues?

1. **Check .env file exists** at `backend/.env`
2. **Verify no spaces** in email credentials
3. **Restart the server** after changing .env
4. **Check firewall** - port 587 might be blocked
5. **Run diagnostics** at `http://localhost:5000/test-email.html`

---

## Users Perspective

Users will see:
- ✅ Instant feedback: "Verification code sent! Check your email."
- ✅ Clear instructions: "Check your inbox for the verification code"
- ⚠️ If email fails: Users are notified and can retry
- ⏱️ OTP expires in 5 minutes
- 🔄 Can resend OTP multiple times (rate limited)

---

**Need Help?** Check the diagnostic page or review the error message in your server logs.
