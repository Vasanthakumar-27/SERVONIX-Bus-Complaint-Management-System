// user_dashboard.js - Complete User Dashboard Implementation

console.log('[USER DASHBOARD] Script loaded');

// Helper: Escape HTML to prevent XSS
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Helper function to get API base URL
function getAPIBase() {
    if (window.API_BASE) return window.API_BASE;
    
    if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') {
        return 'http://127.0.0.1:5000';
    } else {
        return `http://${window.location.hostname}:5000`;
    }
}

// Helper function to get token (fallback if auth.js not loaded)
function getToken() {
    return localStorage.getItem('token');
}

// Helper function for API requests (fallback if auth.js not loaded)
async function apiRequest(path, method='GET', body=null, isFormData=false) {
    
    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    
    if (body && !isFormData) {
        headers['Content-Type'] = 'application/json';
    }
    
    const res = await fetch(getAPIBase() + path, { 
        method, 
        headers, 
        body: isFormData ? body : (body ? JSON.stringify(body) : undefined)
    });
    
    // Handle 401 errors
    if (res.status === 401) {
        console.error('[USER DASHBOARD] 401 Unauthorized - Session expired');
        localStorage.removeItem('token');
        sessionStorage.setItem('fromSplash', 'true');
        window.location.href = '/html/login.html';
    }
    
    return res;
}

// Global state
const state = {
    currentUser: null,
    draftComplaint: null,
    autosaveInterval: null
};

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', async function() {
    console.log('[USER DASHBOARD] Initializing...');
    
    // Load user data
    await loadUserData();
    
    // Setup navigation
    setupNavigation();
    
    // Setup autosave for complaint draft
    setupAutosave();
    
    // Show create complaint page by default
    showSection('create-complaint');
    
    // Setup event listeners
    setupEventListeners();
    
    console.log('[USER DASHBOARD] Initialization complete');
});

// Load current user data
async function loadUserData() {
    const token = getToken();
    if (!token) {
        console.error('[USER] No token found - redirecting to login');
        window.location.href = '/html/login.html';
        return;
    }
    
    try {
        const res = await apiRequest('/api/profile');
        
        if (res.ok) {
            state.currentUser = await res.json();
            console.log('[USER] Loaded:', state.currentUser);
            
            // Update UI with user info
            const userName = document.getElementById('userName');
            if (userName) userName.textContent = state.currentUser.name;
            
            const userEmail = document.getElementById('userEmail');
            if (userEmail) userEmail.textContent = state.currentUser.email;
        } else if (res.status === 401) {
            console.error('[USER] 401 - Token expired or invalid');
            localStorage.removeItem('token');
            window.location.href = '/html/login.html';
        } else {
            console.error('[USER] Failed to load user data:', res.status);
            localStorage.removeItem('token');
            window.location.href = '/html/login.html';
        }
    } catch (error) {
        console.error('[USER] Error:', error);
    }
}

