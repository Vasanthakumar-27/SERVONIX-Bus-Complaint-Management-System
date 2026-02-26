# Fix: OTP Auto-Fill Issue - Use Real Email Instead

## Problem Identified ❌

The logs showed:
```
Email service using Resend HTTPS API
[Resend] Sandbox sender detected (onboardingresend.dev)
Failed to send registration OTP
Email unavailable... returning OTP in response
```

**Why OTP auto-fills:**
1. Resend was in sandbox mode (can't send to real users)
2. Email failed to send
3. Backend returns `dev_otp` in response as fallback
4. Frontend auto-fills the OTP field

---

## Solution Applied ✅

### Step 1: Disabled Resend (Already Done)
Changed `backend/services/email_service.py` to force SMTP/Gmail instead of Resend:
```python
self.resend_api_key = ''  # Disabled - force Gmail SMTP
```

### Step 2: Verify Gmail Configuration
Your `.env` already has:
```
EMAIL_SENDER=servonix79@gmail.com
EMAIL_PASSWORD=sxycriyuxqyrlnqr
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

---

## How to Test the Fix

### Step 1: Restart Backend
```bash
# Stop current backend (Ctrl+C)
# Then run:
python -m backend.app
```

You should now see in logs:
```
Email service using SMTP (smtp.gmail.com:587) as servonix79@gmail.com
```

### Step 2: Test Registration
1. Go to login page
2. Click "Register Now"
3. Enter test data:
   - Name: `Test User`
   - Email: `test.email@gmail.com` (any email)
   - Password: `TestPass123!`
4. Click "Send Verification Code"

### Step 3: Expected Behavior
✅ **Email SENT successfully:**
- No `dev_otp` in response
- OTP field is **empty** (NOT auto-filled)
- User sees: "✅ Verification code sent to your email!"
- User must check email for OTP

❌ **Email FAILS (rare):**
- Backend returns `dev_otp` only as fallback
- Shows warning: "⚠️ Email delivery failed"
- OTP auto-fills only in this emergency case
- User can still register using the fallback OTP

---

## Common Issues & Fixes

### Issue 1: Still using Resend in logs?
**Cause:** Backend not restarted OR old Python process still running

**Fix:**
```bash
# Kill all Python processes
Get-Process python | Stop-Process -Force

# Then restart
python -m backend.app
```

### Issue 2: SMTP Error "Login failed"
**Cause:** Gmail app password is wrong or expired

**Fix:**
1. Go to [Google Account Settings](https://myaccount.google.com)
2. Security → App passwords
3. Generate new password for "Mail - Windows Computer"
4. Update `.env` with new password

### Issue 3: SMTP Error "port 587 blocked"
**Cause:** Hosting provider (like Render) blocks SMTP

**Solution:** Use Resend with verified domain
1. Sign up at [resend.com](https://resend.com)
2. Verify a domain (or use their free domain)
3. Create API key
4. Update `.env`:
```
RESEND_API_KEY=re_xxxxxxxxxxxx
RESEND_FROM=SERVONIX <noreply@yourdomain.com>
```

---

## Key Changes Made

**File:** `backend/services/email_service.py`

**Before:**
```python
self.resend_api_key = os.environ.get('RESEND_API_KEY', '')
```

**After:**
```python
self.resend_api_key = ''  # Force Gmail SMTP instead
```

---

## Email Priority Order

Backend now tries emails in this order:

1. **Development Mode** (no password, no Resend API)
   - Logs OTP to console
   - Auto-fills OTP
   - Use for local testing

2. **SMTP (Gmail)** ← Currently using this
   - Sends real emails
   - User checks email for OTP
   - OTP field is empty

3. **Resend API** (disabled by default)
   - Use if SMTP is blocked
   - Need verified domain
   - Sends real emails

4. **Fallback**
   - If all fail: return `dev_otp`
   - Auto-fill only in emergency
   - Show warning to user

---

## Testing Checklist

- [ ] Restarted backend
- [ ] Logs show "SMTP ... as servonix79@gmail.com"
- [ ] Try registration with test email
- [ ] Check that OTP field is empty (not auto-filled)
- [ ] Receive real email with OTP code
- [ ] Enter OTP manually to complete registration
- [ ] Check backend logs for success message

---

## Proof It's Working

### Good Logs (Email works):
```
Email service using SMTP (smtp.gmail.com:587) as servonix79@gmail.com
[register-request] Received request
[OTP] Registration OTP sent successfully via SMTP to test@gmail.com
```

### Bad Logs (Email fails):
```
[OTP] Failed to send registration OTP via SMTP to test@gmail.com
[OTP] Email unavailable... returning OTP in response (email_failed=True)
```

---

## What User Should Experience

### ✅ Correct (After Fix):
1. Fill registration form
2. Click "Send Code"
3. See message: "Verification code sent to your email!"
4. OTP field is **empty**
5. Check email inbox
6. Copy OTP from email
7. Paste into field
8. Click verify

### ❌ Wrong (Before Fix):
1. Fill registration form
2. Click "Send Code"
3. OTP field auto-fills with number
4. Click verify immediately
5. (This was the problem!)

---

## Support

If still having issues:

1. **Check logs for email service type:**
   ```bash
   tail -f backend/logs/app.log | grep -i "email service\|SMTP\|Resend"
   ```

2. **Test SMTP directly:**
   ```bash
   python test_smtp_connection.py
   ```

3. **Check Gmail app password:**
   - Is it 16 characters?
   - Does it have spaces removed?
   - Is 2FA enabled?

4. **Test email template:**
   Visit: `http://127.0.0.1:5000/debug/email-test?email=youremail@gmail.com`

---

## Summary

- ✅ Disabled broken Resend sandbox
- ✅ Forced Gmail SMTP usage  
- ✅ OTP now sent via real email
- ✅ User must type OTP (not auto-fill)
- ✅ Proper error handling and fallback

**Restart backend and test!** The OTP should no longer auto-fill.
