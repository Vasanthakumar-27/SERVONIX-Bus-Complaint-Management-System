# RESEND OTP Setup - Quick Checklist

Copy and paste these URLs into your browser to complete setup:

---

## ✅ Quick Setup (5 minutes)

### 1. Get Resend API Key (2 minutes)
```
1. Open: https://resend.com/home
2. Sign up with your email (or login if you have account)
3. Go to: https://resend.com/api-keys
4. Copy the API key (looks like: re_9a8b7c6d...)
5. Keep it open in a tab
```

### 2. Update .env File (1 minute)
```
Edit: backend/.env

Find this section:
RESEND_API_KEY=
RESEND_FROM=SERVONIX <noreply@servonix.com>

Replace with:
RESEND_API_KEY=re_YOUR_KEY_HERE
RESEND_FROM=SERVONIX <noreply@yourdomain.com>

(Or use noreply@resend.dev if you don't have domain yet)
```

### 3. Restart Backend (1 minute)
```
1. Press Ctrl+C to stop current backend
2. Run: python -m backend.app
3. Wait for "Serving on..."
4. Look for log: "Email service using Resend HTTPS API"
```

### 4. Test Registration (1 minute)
```
1. Open frontend login page
2. Click "Register Now"
3. Fill form and click "Send Code"
4. Check your email for OTP
5. Paste OTP and click Verify
```

---

## 🎯 What Happens

### Before (Broken):
```
User clicks "Send Code"
→ Resend fails (sandbox mode)
→ Backend returns OTP in response
→ Frontend auto-fills OTP field
→ User doesn't need email
❌ WRONG!
```

### After (Fixed):
```
User clicks "Send Code"
→ Resend sends real email ✅
→ Backend returns success
→ Frontend leaves OTP field EMPTY ✅
→ User checks email ✅
→ User copies OTP from email ✅
→ User pastes into field and verifies ✅
→ Registration complete ✅
```

---

## 📋 What You're Doing

1. **Enable Resend** (production email API)
2. **Add API Key** (your unique identifier)
3. **Set domain** (where emails come from)
4. **Test it** (verify OTP delivery works)

---

## 🚀 Let's Do It!

### Step 1: Open Resend
👉 **https://resend.com/home**
- Sign up (free)
- Get API key from dashboard
- Copy it

### Step 2: Update .env
Open: `backend/.env`

Paste your API key:
```
RESEND_API_KEY=re_PASTE_YOUR_KEY_HERE
RESEND_FROM=SERVONIX <noreply@yourdomain.com>
```

### Step 3: Restart Backend
```
Ctrl+C
python -m backend.app
```

### Step 4: Test Registration
1. Frontend → Register Now
2. Fill form
3. Click "Send Code"
4. Check email
5. Copy OTP
6. Paste and verify

---

## ✅ Success Looks Like

### Logs Show:
```
Email service using Resend HTTPS API ✅
[Resend] Email sent to user@gmail.com ✅
[OTP] Registration OTP sent successfully via Resend ✅
```

### Frontend Shows:
```
"✅ Verification code sent to your email!" ✅
(OTP field is empty, not auto-filled) ✅
```

### User Experience:
```
Receives real OTP in email ✅
Types it manually ✅
Registration completes ✅
```

---

## 🔗 Helpful Links

| What | Link |
|------|------|
| Get API Key | https://resend.com/api-keys |
| Domain Setup | https://resend.com/domains |
| Documentation | https://resend.com/docs |
| Support | support@resend.com |

---

## ⚠️ If It Fails

**Logs show "Sandbox sender detected":**
→ API key not saved in .env OR backend not restarted

**Logs show "Failed (401) unauthorized":**
→ API key is wrong, copy again from Resend dashboard

**OTP still auto-fills:**
→ Clear browser cache: `Ctrl+Shift+Delete`
→ Hard refresh: `Ctrl+Shift+R`

**Email not received:**
→ Check spam folder
→ Try different email address
→ Wait 1-2 minutes

---

## 🎉 That's It!

Once you add the API key and restart, Resend OTP will work perfectly!

**Status:** ⏳ Awaiting your API key setup

---

**Questions?** Check `RESEND_SETUP.md` for detailed guide
