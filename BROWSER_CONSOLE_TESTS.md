# Browser Console Testing Guide - Quick Start

Copy and paste these commands into your browser's DevTools console to test the fixes.

## Step 1: Check API Configuration
```javascript
console.log('=== API Configuration ===');
console.log('API_BASE:', window.API_BASE);
console.log('Current URL:', window.location.href);
```

## Step 2: Test API Health
```javascript
fetch('http://127.0.0.1:5000/api/health')
  .then(r => {
    console.log('✓ Health Check - Status:', r.status);
    return r.json();
  })
  .then(d => console.log('✓ Response:', d))
  .catch(e => console.error('✗ Error:', e.message));
```

## Step 3: Test CORS Preflight
```javascript
fetch('http://127.0.0.1:5000/api/register-request', {
  method: 'OPTIONS',
  headers: {
    'Access-Control-Request-Method': 'POST',
    'Access-Control-Request-Headers': 'Content-Type'
  }
})
.then(r => {
  console.log('✓ Preflight Status:', r.status);
  console.log('✓ CORS Headers:');
  ['access-control-allow-origin', 'access-control-allow-methods'].forEach(h => {
    console.log(`  ${h}:`, r.headers.get(h));
  });
})
.catch(e => console.error('✗ Preflight Error:', e.message));
```

## Step 4: Monitor Registration Request
```javascript
const testData = {
  name: 'Debug Test User',
  email: 'debugtest@example.com',
  password: 'TestPassword123!'
};

console.log('Sending registration request...');
fetch('http://127.0.0.1:5000/api/register-request', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(testData)
})
.then(r => {
  console.log('✓ Registration Status:', r.status);
  console.log('✓ Response Headers:', {
    'content-type': r.headers.get('content-type'),
    'access-control-allow-origin': r.headers.get('access-control-allow-origin')
  });
  return r.json();
})
.then(d => {
  console.log('✓ Response Data:', d);
  if (d.dev_otp) {
    console.warn('⚠ Dev OTP (email service not working):', d.dev_otp);
  }
  if (d.registration_token) {
    console.log('✓ Registration token received');
    window.testToken = d.registration_token;
  }
})
.catch(e => console.error('✗ Error:', e.message));
```

## Step 5: Monitor WebSocket Connection
```javascript
console.log('=== WebSocket / Socket.IO ===');

// Check if Socket.IO library is loaded
if (typeof io !== 'undefined') {
  console.log('✓ Socket.IO library loaded');
  
  // Create a test connection
  const socket = io('http://127.0.0.1:5000', {
    transports: ['polling', 'websocket'],
    reconnection: true
  });
  
  socket.on('connect', () => {
    console.log('✓ WebSocket Connected - Session ID:', socket.id);
    
    // Try to register
    socket.emit('register', { 
      user_id: 'test-user-123' 
    });
  });
  
  socket.on('register_response', (data) => {
    console.log('✓ Register Response:', data);
  });
  
  socket.on('disconnect', () => {
    console.log('⚠ WebSocket Disconnected');
  });
  
  socket.on('error', (error) => {
    console.error('✗ WebSocket Error:', error);
  });
  
  // Store for later cleanup
  window.testSocket = socket;
} else {
  console.warn('⚠ Socket.IO library not loaded');
}
```

