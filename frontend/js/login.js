// login.js: Handles login form and redirects to correct dashboard

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('loginForm');
    if (!form) return;
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        if (!email || !password) {
            showToast('Please enter email and password.', 'error');
            return;
        }
        const result = await window.authLogin(email, password);
        if (result.error) {
            showToast(result.error, 'error');
            return;
        }
        // Store token and user info
        window.setToken(result.token);
        if (result.role) localStorage.setItem('user_role', result.role);
        if (result.name) localStorage.setItem('user_name', result.name);
        if (result.email) localStorage.setItem('user_email', result.email);
        // Redirect based on role
        if (result.role === 'user') {
            window.location.href = 'user_dashboard.html';
        } else if (result.role === 'admin') {
            window.location.href = 'admin_dashboard.html';
        } else if (result.role === 'head') {
            window.location.href = 'head_dashboard.html';
        } else {
            showToast('Unknown role. Contact support.', 'error');
        }
    });
});

function showToast(msg, type) {
    let toast = document.createElement('div');
    toast.className = 'toast ' + (type || 'info');
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3000);
}