// Setup navigation between sections
function setupNavigation() {
    const navLinks = document.querySelectorAll('[data-section]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.getAttribute('data-section');
            showSection(section);
            
            // Update active state
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// Show specific section
function showSection(sectionId) {
    const sections = document.querySelectorAll('.page');
    sections.forEach(section => {
        section.classList.remove('active');
    });
    
    const targetSection = document.getElementById(sectionId + 'Page');
    if (targetSection) {
        targetSection.classList.add('active');
        
        // Load data for specific sections
        if (sectionId === 'complaints-history') {
            loadComplaintsHistory();
        } else if (sectionId === 'create-complaint') {
            loadDraftComplaint();
        }
    }
}

// Setup autosave for complaint draft
function setupAutosave() {
    // Autosave every 15 seconds
    state.autosaveInterval = setInterval(saveDraftComplaint, 15000);
    
    // Save on page unload
    window.addEventListener('beforeunload', saveDraftComplaint);
}

// Save complaint draft to localStorage
function saveDraftComplaint() {
    const form = document.getElementById('createComplaintForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const draft = {};
    
    for (let [key, value] of formData.entries()) {
        if (value) draft[key] = value;
    }
    
    if (Object.keys(draft).length > 0) {
        localStorage.setItem('complaint_draft', JSON.stringify(draft));
        console.log('[DRAFT] Saved');
    }
}

// Load complaint draft from localStorage
function loadDraftComplaint() {
    const draftJson = localStorage.getItem('complaint_draft');
    if (!draftJson) return;
    
    try {
        const draft = JSON.parse(draftJson);
        const form = document.getElementById('createComplaintForm');
        if (!form) return;
        
        Object.keys(draft).forEach(key => {
            const input = form.elements[key];
            if (input) input.value = draft[key];
        });
        
        showToast('Draft restored', 'info');
        console.log('[DRAFT] Loaded');
    } catch (error) {
        console.error('[DRAFT] Error loading:', error);
    }
}

// Clear complaint draft
function clearDraftComplaint() {
    localStorage.removeItem('complaint_draft');
    console.log('[DRAFT] Cleared');
}

// Setup event listeners
function setupEventListeners() {
    // District change -> load routes
    const districtSelect = document.getElementById('complaintDistrict');
    if (districtSelect) {
        districtSelect.addEventListener('change', function() {
            const districtId = this.value;
            if (districtId) {
                loadRoutes(districtId);
            } else {
                const routeSelect = document.getElementById('complaintRoute');
                if (routeSelect) {
                    routeSelect.innerHTML = '<option value="">Select Route</option>';
                    routeSelect.disabled = true;
                }
            }
        });
    }
    
    // Route change -> load buses
    const routeSelect = document.getElementById('complaintRoute');
    if (routeSelect) {
        routeSelect.addEventListener('change', function() {
            const routeId = this.value;
            if (routeId) {
                loadBuses(routeId);
            }
        });
    }
    
    // Bus number input -> auto-suggest
    const busNumberInput = document.getElementById('complaintBusNumber');
    if (busNumberInput) {
        busNumberInput.addEventListener('blur', function() {
            autoSuggestBus(this.value);
        });
    }
    
    // Create complaint form submit
    const createForm = document.getElementById('createComplaintForm');
    if (createForm) {
        createForm.addEventListener('submit', handleCreateComplaint);
    }
    
    // Feedback form submit
    const feedbackForm = document.getElementById('feedbackForm');
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', handleSubmitFeedback);
    }
    
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            localStorage.removeItem('token');
            window.location.href = '/html/login.html';
        });
    }
}