## Step 6: Complete Registration Flow
```javascript
async function testCompleteRegistration() {
  console.log('=== Testing Complete Registration Flow ===\n');
  
  const email = 'test-' + Date.now() + '@example.com';
  const testData = {
    name: 'Test User ' + Date.now(),
    email: email,
    password: 'TestPassword123!'
  };
  
  try {
    // Step 1: Request OTP
    console.log('Step 1: Requesting OTP...');
    const requestRes = await fetch('http://127.0.0.1:5000/api/register-request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(testData)
    });
    
    const requestData = await requestRes.json();
    console.log('✓ OTP Request Status:', requestRes.status);
    console.log('✓ Response:', requestData);
    
    if (!requestRes.ok) {
      console.error('✗ OTP Request Failed:', requestData.error);
      return;
    }
    
    // Get OTP from response
    let otp = requestData.dev_otp;
    if (!otp) {
      console.warn('⚠ No OTP in response. Email should have been sent to:', email);
      otp = prompt('Enter OTP (or "skip" to skip verification)');
      if (otp === 'skip') {
        console.log('Skipping verification test');
        return;
      }
    } else {
      console.log('✓ OTP from response:', otp);
    }
    
    // Step 2: Verify OTP
    console.log('\nStep 2: Verifying OTP...');
    const verifyRes = await fetch('http://127.0.0.1:5000/api/register-verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email,
        otp: otp,
        registration_token: requestData.registration_token || ''
      })
    });
    
    const verifyData = await verifyRes.json();
    console.log('✓ Verify Status:', verifyRes.status);
    console.log('✓ Response:', verifyData);
    
    if (verifyRes.ok) {
      console.log('✅ Registration successful!');
      console.log('User details:', verifyData.user);
    } else {
      console.error('✗ Verification failed:', verifyData.error);
    }
    
  } catch (error) {
    console.error('✗ Error during test:', error.message);
  }
}

// Run the test
testCompleteRegistration();
```

## Step 7: Check Logs

### What to look for in backend logs:
```
✓ [register-request] Received request - method: POST
✓ [register-request] Request data keys: ['name', 'email', 'password']
✓ Registration OTP sent to test@example.com
✓ Client connected - IP: 127.0.0.1, Session ID: xxxxx
✓ User 123 registered for real-time updates
```

### What to look for in browser console:
```
✓ API_BASE_URL = http://127.0.0.1:5000
✓ Verification code sent to your email!
✓ WebSocket connected: xxxxx
✓ User registered for real-time updates
```

## Troubleshooting Commands

### If you see "Failed to fetch":
```javascript
console.log('API_BASE_URL:', window.API_BASE);
console.log('Trying to fetch:', window.API_BASE + '/api/register-request');

// Test with full URL
fetch('http://127.0.0.1:5000/api/health')
  .then(r => console.log('Health check:', r.status))
  .catch(e => console.error('Cannot reach backend:', e.message));
```

### If Socket.IO doesn't connect:
```javascript
console.log('Socket.IO available?', typeof io !== 'undefined');
console.log('Token in storage?', localStorage.getItem('token') ? 'yes' : 'no');

// Try manual connection
const socket = io('http://127.0.0.1:5000');
socket.on('connect_error', (e) => console.error('Connection Error:', e));
```

### If email says "dev_otp":
```javascript
// Email service is not configured - this is expected
// The OTP will be shown directly in the response
console.log('Email service status: Not configured for this environment');
console.log('Dev OTP shown in response - use this for testing');
```

## Quick Copy-Paste Test Blocks

### Test 1: Just Check API
```javascript
fetch('http://127.0.0.1:5000/api/health').then(r => r.json()).then(d => console.log('API OK:', d)).catch(e => console.error('API Error:', e.message));
```

### Test 2: Just Check WebSocket
```javascript
const s = io('http://127.0.0.1:5000'); s.on('connect', () => console.log('Connected:', s.id)); s.on('error', (e) => console.error('Error:', e));
```

### Test 3: Just Test Registration
```javascript
fetch('http://127.0.0.1:5000/api/register-request', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: 'Test', email: 'test@test.com', password: 'Test123!'})}).then(r => r.json()).then(d => console.log(d)).catch(e => console.error(e.message));
```

---

## Notes

- Replace `http://127.0.0.1:5000` with your actual backend URL
- Commands can be run multiple times
- Check browser console for detailed error messages
- Check backend logs in `backend/logs/app.log` for server-side issues
- For production, use HTTPS instead of HTTP
- Remove test data after testing

---

**Testing Complete!** ✓

If all commands show ✓, the fixes are working correctly.
