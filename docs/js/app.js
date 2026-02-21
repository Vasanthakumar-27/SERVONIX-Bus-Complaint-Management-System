// app.js - Shared frontend API configuration and helpers

// API Configuration — prefer the global set by config.js (loaded first);
// fall back to local detection for contexts where config.js isn't present.
const hostname = window.location.hostname || '127.0.0.1';
const protocol = window.location.protocol;
let API_BASE = window.API_BASE;
if (!API_BASE) {
    if (hostname === '127.0.0.1' || hostname === 'localhost' || hostname === '') {
        API_BASE = 'http://127.0.0.1:5000';
    } else if (hostname.includes('devtunnels.ms')) {
        API_BASE = `${protocol}//${hostname}`;
    } else if (hostname.includes('github.io') || hostname.includes('onrender.com')) {
        API_BASE = 'https://servonix-bus-complaint-management-system.onrender.com';
    } else {
        API_BASE = `${protocol}//${hostname}`;
    }
    window.API_BASE = API_BASE;
}

async function request(path, method='GET', body){
  const opts = { method, headers: {} };
  if (body){ opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const res = await fetch(API_BASE + path, opts);
  return res;
}

export { request };