// Handle create complaint submission
async function handleCreateComplaint(e) {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Show confirmation modal first
    const confirmed = await showConfirmModal(
        'Submit Complaint',
        'Are you sure you want to submit this complaint? You can edit it within 5 minutes after submission.'
    );
    
    if (!confirmed) return;
    
    // Disable submit button and show spinner
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
    
    const formData = new FormData(form);
    try {
        const res = await apiRequest('/api/complaints', 'POST', formData, true);
        
        if (res.ok) {
            const result = await res.json();
            
            // Clear draft
            clearDraftComplaint();
            
            // Reset form
            form.reset();
            
            // Show success message with complaint ID
            showToast(`Complaint #${result.id} submitted successfully!`, 'success');
            
            // Show download receipt option
            showSuccessModal(result.id);
            
            console.log('[COMPLAINT] Created:', result.id);
        } else {
            const error = await res.json();
            showToast(error.error || 'Failed to submit complaint', 'error');
        }
    } catch (error) {
        console.error('[COMPLAINT] Error:', error);
        showToast('Network error. Please try again.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Complaint';
    }
}

// Load complaints history
async function loadComplaintsHistory(filters = {}) {
    const page = filters.page || 1;
    const status = filters.status || '';
    const search = filters.search || '';
    
    const params = new URLSearchParams({
        page,
        per_page: 20
    });
    
    if (status) params.append('status', status);
    if (search) params.append('q', search);
    
    try {
        const res = await apiRequest(`/api/user/complaints?${params}`);
        
        if (res.ok) {
            const data = await res.json();
            renderComplaintsTable(data.complaints);
            renderPagination(data.page, data.total_pages);
            console.log('[HISTORY] Loaded:', data.complaints.length, 'complaints');
        }
    } catch (error) {
        console.error('[HISTORY] Error:', error);
    }
}

// Render complaints table
function renderComplaintsTable(complaints) {
    const tbody = document.getElementById('complaintsTableBody');
    if (!tbody) return;
    
    if (complaints.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px;">
                    <i class="fas fa-inbox" style="font-size: 48px; color: #999; margin-bottom: 10px;"></i>
                    <p>No complaints found</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = complaints.map(complaint => `
        <tr>
            <td>#${complaint.id}</td>
            <td>${formatDate(complaint.created_at)}</td>
            <td>${complaint.district_name || 'N/A'}</td>
            <td>${complaint.route_name || 'N/A'}</td>
            <td>${complaint.bus_number}</td>
            <td>${complaint.category}</td>
            <td>${getStatusBadge(complaint.status)}</td>
            <td>
                <button class="btn-icon" onclick="viewComplaint(${complaint.id})" title="View">
                    <i class="fas fa-eye"></i>
                </button>
                ${complaint.edit_allowed ? `
                    <button class="btn-icon" onclick="editComplaint(${complaint.id})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                ` : ''}
                ${complaint.edit_allowed ? `
                    <button class="btn-icon btn-danger" onclick="deleteComplaint(${complaint.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                ` : ''}
            </td>
        </tr>
    `).join('');
}

// Render pagination
function renderPagination(currentPage, totalPages) {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;
    
    let html = '';
    
    if (currentPage > 1) {
        html += `<button onclick="loadComplaintsHistory({page: ${currentPage - 1}})">Previous</button>`;
    }
    
    html += `<span>Page ${currentPage} of ${totalPages}</span>`;
    
    if (currentPage < totalPages) {
        html += `<button onclick="loadComplaintsHistory({page: ${currentPage + 1}})">Next</button>`;
    }
    
    pagination.innerHTML = html;
}

// View complaint details
async function viewComplaint(id) {
    
    try {
        const res = await apiRequest(`/api/complaints/${id}`);
        
        if (res.ok) {
            const complaint = await res.json();
            showComplaintModal(complaint);
        }
    } catch (error) {
        console.error('[VIEW] Error:', error);
    }
}

// Edit complaint
async function editComplaint(id) {
    // Load complaint data and populate form
    
    try {
        const res = await apiRequest(`/api/complaints/${id}`);
        
        if (res.ok) {
            const complaint = await res.json();
            
            // Switch to create page and populate with complaint data
            showSection('create-complaint');
            
            // Populate form fields
            document.getElementById('complaintId').value = id;
            document.getElementById('complaintDescription').value = complaint.description;
            document.getElementById('complaintCategory').value = complaint.category;
            document.getElementById('complaintPriority').value = complaint.priority;
            document.getElementById('complaintBusNumber').value = complaint.bus_number;
            
            showToast('Editing complaint - submit to save changes', 'info');
        }
    } catch (error) {
        console.error('[EDIT] Error:', error);
    }
}

// Delete complaint
async function deleteComplaint(id) {
    if (!confirm('Are you sure you want to delete this complaint?')) return;
    
    try {
        const res = await apiRequest(`/api/complaints/${id}`, 'DELETE');
        
        if (res.ok) {
            showToast('Complaint deleted successfully', 'success');
            loadComplaintsHistory();
        } else {
            const error = await res.json();
            showToast(error.error || 'Failed to delete complaint', 'error');
        }
    } catch (error) {
        console.error('[DELETE] Error:', error);
        showToast('Network error', 'error');
    }
}

// Submit feedback
async function handleSubmitFeedback(e) {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Get form values
    const rating = form.querySelector('input[name="rating"]:checked')?.value;
    const message = form.querySelector('textarea[name="message"]')?.value?.trim();
    
    if (!rating) {
        showToast('Please select a rating', 'warning');
        return;
    }
    
    if (!message || message.length < 1) {
        showToast('Please enter a feedback message', 'warning');
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    
    try {
        const res = await apiRequest('/api/feedback', 'POST', {
            rating: parseInt(rating),
            message: message
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showToast('Feedback submitted successfully!', 'success');
            form.reset();
        } else {
            showToast(data.error || 'Failed to submit feedback', 'error');
        }
    } catch (error) {
        console.error('[FEEDBACK] Error:', error);
        showToast('Network error: ' + error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Feedback';
    }
}

// Utility functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge badge-warning">Pending</span>',
        'in_progress': '<span class="badge badge-info">In Progress</span>',
        'resolved': '<span class="badge badge-success">Resolved</span>'
    };
    return badges[status] || '<span class="badge badge-secondary">Unknown</span>';
}

// Toast notification system
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 100);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Confirmation modal
function showConfirmModal(title, message) {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>${title}</h3>
                <p>${message}</p>
                <div class="modal-actions">
                    <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove(); window.modalResolve(false)">Cancel</button>
                    <button class="btn-primary" onclick="this.closest('.modal-overlay').remove(); window.modalResolve(true)">Confirm</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        window.modalResolve = resolve;
    });
}

// Delete confirmation modal with reason input
function showDeleteModal() {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Delete Complaint</h3>
                <p>Please provide a reason for deleting this complaint:</p>
                <textarea id="deleteReason" rows="3" placeholder="Enter reason..." style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px;"></textarea>
                <div class="modal-actions">
                    <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove(); window.modalResolve(null)">Cancel</button>
                    <button class="btn-danger" onclick="const reason = document.getElementById('deleteReason').value.trim(); if (!reason) { alert('Reason is required'); return; } this.closest('.modal-overlay').remove(); window.modalResolve(reason)">Delete</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        window.modalResolve = resolve;
    });
}

// Success modal with download receipt option
function showSuccessModal(complaintId) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <div style="text-align: center;">
                <i class="fas fa-check-circle" style="font-size: 64px; color: #10b981; margin-bottom: 20px;"></i>
                <h3>Complaint Submitted Successfully!</h3>
                <p style="font-size: 24px; font-weight: 600; margin: 20px 0;">Complaint ID: #${complaintId}</p>
                <p>Your complaint has been received and will be processed soon.</p>
                <div class="modal-actions" style="margin-top: 30px;">
                    <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">Close</button>
                    <button class="btn-primary" onclick="downloadReceipt(${complaintId}); this.closest('.modal-overlay').remove()">
                        <i class="fas fa-download"></i> Download Receipt
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// Download complaint receipt
function downloadReceipt(complaintId) {
    showToast('Generating receipt...', 'info');
    window.open(`${getAPIBase()}/api/complaints/${complaintId}/receipt`, '_blank');
}

// Show complaint details modal
function showComplaintModal(complaint) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 800px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3>Complaint #${complaint.id}</h3>
                <button onclick="this.closest('.modal-overlay').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <p><strong>Status:</strong> ${getStatusBadge(complaint.status)}</p>
                    <p><strong>Priority:</strong> ${complaint.priority}</p>
                    <p><strong>Category:</strong> ${complaint.category}</p>
                    <p><strong>District:</strong> ${complaint.district_name || 'N/A'}</p>
                    <p><strong>Route:</strong> ${complaint.route_name || 'N/A'}</p>
                </div>
                <div>
                    <p><strong>Bus Number:</strong> ${complaint.bus_number}</p>
                    <p><strong>Bus Name:</strong> ${complaint.bus_name || 'N/A'}</p>
                    <p><strong>Created:</strong> ${formatDate(complaint.created_at)}</p>
                    <p><strong>Assigned Admin:</strong> ${complaint.admin_name || 'Not assigned'}</p>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <p><strong>Description:</strong></p>
                <p style="background: #f9fafb; padding: 15px; border-radius: 8px; margin-top: 10px;">${complaint.description}</p>
            </div>
            ${complaint.media_files && complaint.media_files.length > 0 ? `
                <div style="margin-top: 20px;">
                    <p><strong>Attachments:</strong></p>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px;">
                        ${complaint.media_files.map(file => `
                            <div style="border: 1px solid #ddd; padding: 10px; border-radius: 8px;">
                                <i class="fas fa-file"></i> ${file.file_name}
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            <div class="modal-actions" style="margin-top: 30px;">
                <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">Close</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// Make functions globally accessible
window.viewComplaint = viewComplaint;
window.editComplaint = editComplaint;
window.deleteComplaint = deleteComplaint;
window.downloadReceipt = downloadReceipt;
window.loadComplaintsHistory = loadComplaintsHistory;

// Real-time auto-refresh functionality
let autoRefreshInterval = null;

function startAutoRefresh() {
    // Clear existing interval if any
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    // Initial load
    loadComplaintsHistory();
    
    // Auto-refresh every 10 seconds
    autoRefreshInterval = setInterval(() => {
        console.log('[AUTO-REFRESH] Updating complaints data...');
        loadComplaintsHistory();
        
        // Also refresh user data to catch any profile updates
        loadUserData().catch(err => console.error('[AUTO-REFRESH] User data error:', err));
    }, 10000);
    
    console.log('[AUTO-REFRESH] Started - refreshing every 10 seconds');
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        console.log('[AUTO-REFRESH] Stopped');
    }
}

// Start auto-refresh when complaints history is visible
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.target.classList.contains('active')) {
            const section = mutation.target.getAttribute('id') || mutation.target.getAttribute('data-section');
            if (section === 'complaints-history') {
                startAutoRefresh();
            } else {
                stopAutoRefresh();
            }
        }
    });
});

// Observe section changes
document.addEventListener('DOMContentLoaded', () => {
    const sections = document.querySelectorAll('.page');
    sections.forEach(section => {
        observer.observe(section, { attributes: true, attributeFilter: ['class'] });
    });
    
    // Start auto-refresh if complaints page is initially active
    const complaintsSection = document.getElementById('complaintsPage');
    if (complaintsSection && complaintsSection.classList.contains('active')) {
        startAutoRefresh();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});
