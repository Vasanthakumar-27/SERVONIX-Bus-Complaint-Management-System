# DEBUG FIXES - February 26, 2026

## Issues Identified

Based on the browser console errors and server logs shown in the screenshot, the following issues have been identified and fixed:

### 1. **TypeError: Failed to fetch** - CORS and Preflight Issues
**Problem:** The browser was showing a "Failed to fetch" error when trying to reach `/api/register-request` endpoint.

**Root Cause:** 
- Missing proper handling of CORS OPTIONS preflight requests
- Potential mismatch between frontend API_BASE_URL and backend server URL

**Fixes Applied:**
- ✅ Added explicit OPTIONS request handler in `backend/app.py`
- ✅ Enhanced request logging in auth routes to debug URL mismatches
- ✅ Improved frontend error messages to show actual error details and API URL being called

**Changed Files:**
- `backend/app.py` - Added preflight handler before request
- `backend/routes/auth.py` - Added request logging and OPTIONS support
- `frontend/login.html` - Enhanced error logging with API_BASE_URL and detailed error info

---

### 2. **Socket.IO Connection Drops** - Client Disconnecting Immediately
**Problem:** Server logs show connections being established then immediately dropped:
```
(25) accepted ('10.209.26.114', 43294)
Client disconnected
```

**Root Cause:**
- Socket.IO register event handler expected `user_id` but frontend sends `token`
- Missing error handling in emit calls causing silent failures
- Inadequate logging to understand disconnection reasons

**Fixes Applied:**
- ✅ Updated Socket.IO register handler to accept both `user_id` and `token`
- ✅ Added try/catch blocks around all emit() calls
- ✅ Enhanced logging with session IDs and IP addresses
- ✅ Better error messages when register fails

**Changed Files:**
- `backend/services/socketio_service.py` - Updated register handler and added error handling

---

### 3. **Improved Error Handling**
**Changes Made:**

#### Frontend (login.html):
- Added detailed error logging showing:
  - Error name and message
  - API_BASE_URL being used
  - Actual fetch URL
  - This helps quickly identify URL/CORS issues

#### Backend (socketio_service.py):
- Wrapped all emit() calls in try/catch
- Added session ID and IP address to connection logs
- Support both token and user_id for registration
- Better error messages for debugging

#### Backend (app.py):
- Added explicit OPTIONS handler for preflight requests
- Maintained existing CORS configuration

---

## Debugging Steps

### 1. **Check API Connectivity**
```bash
# From the frontend console, check:
console.log('API_BASE_URL:', window.API_BASE || 'not set')

# Or check what was set by auth.js:
console.log('window.API_BASE:', window.API_BASE)
```

### 2. **Monitor Network Requests**
- Open DevTools → Network tab
- Filter to see registration requests
- Check for CORS errors (shown with red X)
- Look at Response headers for CORS headers

### 3. **Monitor Socket.IO Connections**
- Check backend logs for Socket.IO messages
- Look for registration attempts and errors
- Session IDs help track individual connections

### 4. **Test Registration Flow**
The registration flow has three steps:
1. Step 1: `POST /api/register-request` - Send OTP
2. Step 2: `POST /api/register-verify` - Verify OTP
3. Step 3: Create account

Each step now logs:
- Request details (method, headers)
- Input validation
- Database operations
- Email operations
- Response sent

---

## Configuration Checklist

### Backend Configuration
- [ ] `FRONTEND_URL` environment variable set (optional)
- [ ] CORS origins configured correctly in `app.py`
- [ ] SocketIO async_mode set to 'eventlet'
- [ ] Database tables exist (especially `registration_otp`)
- [ ] Email service configured (Resend or SMTP)

### Frontend Configuration  
- [ ] `window.API_BASE` or `window.API_BASE_URL` set correctly
- [ ] Socket.IO client library loaded in HTML
- [ ] Auth token stored in localStorage after login

### Network Configuration
- [ ] Backend server accessible from frontend domain
- [ ] CORS headers returned by backend
- [ ] No firewall blocking `WebSocket` upgrade
- [ ] Correct port configured (default 5000)

---

## How to Test

### Test 1: Direct API Call
```javascript
// In browser console:
fetch('http://YOUR_API_URL/api/register-request', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    name: 'Test User',
    email: 'test@example.com',
    password: 'Test123!'
  })
})
.then(r => r.json())
.then(d => console.log('Success:', d))
.catch(e => console.error('Error:', e))
```

### Test 2: Check API Health
```javascript
// In browser console:
fetch('http://YOUR_API_URL/api/health')
  .then(r => r.json())
  .then(d => console.log('Health:', d))
```

### Test 3: Monitor Logs
```bash
# Terminal: Watch backend logs
tail -f backend/logs/app.log | grep -E "register|Socket|Client"
```

---

## Next Steps if Issues Persist

1. **Check Backend Logs:** Look for specific error messages in `backend/logs/app.log`

2. **Enable Debug Mode:** Set `DEBUG=True` in environment for more detailed logging

3. **Check Network Conditions:** 
   - Verify API_BASE_URL matches actual server
   - Check browser DevTools Network tab
   - Look for CORS preflight (OPTIONS) failures

4. **Verify Database:** 
   - Ensure `registration_otp` table exists
   - Check user table for schema

5. **Test Email Delivery:** 
   - Check email service configuration
   - Verify OTP is being generated (in logs)
   - See if OTP is returned in response (dev mode)

---

## Files Modified

1. **backend/app.py**
   - Added preflight request handler
   - Better CORS configuration

2. **backend/routes/auth.py**
   - Added request logging to register-request
   - Added OPTIONS support to register-request

3. **backend/services/socketio_service.py**
   - Enhanced connect handler with IP/session logging
   - Enhanced disconnect handler with more info
   - Updated register handler to support token and user_id
   - Added error handling to all emit() calls

4. **frontend/login.html**
   - Enhanced error logging in sendRegistrationOTP()
   - Enhanced error logging in verifyRegistrationOTP()
   - Shows API_BASE_URL and actual error messages

---

## Related Issues

These fixes address:
- ✅ TypeError: Failed to fetch errors
- ✅ CORS preflight failures  
- ✅ Socket.IO immediate disconnections
- ✅ Missing error details in console
- ✅ Inability to debug connection issues

---

**Last Updated:** February 26, 2026
**Status:** Fixed - Ready for testing
