/**
 * SERVONIX - API Configuration
 * Sets the backend API base URL used across all pages.
 * Update RENDER_URL when the backend URL changes.
 */
(function () {
    var RENDER_URL = 'https://servonix-bus-complaint-management-system.onrender.com';

    // Use Render backend when served from GitHub Pages or any remote origin.
    // Fall back to localhost when running locally (file:// or localhost).
    var host = window.location.hostname;
    var isLocal = (host === 'localhost' || host === '127.0.0.1' || host === '');

    window.API_BASE = isLocal ? 'http://127.0.0.1:5000' : RENDER_URL;

    console.log('[SERVONIX] API_BASE set to:', window.API_BASE);
})();
