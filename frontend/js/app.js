// app.js - Shared frontend API configuration and helpers

// API Configuration - Dynamic detection
const hostname = window.location.hostname || '127.0.0.1';
const protocol = window.location.protocol;
let API_BASE;
if (hostname === '127.0.0.1' || hostname === 'localhost') {
    API_BASE = 'http://127.0.0.1:5000';
} else if (hostname.includes('devtunnels.ms')) {
    API_BASE = `${protocol}//${hostname}`;
} else {
    API_BASE = `${protocol}//${hostname}:5000`;
}

async function request(path, method='GET', body){
  const opts = { method, headers: {} };
  if (body){ opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const res = await fetch(API_BASE + path, opts);
  return res;
}

export { request };
