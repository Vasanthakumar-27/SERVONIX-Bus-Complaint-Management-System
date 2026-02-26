# RESEND API SETUP - Complete Guide

## What You Need
✅ OTP sent via Resend to user's email  
✅ User receives OTP  
✅ User enters OTP manually  
✅ Registration completes successfully  

---

## Step 1️⃣: Get Resend API Key

### Option A: Quick Start (Dev/Testing)
```
1. Go to https://resend.com/home
2. Sign up with your email (it's free!)
3. Verify your email
4. Click "API Keys" in sidebar
5. Copy the API key (starts with "re_")
6. ⚠️ LIMITATION: Only sends to your verified email address
```

### Option B: Production (Send to Anyone)
```
1. Sign up at https://resend.com
2. Go to Domains tab
3. Add your domain (you must own it)
4. Follow DNS verification instructions
5. Once verified, you can send from that domain
6. Create API key
7. Use that domain in RESEND_FROM
```

---

## Step 2️⃣: Update Your .env File

Open `backend/.env` and find this section:

```
# RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
# RESEND_FROM=SERVONIX <noreply@yourdomain.com>
```

**Replace with YOUR details:**

### If using Quick Start (dev):
```env
RESEND_API_KEY=re_9a8b7c6d5e4f3g2h1i0j0k
RESEND_FROM=SERVONIX <onboarding@resend.dev>
```

### If using Production (custom domain):
```env
RESEND_API_KEY=re_9a8b7c6d5e4f3g2h1i0j0k
RESEND_FROM=SERVONIX <noreply@yourdomain.com>
```

---

## Step 3️⃣: Verify Configuration

### Check your .env looks like:
```env
RESEND_API_KEY=re_xxxxxxxxxxxx  ← Should have a real API key
RESEND_FROM=SERVONIX <noreply@...>  ← Should have your domain

# NOT this (commented out or empty):
# RESEND_API_KEY=
```

### Make sure to NOT have:
```env
✗ RESEND_API_KEY=  (empty)
✗ RESEND_API_KEY commented out
✗ RESEND_FROM=SERVONIX <onboarding@resend.dev> (if you have your own domain)
```

---

## Step 4️⃣: Restart Backend

```bash
# Stop current backend (Ctrl+C)
# Then run:
python -m backend.app
```

**Expected log output:**
```
Email service using Resend HTTPS API
```

**NOT this (old broken way):**
```
Sandbox sender detected (onboardingresend.dev)
```

---

## Step 5️⃣: Test OTP Delivery

### Test 1: Check API Key is Valid
```bash
curl -H "Authorization: Bearer re_YOUR_API_KEY" \
  https://api.resend.com/emails \
  -X GET
```

Should return: `200 OK`

### Test 2: Registration Test
1. Open frontend login page
2. Click "Register Now"
3. Fill in form:
   - Name: `Test User`
   - Email: `your-email@gmail.com` (the one that will receive OTP)
   - Password: `TestPass123!`
4. Click "Send Verification Code"

### Expected Results:
```
✅ Message shows: "Verification code sent to your email!"
✅ OTP field is EMPTY (not auto-filled)
✅ Check your email for OTP
✅ Copy 6-digit code from email
✅ Paste into field and click Verify
✅ Registration complete!
```

---

## Step 6️⃣: Check Backend Logs

Run this to watch logs in real-time:
```bash
# In a second terminal:
tail -f backend/logs/app.log | grep -i "resend\|otp\|email"
```

**Good logs (OTP sent via Resend):**
```
Email service using Resend HTTPS API
[Resend] Email sent to user@gmail.com: Registration OTP
[OTP] Registration OTP sent successfully via Resend to user@gmail.com
```

**Bad logs (OTP failed, returning fallback):**
```
[Resend] Failed (401): Unauthorized
[OTP] Failed to send registration OTP via Resend
[OTP] Email unavailable... returning OTP in response
```

---

## Troubleshooting

### Problem 1: API Key Rejected (401 Error)
```
[Resend] Failed (401): Unauthorized
```

**Solution:**
1. Copy API key again from https://resend.com
2. Paste the ENTIRE key (it should start with `re_`)
3. Make sure no extra spaces
4. Restart backend
5. Test again

### Problem 2: Still using Sandbox (onboarding@resend.dev)
```
[Resend] Sandbox sender detected
```

**Solution:**
1. Check your .env files
2. Make sure `RESEND_API_KEY` line is NOT commented out
3. Make sure it has actual API key (not empty)
4. Restart backend

### Problem 3: OTP Still Auto-filling
```
No email in backend logs, but OTP auto-fills
```

**Solution:**
1. Clear browser cache/cookies
2. Hard refresh: `Ctrl+Shift+R`
3. Try registration again
4. Check logs while you try

### Problem 4: Email Not Received
```
Logs show: Email sent successfully
But no email in inbox
```

**Solution:**
1. Check spam/junk folder
2. Verify sender email in logs: `to_email@gmail.com`
3. Wait 1-2 minutes (may take time)
4. Try different email address
5. Check Resend dashboard for bounce reasons

### Problem 5: Domain Verification Failed
```
Error: Domain not verified
```

**Solution:**
1. Go to https://resend.com/domains
2. Check domain status
3. Add DNS records (TXT, MX, etc.)
4. Wait for verification (usually 10 minutes)
5. Use the domain in RESEND_FROM once verified

---

## Complete .env Example

Here's what a complete working .env should look like:

```env
DB_HOST=127.0.0.1
DB_USER=root
DB_PASSWORD=
DB_NAME=bus_complaints

# RESEND API - Primary Email Service
RESEND_API_KEY=re_9a8b7c6d5e4f3g2h1i0j0k1a2b3c4d
RESEND_FROM=SERVONIX <noreply@yourdomain.com>

# Gmail SMTP - Fallback (only used if RESEND_API_KEY not set)
EMAIL_SENDER=servonix79@gmail.com
EMAIL_PASSWORD=sxycriyuxqyrlnqr
EMAIL_FROM_NAME=SERVONIX

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_TIMEOUT=10

DEBUG=1
```

---

## Email Service Priority

Backend tries providers in this order:

```
1. Resend API (if RESEND_API_KEY is set)
   ↓ Success? → Send email, OTP empty field ✅
   ↓ Fail? → Try next
   
2. Gmail SMTP (if EMAIL_PASSWORD is set)
   ↓ Success? → Send email, OTP empty field ✅
   ↓ Fail? → Try next
   
3. Development Mode (console logging)
   ↓ Log OTP to console/file
   ↓ Auto-fill OTP in frontend ⚠️
```

---

## Testing Checklist

- [ ] Created Resend account
- [ ] Got API key from Resend dashboard
- [ ] Updated RESEND_API_KEY in backend/.env
- [ ] Updated RESEND_FROM with your domain
- [ ] Restarted backend
- [ ] Check logs show "Resend HTTPS API" (not sandbox)
- [ ] Test registration with real email
- [ ] Check email received OTP
- [ ] User manually enters OTP
- [ ] Registration completes successfully

---

## Next Step

1. **Get API key** from https://resend.com
2. **Update .env** with API key and domain
3. **Restart backend**: `Ctrl+C` then `python -m backend.app`
4. **Test registration** with real email
5. **Verify** OTP arrives in inbox

That's it! You're now using production Resend for OTP delivery. 🚀

---

## Support Links

- **Resend Dashboard:** https://resend.com/home
- **Resend Docs:** https://resend.com/docs
- **Domain Setup:** https://resend.com/docs/dashboard/domains/setup
- **API Reference:** https://resend.com/docs/api-reference/emails/send
