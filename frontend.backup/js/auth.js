// API Base URL - Auto-detect based on current host
var API_BASE;
if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') {
    API_BASE = 'http://127.0.0.1:5000';
} else if (window.location.hostname.includes('devtunnels.ms')) {
    // DevTunnel support for public access
    API_BASE = `https://${window.location.hostname}`;
} else if (window.location.protocol === 'https:') {
    // HTTPS support for production
    API_BASE = `https://${window.location.hostname}:5000`;
} else {
    // Local network HTTP
    API_BASE = `http://${window.location.hostname}:5000`;
}
window.API_BASE = API_BASE;
// Helpful debug: expose and log API base so you can confirm frontend->backend connection
console.log('[auth.js] API_BASE =', API_BASE);

function setToken(t){ localStorage.setItem('token', t); }
function getToken(){ return localStorage.getItem('token'); }
function clearToken(){ localStorage.removeItem('token'); }

async function apiRequest(path, method='GET', body=null, isFormData=false){
  const headers = {};
  const token = getToken();
  if (token) headers['Authorization'] = 'Bearer ' + token;
  
  // Don't set Content-Type for FormData - browser will set it with boundary
  if (body && !isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  
  const res = await fetch(API_BASE + path, { 
    method, 
    headers, 
    body: isFormData ? body : (body ? JSON.stringify(body) : undefined)
  });
  // if unauthorized, clear token
  if (res.status === 401) { clearToken(); }
  return res;
}

async function authRegister(name, email, password){
  try {
    const res = await fetch(API_BASE + '/api/register', {
      method:'POST', 
      headers:{'Content-Type':'application/json'}, 
      body: JSON.stringify({name, email, password})
    });
    const data = await res.json();
    
    if (res.ok && data.token) {
      return data;
    }
    
    return { error: data.error || 'Registration failed' };
  } catch (error) {
    console.error('Registration error:', error);
    return { error: 'Connection error. Please try again.' };
  }
}

async function authLogin(email, password){
  try {
    const res = await fetch(API_BASE + '/api/login', {
      method:'POST', 
      headers:{'Content-Type':'application/json'}, 
      body: JSON.stringify({email, password})
    });
    const data = await res.json();
    
    if (res.ok && data.token) {
      return data;
    }
    
    return { error: data.error || 'Login failed' };
  } catch (error) {
    console.error('Login error:', error);
    return { error: 'Connection error. Please try again.' };
  }
}

// Legacy function for backward compatibility
async function adminLogin(email, password){
  return await authLogin(email, password);
}

// If this file is loaded as a plain <script> (non-module), expose functions on window for compatibility.
// We intentionally avoid using ES module `export` here so HTML pages that include this file
// with a normal <script src="..."> tag won't throw "Unexpected token 'export'".
window.setToken = setToken; 
window.getToken = getToken; 
window.clearToken = clearToken; 
window.apiRequest = apiRequest; 
window.authRegister = authRegister; 
window.authLogin = authLogin; 
window.adminLogin = adminLogin;
