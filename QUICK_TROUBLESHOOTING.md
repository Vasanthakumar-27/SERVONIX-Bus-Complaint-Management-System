# ⚡ Quick OTP Troubleshooting Checklist

## OTP Not Arriving in User's Email?

Use this checklist to identify and fix the issue:

---

## Step 1: Check Email Service Status (2 minutes)

### Option A: Using the Diagnostic Tool (EASIEST)
1. Open: **`http://localhost:5000/test-email.html`**
2. Click **"Check Status"** button
3. Look at the result - it should show which email service is configured

### Option B: API Endpoint
```bash
curl http://localhost:5000/api/email-status
```

### What Should I See?
One of these:
- ✅ `"mode": "smtp"` (Gmail/SMTP configured)
- ✅ `"mode": "resend"` (Resend API configured)
- ❌ `"mode": "development"` (No credentials - NEEDS FIX)

**If you see "development" mode:** Go to Step 2 ⬇️

---

## Step 2: Run Full Diagnostics (2 minutes)

1. Open: **`http://localhost:5000/test-email.html`**
2. Click **"Run Diagnostics"** button
3. Read the troubleshooting suggestions
4. Follow the recommended solution

---

## Step 3: Verify Email Works (1 minute)

1. Open: **`http://localhost:5000/test-email.html`**
2. Enter **YOUR EMAIL ADDRESS** in the test section
3. Click **"Send Test Email"**
4. **Check your inbox** (and spam folder) for the test email

### If You Receive It:
✅ Email is working correctly - issue solved!

### If You Don't Receive It:
❌ Email configuration has an issue - follow the diagnostics suggestions

---

## Common Fixes (Quick Reference)

### Issue 1: No Email Credentials Configured
**Error Message:** "Development mode - no email credentials configured"

**Fix in 30 seconds:**
1. Open `backend/.env` file
2. Find this section:
   ```
   EMAIL_SENDER=servonix79@gmail.com
   EMAIL_PASSWORD=sxycriyuxqyrlnqr
   ```
3. **Most important:** Check if `EMAIL_PASSWORD` is set! 
   - If blank or says `your_password_here` → that's the problem
4. Get a Gmail App Password (see below)
5. Restart the backend server

---

### Issue 2: Gmail Authentication Failed

**Error Message:** "SMTP authentication failed"

**Fix in 2 minutes:**

**For Gmail Users:**

1. Go to: https://myaccount.google.com/
2. Click **Security** in left menu
3. Scroll down, enable **2-Step Verification** (if not enabled)
4. Go back to Security, find **App passwords**
5. Select: "Mail" + "Windows Computer"
6. Copy the **16-character password** (ignore spaces)
7. Open `backend/.env`
8. Replace the `EMAIL_PASSWORD` value with the one you copied
9. **Restart the server** → Done!

---

### Issue 3: Port 587 Blocked (Render, Heroku, AWS)

**Error Message:** "Cannot connect to SMTP server (port blocked)"

**This is VERY common on:**
- Render.com
- Heroku
- AWS
- Other cloud hosting

**Fix: Use Resend API instead (5 minutes)**

1. Sign up FREE at: https://resend.com
2. Create a new domain or verify existing one
3. In dashboard, create API key → Copy it
4. Open `backend/.env`
5. Add these lines:
   ```
   RESEND_API_KEY=re_paste_your_key_here
   RESEND_FROM=SERVONIX <noreply@yourdomain.com>
   ```
6. Remove or comment out Gmail settings (optional)
7. Restart server → Done!

---

## The Fastest Way to Fix It

1. 🔧 Open `http://localhost:5000/test-email.html`
2. 🔍 Click "Run Diagnostics"
3. 👀 Read the specific issue
4. ⚡ Follow the exact fix provided
5. ✅ Test with "Send Test Email"

---

## If You're Still Stuck

### Check Server Logs
```bash
# Watch real-time logs
tail -f backend/logs/app.log

# Look for [OTP] messages
# Should see something like:
# "[OTP] Registration OTP sent to user@example.com"
# OR
# "[OTP] Failed to send registration OTP to user@example.com"
```

### Check Email Was Actually Sent
1. Look in server logs for `[OTP]` messages
2. If you see "sent successfully" → email was sent, check user's spam folder
3. If you see "failed" → email service needs fixing

### Manual Email Test
```bash
curl -X POST http://localhost:5000/api/email-test \
  -H "Content-Type: application/json" \
  -d '{"to": "your.email@example.com"}'
```

---

## Decision Tree

```
OTP Not Arriving?
│
├─ Check Diagnostics Page
│  ├─ Shows: "development mode" ──→ Set EMAIL_PASSWORD in .env
│  ├─ Shows: "authentication failed" ──→ Use Gmail App Password
│  ├─ Shows: "port blocked" ──→ Use Resend API
│  └─ Shows: "working" ──→ Check user's spam folder
│
└─ Still Not Working?
   ├─ Restart backend server
   ├─ Check .env file has no typos
   ├─ Check firewall/port settings
   └─ Review server logs for [OTP] messages
```

---

## What Users Should See

### When They Register:
1. ✅ Instant message: "Verification code sent! Check your email."
2. 📧 Receive OTP code via email
3. ✏️ Enter code and complete registration
4. ✅ Account created

### When They Reset Password:
1. ✅ Instant message: "OTP sent to your email!"
2. 📧 Receive OTP code via email
3. ✏️ Enter code to reset password
4. ✅ Password reset complete

---

## Success Indicators

✅ Users receive OTP emails within seconds
✅ Diagnostic tool shows "connection ok: true"
✅ Test email is received successfully
✅ Server logs show "[OTP] ... sent successfully"
✅ Users can complete registration/password reset

---

## 5-Minute Quick Fix

```bash
# 1. Open diagnostic page
open http://localhost:5000/test-email.html

# 2. Click "Run Diagnostics" 
# 3. Read the error message
# 4. Apply the fix suggested
# 5. Click "Send Test Email"
# 6. Check if email arrives

# 7. If still failing, restart server:
# Press Ctrl+C in terminal, then:
python -m backend.app
```

**That's it!** 90% of issues are fixed with these steps.

---

**Need Help?** 
- Check `EMAIL_SETUP_GUIDE.md` for detailed instructions
- Check `OTP_UPDATES_SUMMARY.md` for technical details
- Check server logs for [OTP] messages
