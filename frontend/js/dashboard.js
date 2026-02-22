// Dashboard JavaScript - Real-time updates and management
// Auto-detect API base based on current host
let API_BASE;
const hostname = window.location.hostname || '127.0.0.1';
const protocol = window.location.protocol;

if (hostname === '127.0.0.1' || hostname === 'localhost') {
    API_BASE = 'http://127.0.0.1:5000';
} else if (hostname.includes('devtunnels.ms')) {
    // DevTunnel support - no port needed
    API_BASE = `${protocol}//${hostname}`;
} else if (protocol === 'https:') {
    // HTTPS production
    API_BASE = `https://${hostname}:5000`;
} else {
    // Local network HTTP
    API_BASE = `http://${hostname}:5000`;
}
console.log('[dashboard.js] API_BASE =', API_BASE);

// Helper: Escape HTML to prevent XSS
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

let refreshInterval;
let currentUser = null;
const adminSummaryCache = new Map();
const adminMessagesCache = new Map();

// Helper: Detect if any 3-dot dropdown is open
function isAnyDropdownOpen() {
    // Adjust selector as per your dropdown implementation
    // Example for Bootstrap: '.dropdown-menu.show'
    // Example for custom: '.three-dot-menu.open'
    return !!document.querySelector('.dropdown-menu.show, .three-dot-menu.open, .dropdown-menu[aria-expanded="true"]');
}

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', function() {
    // Show loader initially
    showDashboardLoader();
    
    // Check authentication
    const token = localStorage.getItem('token');
    const userRole = localStorage.getItem('user_role');
    const userName = localStorage.getItem('user_name');
    
    console.log('Dashboard init - Token:', token ? 'exists' : 'missing');
    console.log('Dashboard init - Role:', userRole);
    console.log('Dashboard init - Name:', userName);
    
    if (!token) {
        console.error('❌ No token found - User needs to login');
        alert('Please login first!');
        window.location.href = 'login.html';
        return;
    }
    
    if (userRole !== 'head') {
        console.error('❌ User role is not head:', userRole);
        alert('Access denied! This dashboard is for HEAD users only.');
        window.location.href = 'login.html';
        return;
    }
    
    console.log('✅ Authentication validated - Loading dashboard...');
    
    currentUser = {
        name: userName,
        role: userRole,
        email: localStorage.getItem('user_email'),
        id: localStorage.getItem('user_id')
    };
    
    const welcomeTextEl = document.getElementById('welcomeText');
    if (welcomeTextEl) {
        welcomeTextEl.textContent = `Welcome, ${userName || 'Head Administrator'}`;
    }
    
    // Initial data load
    loadAllData().then(() => {
        // Hide loader after data is loaded
        setTimeout(() => {
            hideDashboardLoader();
        }, 800);
    });
    
    // Set up auto-refresh every 5 seconds - only refresh real-time data
    refreshInterval = setInterval(() => {
        if (!isAnyDropdownOpen()) {
            loadRealTimeData();  // Changed from loadAllData() to only refresh real-time stats
        } else {
            console.log('[Auto-Refresh] Skipped due to open dropdown menu');
        }
    }, 5000);
    
    // Set up event listeners
    setupEventListeners();
});

// Setup all event listeners
function setupEventListeners() {
    // Sidebar navigation
    document.querySelectorAll('.sidebar-item[data-section]').forEach(item => {
        item.addEventListener('click', function() {
            const section = this.dataset.section;
            switchSection(section);
        });
    });
    
    // Status filter for complaints
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', loadComplaints);
    }
    
    // Search complaints (with null check)
    const searchComplaints = document.getElementById('searchComplaints');
    if (searchComplaints) {
        searchComplaints.addEventListener('input', debounce(loadComplaints, 500));
    }
}

// Switch between sections
function switchSection(section) {
    // Show loader when switching sections
    showDashboardLoader();
    
    // Update sidebar
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.remove('active');
    });
    const sidebarItem = document.querySelector(`.sidebar-item[data-section="${section}"]`);
    if (sidebarItem) {
        sidebarItem.classList.add('active');
    }
    
    // Update content
    document.querySelectorAll('.content-section').forEach(sec => {
        sec.classList.remove('active');
    });
    const sectionEl = document.getElementById(section);
    if (sectionEl) {
        sectionEl.classList.add('active');
    }
    
    // Load section-specific data
    loadSectionData(section);
    
    // Hide loader after a short delay
    setTimeout(() => {
        hideDashboardLoader();
    }, 500);
}

// Show dashboard loader
function showDashboardLoader() {
    const loader = document.getElementById('dashboardLoader');
    if (loader) {
        loader.classList.remove('hidden');
    }
}

// Hide dashboard loader
function hideDashboardLoader() {
    const loader = document.getElementById('dashboardLoader');
    if (loader) {
        loader.classList.add('hidden');
    }
}

// Make loader functions globally accessible
window.showDashboardLoader = showDashboardLoader;
window.hideDashboardLoader = hideDashboardLoader;

// Load section-specific data
function loadSectionData(section) {
    switch(section) {
        case 'admin-management':
            loadAdminList();
            break;
        case 'complaints':
            loadComplaints();
            break;
        case 'activities':
            loadAdminActivities();
            break;
        case 'feedback':
            if (typeof window.loadAllFeedback === 'function') {
                window.loadAllFeedback();
            }
            break;
        case 'user-logs':
            loadUserLogs();
            break;
        case 'users':
            loadAllUsers();
            break;
        case 'online-users':
            loadOnlineUsers();
            break;
    }
}

// Load all dashboard data
async function loadAllData() {
    console.log('🔄 Loading all dashboard data...');
    try {
        await Promise.all([
            loadDashboardStats(),
            loadRecentActivity()
        ]);
        updateLastUpdateTime();
        console.log('✅ Dashboard data loaded successfully');
    } catch (error) {
        console.error('❌ Error loading data:', error);
        showToast('Connection Error', 'Failed to update data', 'danger');
    }
}

// Load only real-time data (for auto-refresh) - lightweight
async function loadRealTimeData() {
    try {
        // Only refresh stats and recent activity, not full lists
        await Promise.all([
            loadDashboardStats(),
            loadRecentActivity(),
            // Also refresh districts and routes for real-time updates
            loadDistricts().catch(() => {}),
            loadRoutes().catch(() => {})
        ]);
        updateLastUpdateTime();
    } catch (error) {
        // Silent fail for background refresh
        console.error('Background refresh failed:', error);
    }
}

// Logout function
function logout() {
    console.log('Logging out...');
    localStorage.removeItem('token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_email');
    localStorage.removeItem('user_id');
    window.location.href = 'login.html';
}

// Make functions globally accessible
window.logout = logout;

// Load dashboard statistics
async function loadDashboardStats() {
    console.log('📊 Loading dashboard stats...');
    try {
        const response = await apiRequest('/api/dashboard/stats', 'GET');
        console.log('Stats response:', response);
        if (response && response.ok) {
            const data = await response.json();
            const stats = data.stats || data;
            // Animate counter updates (with null checks)
            if (document.getElementById('totalUsers')) {
                console.log('Updating totalUsers:', stats.total_users);
                animateCounter('totalUsers', stats.total_users || 0);
            }
            if (document.getElementById('activeAdmins')) animateCounter('activeAdmins', stats.active_admins || 0);
            if (document.getElementById('totalComplaints')) animateCounter('totalComplaints', stats.total_complaints || 0);
            if (document.getElementById('pendingComplaints')) animateCounter('pendingComplaints', stats.pending_complaints || 0);
            // Update overview section (with null checks)
            const overviewPending = document.getElementById('overviewPending');
            const overviewInProgress = document.getElementById('overviewInProgress');
            const overviewResolved = document.getElementById('overviewResolved');
            if (overviewPending) overviewPending.textContent = stats.pending_complaints || 0;
            if (overviewInProgress) overviewInProgress.textContent = stats.inprogress_complaints || 0;
            if (overviewResolved) overviewResolved.textContent = stats.resolved_complaints || 0;
        } else {
            console.error('Failed to load stats - response not ok:', response);
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Feedback delete logic (user and head can delete)
async function deleteFeedback(feedbackId) {
    try {
        const response = await apiRequest(`/api/feedback/${feedbackId}`, 'DELETE');
        if (response.ok) {
            showToast('Success', 'Feedback deleted', 'success');
            // Reload feedback list
            loadUserFeedbacks();
        } else {
            showToast('Error', 'Failed to delete feedback', 'danger');
        }
    } catch (error) {
        showToast('Error', 'Connection error', 'danger');
    }
// removed stray closing brace
}

// Alias for loadDashboardStats
const loadStatistics = loadDashboardStats;

// Animate counter changes
function animateCounter(elementId, newValue) {
    const element = document.getElementById(elementId);
    const currentValue = parseInt(element.textContent) || 0;
    
    if (currentValue === newValue) return;
    
    const duration = 500;
    const steps = 20;
    const increment = (newValue - currentValue) / steps;
    const stepDuration = duration / steps;
    
    let current = currentValue;
    let step = 0;
    
    const timer = setInterval(() => {
        step++;
        current += increment;
        element.textContent = Math.round(current);
        
        if (step >= steps) {
            clearInterval(timer);
            element.textContent = newValue;
        }
    }, stepDuration);
    
    // Add pulse animation
    element.style.transform = 'scale(1.1)';
    setTimeout(() => {
        element.style.transform = 'scale(1)';
    }, 200);
}

// Load recent activity preview
async function loadRecentActivity() {
    console.log('📋 Loading recent activity...');
    try {
        const response = await apiRequest('/api/dashboard/admin_logs?limit=3', 'GET');
        console.log('Recent activity response:', response);
        
        if (response && response.ok) {
            const data = await response.json();
            console.log('Recent activity data:', data);
            const previewEl = document.getElementById('recentActivityPreview');
            if (previewEl) {
                if (data.logs && data.logs.length > 0) {
                    const html = data.logs.map(log => `
                        <div class="mb-2">
                            <small class="text-muted">${formatTimeAgo(log.created_at)}</small>
                            <br>
                            <strong>${log.admin_name}</strong>: ${log.description || log.action}
                        </div>
                    `).join('');
                    previewEl.innerHTML = html;
                } else {
                    previewEl.innerHTML = '<p class="text-muted">No recent activity</p>';
                }
            }
        }
    } catch (error) {
        console.error('Error loading recent activity:', error);
    }
}

// Load admin list
async function loadAdminList() {
    try {
        const response = await apiRequest('/api/head/admins', 'GET');
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to load admins');
        }

        const data = await response.json();
        const admins = Array.isArray(data) ? data : data.admins || [];
        const tbody = document.getElementById('adminTableBody');

        if (!tbody) {
            console.warn('adminTableBody element not found');
            return;
        }

        adminSummaryCache.clear();

        if (admins.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">No admins found</td></tr>';
            return;
        }

        tbody.innerHTML = admins.map(admin => {
            adminSummaryCache.set(admin.id, admin);
            const districtNames = admin.districts_list && admin.districts_list.length
                ? admin.districts_list.join(', ')
                : '';
            const routeNames = admin.routes_list && admin.routes_list.length
                ? admin.routes_list.join(', ')
                : '';
            const unreadBadge = admin.unread_notifications
                ? `<span class="badge bg-danger" style="margin-left: 6px;">${admin.unread_notifications} new</span>`
                : '';
            const lastActive = admin.last_active ? formatTimeAgo(admin.last_active) : 'N/A';

            return `
                <tr>
                    <td>
                        <span class="admin-name-link" onclick="showAdminDetails(${admin.id})" style="cursor: pointer; color: #5b47fb; text-decoration: underline;">
                            ${admin.name}
                        </span>
                        ${unreadBadge}
                    </td>
                    <td>${admin.email}</td>
                    <td style="cursor: pointer;" onclick="showAdminAssignmentInHeader(${admin.id}, '${admin.name.replace(/'/g, "\\'")}', '${districtNames.replace(/'/g, "\\'")}', '${routeNames.replace(/'/g, "\\'")}')">
                        ${districtNames ? `<div><strong style="font-size:0.95rem;">Districts:</strong> <span class="badge bg-info">${districtNames}</span></div>` : ''}
                        ${routeNames ? `<div style="margin-top:6px;"><strong style="font-size:0.95rem;">Routes:</strong> <span class="badge bg-secondary">${routeNames}</span></div>` : (districtNames ? '' : '<span class="text-muted">Not assigned</span>')}
                        ${(districtNames || routeNames) ? '<div style="margin-top:4px;"><small style="color:#5b47fb;"><i class="fas fa-info-circle"></i> Click to view in header</small></div>' : ''}
                    </td>
                    <td>
                        <div style="display:flex;flex-direction:column;gap:4px;align-items:flex-start;">
                            <span class="badge bg-${admin.is_active ? 'success' : 'secondary'}">
                                ${admin.is_active ? 'Active' : 'Inactive'}
                            </span>
                            <small class="text-muted">Last active: ${lastActive}</small>
                        </div>
                    </td>
                    <td>
                        ${admin.role !== 'head' ? `
                            <button class="btn btn-sm btn-outline-primary" onclick="toggleAdminStatus(${admin.id}, ${admin.is_active})" title="Toggle Status">
                                <i class="bi bi-toggle-${admin.is_active ? 'on' : 'off'}"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deactivateAdmin(${admin.id}, '${admin.name.replace(/'/g, "&#39;")}')" title="Delete">
                                <i class="bi bi-trash"></i>
                            </button>
                        ` : '<span class="text-muted">Protected</span>'}
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading admins:', error);
        showToast('Error', 'Failed to load admin list', 'danger');
    }
}
// Handle create admin form submission
async function handleCreateAdmin(e) {
    e.preventDefault();
    
    const nameEl = document.getElementById('adminName');
    const emailEl = document.getElementById('adminEmail');
    const passwordEl = document.getElementById('adminPassword');
    
    if (!nameEl || !emailEl || !passwordEl) {
        console.warn('Form elements not found');
        return;
    }
    
    const name = nameEl.value.trim();
    const email = emailEl.value.trim();
    const password = passwordEl.value;
    
    if (!name || !email || !password) {
        showToast('Validation Error', 'All fields are required', 'warning');
        return;
    }
    
    if (password.length < 6) {
        showToast('Validation Error', 'Password must be at least 6 characters', 'warning');
        return;
    }
    
    try {
        const response = await apiRequest('/api/head/create-admin', 'POST', {
            name, email, password
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast('Success', `Admin ${name} created successfully!`, 'success');
            document.getElementById('createAdminForm').reset();
            
            // Reload both admin list AND dashboard stats to update the counter
            await Promise.all([
                loadAdminList(),
                loadDashboardStats()
            ]);
        } else {
            const data = await response.json();
            showToast('Error', data.error || 'Failed to create admin', 'danger');
        }
    } catch (error) {
        console.error('Error creating admin:', error);
        showToast('Error', 'Failed to create admin', 'danger');
    }
}

// Toggle admin status
async function toggleAdminStatus(adminId, currentStatus) {
    try {
        const response = await apiRequest(`/api/head/admins/${adminId}/toggle`, 'PUT');

        if (response.ok) {
            const data = await response.json();
            showToast('Success', data.message || 'Status updated', 'success');

            await Promise.all([
                loadAdminList(),
                loadDashboardStats()
            ]);
        } else {
            const data = await response.json();
            showToast('Error', data.error || 'Failed to toggle status', 'danger');
        }
    } catch (error) {
        console.error('Error toggling admin:', error);
        showToast('Error', 'Failed to toggle admin status', 'danger');
    }
}

// Deactivate admin
async function deactivateAdmin(adminId, adminName) {
    showConfirmModal(
        'Deactivate Admin',
        `Are you sure you want to deactivate ${adminName}? This will log them out immediately.`,
        async () => {
            try {
                const response = await apiRequest(`/api/head/admins/${adminId}`, 'DELETE');
                
                if (response.ok) {
                    const data = await response.json();
                    showToast('Success', `Admin ${adminName} deactivated successfully`, 'success');
                    
                    // Reload both admin list AND dashboard stats
                    await Promise.all([
                        loadAdminList(),
                        loadDashboardStats()
                    ]);
                } else {
                    const data = await response.json();
                    showToast('Error', data.error || 'Failed to deactivate admin', 'danger');
                }
            } catch (error) {
                console.error('Error deactivating admin:', error);
                showToast('Error', 'Failed to deactivate admin', 'danger');
            }
        }
    );
}

// Show admin details in modal
async function showAdminDetails(adminId) {
    try {
        showDashboardLoader();
        const [detailsResponse, messagesResponse] = await Promise.all([
            apiRequest(`/api/head/admin/${adminId}/details`, 'GET'),
            apiRequest(`/api/head/admin/${adminId}/messages?include_read=true&limit=50`, 'GET')
        ]);

        if (!detailsResponse.ok) {
            const errorData = await detailsResponse.json();
            throw new Error(errorData.error || 'Failed to load admin details');
        }

        const details = await detailsResponse.json();
        const messagesData = messagesResponse && messagesResponse.ok ? await messagesResponse.json() : { notifications: [] };
        const notifications = messagesData.notifications || [];
        const summary = adminSummaryCache.get(adminId) || {};
        const districts = details.districts || [];
        const allRoutes = details.all_routes || [];
        const lastNotification = summary.last_notification_at ? formatDateTime(summary.last_notification_at) : 'N/A';

        closeAdminDetails();

        const modalHTML = `
            <div id="adminDetailsModal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 9999;">
                <div style="background: white; border-radius: 12px; padding: 30px; max-width: 720px; width: 92%; max-height: 85vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 2px solid #5b47fb; padding-bottom: 15px;">
                        <h3 style="margin: 0; color: #5b47fb; display:flex; flex-direction:column; gap:6px;">
                            <span><i class="bi bi-person-badge"></i> Admin Details</span>
                            <small style="color:#6c757d; font-size:0.85rem;">Last notification: ${lastNotification}</small>
                        </h3>
                        <button onclick="closeAdminDetails()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
                    </div>

                    <div style="margin-bottom: 20px;">
                        <div style="display: grid; grid-template-columns: 140px 1fr; gap: 15px; margin-bottom: 10px;">
                            <strong style="color: #666;">ID:</strong>
                            <span>${details.id}</span>

                            <strong style="color: #666;">Name:</strong>
                            <span>${escapeHtml(details.name)}</span>

                            <strong style="color: #666;">Email:</strong>
                            <span>${escapeHtml(details.email)}</span>

                            <strong style="color: #666;">Status:</strong>
                            <span>
                                <span class="badge bg-${details.is_active ? 'success' : 'secondary'}">
                                    ${details.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </span>

                            <strong style="color: #666;">Created:</strong>
                            <span>${new Date(details.created_at).toLocaleString()}</span>
                        </div>
                    </div>

                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                        <h5 style="margin-top: 0; color: #5b47fb; display:flex;align-items:center;gap:8px;">
                            <i class="bi bi-geo-alt"></i> Assigned Districts
                        </h5>
                        ${districts.length > 0 ?
                            districts.map(d => `
                                <div style="margin-bottom: 10px;">
                                    <strong style="color: #333;">${escapeHtml(d.district_name)}</strong>
                                </div>
                            `).join('')
                            : '<p style="color: #999; margin: 0;">No districts assigned</p>'
                        }
                    </div>

                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                        <h5 style="margin-top: 0; color: #5b47fb; display:flex;align-items:center;gap:8px;">
                            <i class="bi bi-signpost"></i> All Assigned Routes
                        </h5>
                        ${allRoutes.length > 0 ?
                            `<div style="display: flex; flex-wrap: wrap; gap: 8px;">
                                ${allRoutes.map(route =>
                                    `<span class="badge bg-primary" style="font-size: 12px; padding: 6px 12px;">${escapeHtml(route)}</span>`
                                ).join('')}
                            </div>`
                            : '<p style="color: #999; margin: 0;">No routes assigned</p>'
                        }
                    </div>

                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                        <div style="display:flex;justify-content:space-between;align-items:center; margin-bottom:12px;">
                            <h5 style="margin:0; color:#5b47fb; display:flex;align-items:center;gap:8px;">
                                <i class="bi bi-chat-dots"></i> Direct Messages
                            </h5>
                            <button class="btn btn-sm btn-outline-secondary" onclick="markAllAdminMessagesRead(${adminId})">Mark all as read</button>
                        </div>
                        <div id="adminMessagesList-${adminId}" style="display:flex;flex-direction:column;gap:12px;"></div>
                        <div style="margin-top: 15px;">
                            <label for="adminMessageInput-${adminId}" style="font-weight:600; color:#555;">Send a direct message</label>
                            <textarea id="adminMessageInput-${adminId}" class="form-control" rows="3" placeholder="Type your message to this admin..."></textarea>
                            <div style="margin-top:10px; display:flex; gap:10px; justify-content:flex-end;">
                                <button class="btn btn-secondary" onclick="refreshAdminMessages(${adminId})">
                                    <i class="bi bi-arrow-repeat"></i> Refresh
                                </button>
                                <button class="btn btn-primary" onclick="sendAdminMessage(${adminId})">
                                    <i class="bi bi-send"></i> Send Message
                                </button>
                            </div>
                        </div>
                    </div>

                    <div style="margin-top: 20px; text-align: right;">
                        <button onclick="closeAdminDetails()" class="btn btn-primary">
                            <i class="bi bi-check-circle"></i> Close
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        adminMessagesCache.set(adminId, notifications);
        renderAdminMessages(adminId, notifications);
    } catch (error) {
        console.error('Error loading admin details:', error);
        showToast('Error', error.message || 'Failed to load admin details', 'danger');
    } finally {
        hideDashboardLoader();
    }
}

// Close admin details modal
function closeAdminDetails() {
    const modal = document.getElementById('adminDetailsModal');
    if (modal) {
        modal.remove();
    }
}

function renderAdminMessages(adminId, messages) {
    const container = document.getElementById(`adminMessagesList-${adminId}`);
    if (!container) {
        return;
    }

    if (!messages || messages.length === 0) {
        container.innerHTML = '<p class="text-muted" style="margin:0;">No direct messages yet.</p>';
        return;
    }

    container.innerHTML = messages.map(message => {
        const statusBadge = message.is_read
            ? '<span class="badge bg-secondary">Read</span>'
            : `<button class="btn btn-sm btn-outline-primary" onclick="markAdminMessageRead(${adminId}, ${message.id})">Mark as read</button>`;
        return `
            <div style="background:#fff; border:1px solid #e0e0e0; border-radius:8px; padding:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
                    <div>
                        <strong>${escapeHtml(message.sender_name || 'System')}</strong><br>
                        <small class="text-muted">${formatDateTime(message.created_at)}</small>
                    </div>
                    ${statusBadge}
                </div>
                <p style="margin-top:10px; margin-bottom:0; white-space:pre-wrap;">${escapeHtml(message.message || '')}</p>
            </div>
        `;
    }).join('');
}

async function refreshAdminMessages(adminId) {
    try {
        const response = await apiRequest(`/api/head/admin/${adminId}/messages?include_read=true&limit=50`, 'GET');
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to refresh messages');
        }

        const payload = await response.json();
        const messages = payload.notifications || [];
        adminMessagesCache.set(adminId, messages);
        renderAdminMessages(adminId, messages);
        await loadAdminList();
    } catch (error) {
        console.error('Error refreshing admin messages:', error);
        showToast('Error', error.message || 'Could not refresh messages', 'danger');
    }
}

async function sendAdminMessage(adminId) {
    const textarea = document.getElementById(`adminMessageInput-${adminId}`);
    if (!textarea) return;

    const message = textarea.value.trim();
    if (!message) {
        showToast('Validation Error', 'Message cannot be empty', 'warning');
        return;
    }

    try {
        const response = await apiRequest(`/api/head/admin/${adminId}/message`, 'POST', { message });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to send message');
        }

        textarea.value = '';
        showToast('Success', 'Message delivered to admin', 'success');
        await refreshAdminMessages(adminId);
    } catch (error) {
        console.error('Error sending admin message:', error);
        showToast('Error', error.message || 'Failed to send message', 'danger');
    }
}

async function markAdminMessageRead(adminId, notificationId) {
    try {
        const response = await apiRequest(`/api/head/admin/${adminId}/messages/${notificationId}/read`, 'PUT');
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to mark message read');
        }

        showToast('Success', 'Message marked as read', 'success');
        await refreshAdminMessages(adminId);
    } catch (error) {
        console.error('Error marking message read:', error);
        showToast('Error', error.message || 'Failed to update message status', 'danger');
    }
}

async function markAllAdminMessagesRead(adminId) {
    try {
        const response = await apiRequest(`/api/head/admin/${adminId}/messages/mark-read`, 'PUT');
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to mark messages');
        }

        const result = await response.json();
        const count = result.updated || 0;
        showToast('Success', `${count} message${count === 1 ? '' : 's'} marked as read`, 'success');
        await refreshAdminMessages(adminId);
    } catch (error) {
        console.error('Error marking messages read:', error);
        showToast('Error', error.message || 'Failed to mark messages as read', 'danger');
    }
}

function escapeHtml(value) {
    if (value === null || value === undefined) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Load complaints
async function loadComplaints() {
    try {
        const statusFilter = document.getElementById('statusFilter');
        const searchComplaints = document.getElementById('searchComplaints');
        
        const status = statusFilter ? statusFilter.value : 'all';
        const search = searchComplaints ? searchComplaints.value.toLowerCase() : '';
        
        const response = await apiRequest('/api/complaints', 'GET');
        
        if (response.ok) {
            const data = await response.json();
            let complaints = Array.isArray(data) ? data : data.complaints || [];
            
            // Apply filters
            if (status !== 'all') {
                complaints = complaints.filter(c => c.status === status);
            }
            
            if (search) {
                complaints = complaints.filter(c => 
                    c.bus_number.toLowerCase().includes(search) ||
                    c.description.toLowerCase().includes(search)
                );
            }
            
            const tbody = document.getElementById('complaintsTableBody');
            
            if (!tbody) {
                console.warn('complaintsTableBody element not found');
                return;
            }
            
            if (complaints.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center">No complaints found</td></tr>';
                return;
            }
            
            tbody.innerHTML = complaints.map(complaint => `
                <tr>
                    <td>${complaint.id}</td>
                    <td>${complaint.user_name || 'N/A'}</td>
                    <td>${complaint.district_name || 'Not specified'}</td>
                    <td>${complaint.route_name || complaint.route || 'Not specified'}</td>
                    <td><strong>${complaint.bus_number}</strong></td>
                    <td>${complaint.category}</td>
                    <td>
                        ${complaint.admin_name ? 
                            `<span class="badge bg-success">${complaint.admin_name}</span>` : 
                            '<span class="badge bg-secondary">Unassigned</span>'
                        }
                    </td>
                    <td><span class="status-badge status-${complaint.status}">${complaint.status}</span></td>
                    <td>${formatDate(complaint.created_at)}</td>
                    <td>
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-primary" onclick="viewComplaint(${complaint.id})" title="View Details">
                                <i class="bi bi-eye"></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteComplaint(${complaint.id})" title="Delete">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading complaints:', error);
        showToast('Error', 'Failed to load complaints', 'danger');
    }
}

// Alias for loadComplaints
const loadAllComplaints = loadComplaints;

// Load admin activities
async function loadAdminActivities() {
    try {
        const response = await apiRequest('/api/dashboard/admin_logs?limit=50', 'GET');
        if (response.ok) {
            const data = await response.json();
            if (data.logs && data.logs.length > 0) {
                const html = data.logs.map(log => `
                <div class="activity-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <input type="checkbox" class="admin-log-checkbox me-2" value="${log.id}">
                            <strong>${log.admin_name}</strong>
                            <div class="mt-1">
                                <span class="badge bg-primary">${log.action}</span>
                                ${log.description || ''}
                            </div>
                            ${log.ip_address ? `<small class="text-muted">IP: ${log.ip_address}</small>` : ''}
                        </div>
                        <span class="activity-time">${formatDateTime(log.created_at)}</span>
                    </div>
                </div>
            `).join('');
                const activityFeedEl = document.getElementById('activityFeed');
                if (activityFeedEl) {
                    activityFeedEl.innerHTML = html;
                }
            } else {
                const activityFeedEl = document.getElementById('activityFeed');
                if (activityFeedEl) {
                    activityFeedEl.innerHTML = '<p class="text-center text-muted">No activities recorded</p>';
                }
            }
        }
    } catch (error) {
        console.error('Error loading activities:', error);
        showToast('Error', 'Failed to load activities', 'danger');
    }
}

// Load user logs
async function loadUserLogs() {
    try {
        const response = await apiRequest('/api/head/user-logs');
        console.log('User logs response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('User logs data:', data);
            const tbody = document.getElementById('userLogsTable');
            
            if (!tbody) {
                console.warn('userLogsTable element not found');
                return;
            }
            
            if (data.logs && data.logs.length > 0) {
                tbody.innerHTML = data.logs.map(log => `
                    <tr>
                        <td><input type="checkbox" class="user-log-checkbox" value="${log.id}"></td>
                        <td>${log.id}</td>
                        <td>${log.user_name}</td>
                        <td>${log.user_email}</td>
                        <td><span class="badge bg-info">${log.action}</span></td>
                        <td>${log.description}</td>
                        <td>${new Date(log.timestamp).toLocaleString()}</td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No user logs found</td></tr>';
            }
        } else {
            console.error('Failed to load user logs');
            showToast('Error', 'Failed to load user logs', 'danger');
        }
    } catch (error) {
        console.error('Error loading user logs:', error);
        showToast('Error', 'Connection error loading user logs', 'danger');
    }
}

// Load all users
async function loadAllUsers() {
    try {
        const response = await apiRequest('/api/head/users');
        console.log('Users response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Users data:', data);
            const tbody = document.getElementById('usersTable');
            
            if (!tbody) {
                console.warn('usersTable element not found');
                return;
            }
            
            if (data.users && data.users.length > 0) {
                tbody.innerHTML = data.users.map(user => `
                    <tr>
                        <td>${user.id}</td>
                        <td>${user.name}</td>
                        <td>${user.email}</td>
                        <td><span class="badge bg-secondary">${user.role}</span></td>
                        <td><span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                        <td>
                            ${user.role !== 'head' ? `
                                <button class="btn btn-sm btn-danger" onclick="deleteUser(${user.id}, '${user.name}')">
                                    <i class="bi bi-trash"></i> Delete
                                </button>
                            ` : '<span class="text-muted">Protected</span>'}
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No users found</td></tr>';
            }
        } else {
            console.error('Failed to load users');
            showToast('Error', 'Failed to load users', 'danger');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showToast('Error', 'Connection error loading users', 'danger');
    }
}

// Load online users
async function loadOnlineUsers() {
    try {
        const response = await apiRequest('/api/dashboard/online_users', 'GET');
        
        if (response.ok) {
            const data = await response.json();
            if (data.users && data.users.length > 0) {
                const html = data.users.map(user => `
                <div class="online-user">
                    <div class="online-dot"></div>
                    <strong>${user.name}</strong>
                    <span class="text-muted">(${user.role})</span>
                    <small class="text-muted ms-2">${formatTimeAgo(user.last_active)}</small>
                </div>
            `).join('');
            
            const onlineUsersEl = document.getElementById('onlineUsersList');
            if (onlineUsersEl) {
                onlineUsersEl.innerHTML = html;
            }
        } else {
            const onlineUsersEl = document.getElementById('onlineUsersList');
            if (onlineUsersEl) {
                onlineUsersEl.innerHTML = '<p class="text-center text-muted">No users currently online</p>';
            }
        }
    }
    } catch (error) {
        console.error('Error loading online users:', error);
    }
}

// API request helper
async function apiRequest(endpoint, method = 'GET', body = null) {
    const token = localStorage.getItem('token');
    
    console.log('🔑 API Request:', endpoint, 'Token:', token ? token.substring(0, 10) + '...' : 'NO TOKEN');
    
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(API_BASE + endpoint, options);
        console.log('📡 Response status:', response.status, endpoint);
        
        // Check for authentication errors
        if (response.status === 401) {
            console.error('❌ 401 Unauthorized - Redirecting to login');
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = 'login.html';
            return response;
        }
        
        return response;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
        }
    }
// Remove extra closing brace at end of file

// Show toast notification
function showToast(title, message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container');
    const toastId = 'toast-' + Date.now();
    
    const bgColor = {
        'success': 'bg-success',
        'danger': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    }[type] || 'bg-info';
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white ${bgColor} border-0`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong><br>${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Update last update time
function updateLastUpdateTime() {
    document.getElementById('lastUpdate').textContent = `Updated ${new Date().toLocaleTimeString()}`;
}

// Modern Confirm Modal Functions
function showConfirmModal(title, message, onConfirm) {
    const modal = document.getElementById('confirmModal');
    const titleElement = document.getElementById('confirmModalTitle');
    const messageElement = document.getElementById('confirmModalMessage');
    const confirmBtn = document.getElementById('confirmModalBtn');
    
    titleElement.textContent = title;
    messageElement.textContent = message;
    
    // Remove old event listeners by cloning
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    newConfirmBtn.onclick = async () => {
        closeConfirmModal();
        if (onConfirm) await onConfirm();
    };
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeConfirmModal() {
    const modal = document.getElementById('confirmModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Logout function
function logout() {
    showConfirmModal(
        'Confirm Logout',
        'Are you sure you want to logout?',
        async () => {
            clearInterval(refreshInterval);
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = 'login.html';
        }
    );
}

// View complaint details with proof
async function viewComplaint(complaintId) {
    try {
        const response = await apiRequest(`/api/complaints/${complaintId}`, 'GET');
        
        if (response.ok) {
            const complaint = await response.json();
            
            // Populate modal fields
            document.getElementById('modalComplaintId').textContent = complaint.id || 'N/A';
            document.getElementById('modalUserName').textContent = complaint.user_name || complaint.name || 'N/A';
            document.getElementById('modalUserEmail').textContent = complaint.user_email || complaint.email || 'N/A';
            document.getElementById('modalBusNumber').textContent = complaint.bus_number || 'N/A';
            document.getElementById('modalCategory').textContent = complaint.category || 'N/A';
            document.getElementById('modalStatus').innerHTML = `<span class="status-badge status-${complaint.status}">${complaint.status}</span>`;
            document.getElementById('modalCreatedAt').textContent = formatDate(complaint.created_at);
            document.getElementById('modalDescription').textContent = complaint.description || 'No description provided';
            document.getElementById('modalDistrict').textContent = complaint.district_name || 'Not specified';
            document.getElementById('modalRoute').textContent = complaint.route_name || complaint.route || 'Not specified';
            
            // Display assigned admin
            const assignedAdminEl = document.getElementById('modalAssignedAdmin');
            if (assignedAdminEl) {
                if (complaint.admin_name) {
                    assignedAdminEl.innerHTML = `<span class="badge bg-success">${complaint.admin_name}</span>`;
                } else {
                    assignedAdminEl.innerHTML = '<span class="badge bg-secondary">Unassigned</span>';
                }
            }
            
            // Handle media files display
            const proofSection = document.getElementById('modalProofSection');
            
            // Fetch media files for this complaint
            let mediaFiles = complaint.media_files || [];
            if (!mediaFiles.length && complaint.id) {
                try {
                    const mediaResponse = await apiRequest(`/api/complaints/${complaint.id}/media`, 'GET');
                    if (mediaResponse.ok) {
                        const mediaData = await mediaResponse.json();
                        mediaFiles = mediaData.media || [];
                    }
                } catch (err) {
                    console.error('Failed to fetch media files:', err);
                }
            }
            
            if (mediaFiles.length > 0) {
                const mediaHTML = await Promise.all(mediaFiles.map(async (media) => {
                    const isImage = media.file_type === 'image' || media.mime_type?.startsWith('image');
                    const isVideo = media.file_type === 'video' || media.mime_type?.startsWith('video');
                    const isPDF = media.file_type === 'document' || media.mime_type?.includes('pdf');
                    
                    if (isImage) {
                        try {
                            const blobUrl = await fetchProtectedFile(media.file_path);
                            return `<div style="margin: 10px; display: inline-block;">
                                <img src="${blobUrl}" style="max-width: 200px; max-height: 200px; border-radius: 8px; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" onclick="window.open('${blobUrl}', '_blank')" alt="${media.file_name}">
                                <p style="text-align: center; font-size: 0.8rem; margin-top: 5px;">${media.file_name}</p>
                            </div>`;
                        } catch (err) {
                            return `<div style="margin: 10px; padding: 15px; background: #f3f4f6; border-radius: 8px; display: inline-block;">
                                <i class="fas fa-image" style="font-size: 2rem; color: #9ca3af;"></i>
                                <p style="font-size: 0.8rem; margin-top: 5px;">${media.file_name}</p>
                            </div>`;
                        }
                    } else if (isVideo) {
                        return `<div style="margin: 10px; display: inline-block;">
                            <a href="${API_BASE}/uploads/${media.file_path}" target="_blank" class="btn btn-primary">
                                <i class="fas fa-video"></i> ${media.file_name}
                            </a>
                        </div>`;
                    } else {
                        return `<div style="margin: 10px; display: inline-block;">
                            <a href="${API_BASE}/uploads/${media.file_path}" target="_blank" class="btn btn-secondary">
                                <i class="fas fa-file-pdf"></i> ${media.file_name}
                            </a>
                        </div>`;
                    }
                }));
                proofSection.innerHTML = mediaHTML.join('');
            } else if (complaint.proof_path) {
                // Legacy single proof file support
                try {
                    const blobUrl = await fetchProtectedFile(complaint.proof_path);
                    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];
                    const isImage = imageExtensions.some(ext => complaint.proof_path.toLowerCase().endsWith(ext));

                    if (isImage) {
                        proofSection.innerHTML = `<img src="${blobUrl}" class="img-fluid rounded" alt="Complaint Proof" style="max-width: 100%; cursor: pointer;" onclick="window.open('${blobUrl}', '_blank')">`;
                    } else {
                        proofSection.innerHTML = `<a href="${blobUrl}" download class="btn btn-primary">
                            <i class="bi bi-download"></i> Download Proof File
                        </a>`;
                    }
                } catch (err) {
                    console.error('Failed to load proof file', err);
                    proofSection.innerHTML = '<p class="text-muted text-center">Failed to load proof file</p>';
                }
            } else {
                proofSection.innerHTML = '<p class="text-muted text-center">No media files uploaded for this complaint</p>';
            }
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('complaintModal'));
            modal.show();
        } else {
            showToast('Error', 'Failed to load complaint details', 'danger');
        }
    } catch (error) {
        console.error('Error viewing complaint:', error);
        showToast('Error', 'Failed to load complaint details', 'danger');
    }
}

// Utility functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Fetch protected file (with Authorization) and return object URL
async function fetchProtectedFile(filename) {
    const token = localStorage.getItem('token');
    if (!token) throw new Error('Not authenticated');

    // Fetch media file from /api/uploads/ endpoint on backend
    const res = await fetch(`${API_BASE}/api/uploads/${encodeURIComponent(filename)}`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });

    if (!res.ok) {
        throw new Error(`Failed to fetch file: ${res.status}`);
    }

    const blob = await res.blob();
    return URL.createObjectURL(blob);
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
}

function formatTimeAgo(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

// ==================== DISTRICT/ROUTE/BUS MANAGEMENT ====================

let districts = [];
let routes = [];
let buses = [];
let admins = [];
let assignments = [];

// Load Districts
async function loadDistricts() {
    try {
        const response = await fetch(`${API_BASE}/api/districts`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (response.ok) {
            districts = await response.json();
            renderDistrictsTable();
            populateDistrictFilters();
        }
    } catch (error) {
        console.error('Failed to load districts:', error);
    }
}

function renderDistrictsTable() {
    const tbody = document.getElementById('districtsTableBody');
    if (!tbody) return;
    
    if (districts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No districts found</td></tr>';
        return;
    }
    
    tbody.innerHTML = districts.map(d => `
        <tr>
            <td><strong>${d.code}</strong></td>
            <td>${d.name}</td>
            <td>${d.description || '-'}</td>
            <td><span class="badge" style="background:#1c1431;color:#fff;">${d.priority}</span></td>
            <td><span class="badge bg-${d.is_active ? 'success' : 'secondary'}">${d.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <button class="btn btn-sm btn-warning" onclick="editDistrict(${d.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-danger" onclick="deleteDistrict(${d.id}, '${d.name}')"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

function populateDistrictFilters() {
    const selects = ['routeDistrictFilter', 'routeDistrict', 'assignmentDistrict'];
    selects.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            const currentValue = select.value;
            const options = districts.map(d => 
                `<option value="${d.id}">${d.name} (${d.code})</option>`
            ).join('');
            
            if (id === 'routeDistrictFilter') {
                select.innerHTML = '<option value="">All Districts</option>' + options;
            } else {
                select.innerHTML = '<option value="">Select District</option>' + options;
            }
            
            if (currentValue) select.value = currentValue;
        }
    });
}

function showDistrictModal(id = null) {
    const modal = new bootstrap.Modal(document.getElementById('districtModal'));
    document.getElementById('districtModalTitle').textContent = id ? 'Edit District' : 'Add District';
    document.getElementById('districtForm').reset();
    document.getElementById('districtId').value = id || '';
    
    if (id) {
        const district = districts.find(d => d.id === id);
        if (district) {
            document.getElementById('districtCode').value = district.code;
            document.getElementById('districtName').value = district.name;
            document.getElementById('districtDescription').value = district.description || '';
            document.getElementById('districtPriority').value = district.priority;
        }
    }
    
    modal.show();
}

async function saveDistrict() {
    const id = document.getElementById('districtId').value;
    const data = {
        code: document.getElementById('districtCode').value,
        name: document.getElementById('districtName').value,
        description: document.getElementById('districtDescription').value,
        priority: parseInt(document.getElementById('districtPriority').value)
    };
    
    try {
        const url = id ? `${API_BASE}/api/districts/${id}` : `${API_BASE}/api/districts`;
        const method = id ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('districtModal')).hide();
            showToast('Success', `District ${id ? 'updated' : 'created'} successfully`, 'success');
            loadDistricts();
        } else {
            const error = await response.json();
            showToast('Error', error.error || 'Failed to save district', 'danger');
        }
    } catch (error) {
        showToast('Error', 'Connection error', 'danger');
    }
}

function editDistrict(id) {
    showDistrictModal(id);
}

async function deleteDistrict(id, name) {
    showConfirmModal(
        'Delete District',
        `Are you sure you want to delete district "${name}"? This will also delete all routes and buses in this district.`,
        async () => {
            try {
                const response = await fetch(`${API_BASE}/api/districts/${id}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                
                if (response.ok) {
                    showToast('Success', 'District deleted successfully', 'success');
                    loadDistricts();
                    loadRoutes();
                    loadBuses();
                } else {
                    const error = await response.json();
                    showToast('Error', error.error || 'Failed to delete district', 'danger');
                }
            } catch (error) {
                showToast('Error', 'Connection error', 'danger');
            }
        }
    );
}

// Load Routes
async function loadRoutes() {
    const districtId = document.getElementById('routeDistrictFilter')?.value || '';
    const url = districtId ? `${API_BASE}/api/routes?district_id=${districtId}` : `${API_BASE}/api/routes`;
    
    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (response.ok) {
            routes = await response.json();
            renderRoutesTable();
            populateRouteFilters();
        }
    } catch (error) {
        console.error('Failed to load routes:', error);
    }
}

function renderRoutesTable() {
    const tbody = document.getElementById('routesTableBody');
    if (!tbody) return;
    
    if (routes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No routes found</td></tr>';
        return;
    }
    
    tbody.innerHTML = routes.map(r => `
        <tr>
            <td><strong>${r.code}</strong></td>
            <td>${r.name}</td>
            <td>${r.district_name || '-'}</td>
            <td>${r.start_point} → ${r.end_point}</td>
            <td><span class="badge" style="background:#1c1431;color:#fff;">${r.priority}</span></td>
            <td><span class="badge bg-${r.is_active ? 'success' : 'secondary'}">${r.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <button class="btn btn-sm btn-warning" onclick="editRoute(${r.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-danger" onclick="deleteRoute(${r.id}, '${r.name}')"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

function populateRouteFilters() {
    const selects = ['busRouteFilter', 'busRoute', 'assignmentRoute'];
    selects.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            const currentValue = select.value;
            const options = routes.map(r => 
                `<option value="${r.id}">${r.name} (${r.code})</option>`
            ).join('');
            
            if (id === 'busRouteFilter') {
                select.innerHTML = '<option value="">All Routes</option>' + options;
            } else {
                select.innerHTML = '<option value="">Select Route</option>' + options;
            }
            
            if (currentValue) select.value = currentValue;
        }
    });
}

function showRouteModal(id = null) {
    const modal = new bootstrap.Modal(document.getElementById('routeModal'));
    document.getElementById('routeModalTitle').textContent = id ? 'Edit Route' : 'Add Route';
    document.getElementById('routeForm').reset();
    document.getElementById('routeId').value = id || '';
    
    if (id) {
        const route = routes.find(r => r.id === id);
        if (route) {
            document.getElementById('routeDistrict').value = route.district_id;
            document.getElementById('routeCode').value = route.code;
            document.getElementById('routeName').value = route.name;
            document.getElementById('routeStartPoint').value = route.start_point;
            document.getElementById('routeEndPoint').value = route.end_point;
            document.getElementById('routeDescription').value = route.description || '';
            document.getElementById('routePriority').value = route.priority;
        }
    }
    
    modal.show();
}

async function saveRoute() {
    const id = document.getElementById('routeId').value;
    const data = {
        district_id: parseInt(document.getElementById('routeDistrict').value),
        code: document.getElementById('routeCode').value,
        name: document.getElementById('routeName').value,
        start_point: document.getElementById('routeStartPoint').value,
        end_point: document.getElementById('routeEndPoint').value,
        description: document.getElementById('routeDescription').value,
        priority: parseInt(document.getElementById('routePriority').value)
    };
    
    try {
        const url = id ? `${API_BASE}/api/routes/${id}` : `${API_BASE}/api/routes`;
        const method = id ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('routeModal')).hide();
            showToast('Success', `Route ${id ? 'updated' : 'created'} successfully`, 'success');
            loadRoutes();
        } else {
            const error = await response.json();
            showToast('Error', error.error || 'Failed to save route', 'danger');
        }
    } catch (error) {
        showToast('Error', 'Connection error', 'danger');
    }
}

function editRoute(id) {
    showRouteModal(id);
}

async function deleteRoute(id, name) {
    if (!confirm(`Are you sure you want to delete route "${name}"? This will also delete all buses on this route.`)) return;
    try {
        const response = await fetch(`${API_BASE}/api/routes/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (response.ok) {
            showToast('Success', 'Route deleted successfully', 'success');
            loadRoutes();
            loadBuses();
        } else {
            const error = await response.json();
            showToast('Error', error.error || 'Failed to delete route', 'danger');
        }
    } catch (error) {
        showToast('Error', 'Connection error', 'danger');
    }
}
// Removed extra closing brace at end of file

// Load Buses
async function loadBuses() {
    const routeId = document.getElementById('busRouteFilter')?.value || '';
    const url = routeId ? `${API_BASE}/api/buses?route_id=${routeId}` : `${API_BASE}/api/buses`;
    
    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (response.ok) {
            buses = await response.json();
            renderBusesTable();
            populateBusFilters();
        }
    } catch (error) {
        console.error('Failed to load buses:', error);
    }
}

function renderBusesTable() {
    const tbody = document.getElementById('busesTableBody');
    if (!tbody) return;
    
    if (buses.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No buses found</td></tr>';
        return;
    }
    
    tbody.innerHTML = buses.map(b => `
        <tr>
            <td><strong>${b.bus_number}</strong></td>
            <td>${b.bus_name}</td>
            <td>${b.route_name || '-'}</td>
            <td>${b.district_name || '-'}</td>
            <td>${b.capacity}</td>
            <td><span class="badge" style="background:#1c1431;color:#fff;">${b.priority}</span></td>
            <td><span class="badge bg-${b.status === 'active' ? 'success' : b.status === 'maintenance' ? 'warning' : 'secondary'}">${b.status}</span></td>
            <td>
                <button class="btn btn-sm btn-warning" onclick="editBus(${b.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-danger" onclick="deleteBus(${b.id}, '${b.bus_number}')"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

function populateBusFilters() {
    const select = document.getElementById('assignmentBus');
    if (select) {
        const currentValue = select.value;
        select.innerHTML = '<option value="">Select Bus</option>' + buses.map(b => 
            `<option value="${b.id}">${b.bus_name} - ${b.bus_number}</option>`
        ).join('');
        if (currentValue) select.value = currentValue;
    }
}

function showBusModal(id = null) {
    const modal = new bootstrap.Modal(document.getElementById('busModal'));
    document.getElementById('busModalTitle').textContent = id ? 'Edit Bus' : 'Add Bus';
    document.getElementById('busForm').reset();
    document.getElementById('busId').value = id || '';
    
    if (id) {
        const bus = buses.find(b => b.id === id);
        if (bus) {
            document.getElementById('busRoute').value = bus.route_id;
            document.getElementById('busNumber').value = bus.bus_number;
            document.getElementById('busName').value = bus.bus_name;
            document.getElementById('busCapacity').value = bus.capacity;
            document.getElementById('busStatus').value = bus.status;
            document.getElementById('busPriority').value = bus.priority;
        }
    }
    
    modal.show();
}

async function saveBus() {
    const id = document.getElementById('busId').value;
    const data = {
        route_id: parseInt(document.getElementById('busRoute').value),
        bus_number: document.getElementById('busNumber').value,
        bus_name: document.getElementById('busName').value,
        capacity: parseInt(document.getElementById('busCapacity').value),
        status: document.getElementById('busStatus').value,
        priority: parseInt(document.getElementById('busPriority').value)
    };
    
    try {
        const url = id ? `${API_BASE}/api/buses/${id}` : `${API_BASE}/api/buses`;
        const method = id ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('busModal')).hide();
            showToast('Success', `Bus ${id ? 'updated' : 'created'} successfully`, 'success');
            loadBuses();
        } else {
            const error = await response.json();
            showToast('Error', error.error || 'Failed to save bus', 'danger');
        }
    } catch (error) {
        showToast('Error', 'Connection error', 'danger');
    }
}

function editBus(id) {
    showBusModal(id);
}

async function deleteBus(id, busNumber) {
    showConfirmModal(
        'Delete Bus',
        `Are you sure you want to delete bus "${busNumber}"?`,
        async () => {
            try {
                const response = await fetch(`${API_BASE}/api/buses/${id}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                
                if (response.ok) {
                    showToast('Success', 'Bus deleted successfully', 'success');
                    loadBuses();
                } else {
                    const error = await response.json();
                    showToast('Error', error.error || 'Failed to delete bus', 'danger');
                }
            } catch (error) {
                showToast('Error', 'Connection error', 'danger');
            }
        }
    );
}

// Load Admin Assignments
async function loadAssignments() {
    const adminId = document.getElementById('assignmentAdminFilter')?.value || '';
    const url = adminId ? `${API_BASE}/api/admin-assignments?admin_id=${adminId}` : `${API_BASE}/api/admin-assignments`;
    
    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (response.ok) {
            assignments = await response.json();
            renderAssignmentsTable();
        }
    } catch (error) {
        console.error('Failed to load assignments:', error);
    }
}

function renderAssignmentsTable() {
    const tbody = document.getElementById('assignmentsTableBody');
    if (!tbody) return;
    
    if (assignments.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No assignments found</td></tr>';
        return;
    }
    
    tbody.innerHTML = assignments.map(a => `
        <tr>
            <td><strong>${a.admin_name}</strong></td>
            <td>${a.district_name}</td>
            <td>${a.route_name}</td>
            <td>${a.bus_name} (${a.bus_number})</td>
            <td><span class="badge" style="background:#1c1431;color:#fff;">${a.priority}</span></td>
            <td>${new Date(a.created_at).toLocaleDateString()}</td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="deleteAssignment(${a.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

async function loadAdminsForAssignment() {
    try {
        const response = await fetch(`${API_BASE}/api/head/admins`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (response.ok) {
            admins = await response.json();
            const selects = ['assignmentAdmin', 'assignmentAdminFilter'];
            selects.forEach(id => {
                const select = document.getElementById(id);
                if (select) {
                    const options = admins.filter(a => a.role === 'admin' && a.is_active).map(a => 
                        `<option value="${a.id}">${a.name} (${a.email})</option>`
                    ).join('');
                    
                    if (id === 'assignmentAdminFilter') {
                        select.innerHTML = '<option value="">All Admins</option>' + options;
                    } else {
                        select.innerHTML = '<option value="">Select Admin</option>' + options;
                    }
                }
            });
        }
    } catch (error) {
        console.error('Failed to load admins:', error);
    }
}

function showAssignmentModal() {
    const modal = new bootstrap.Modal(document.getElementById('assignmentModal'));
    document.getElementById('assignmentForm').reset();
    document.getElementById('assignmentRoute').disabled = true;
    document.getElementById('assignmentBus').disabled = true;
    modal.show();
}

async function loadRoutesForAssignment() {
    const districtId = document.getElementById('assignmentDistrict').value;
    const routeSelect = document.getElementById('assignmentRoute');
    const busSelect = document.getElementById('assignmentBus');
    
    busSelect.innerHTML = '<option value="">Select Route First</option>';
    busSelect.disabled = true;
    
    if (!districtId) {
        routeSelect.innerHTML = '<option value="">Select District First</option>';
        routeSelect.disabled = true;
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/routes?district_id=${districtId}`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (response.ok) {
            const routes = await response.json();
            routeSelect.innerHTML = '<option value="">Select Route</option>' + routes.map(r => 
                `<option value="${r.id}">${r.name} (${r.code})</option>`
            ).join('');
            routeSelect.disabled = false;
        }
    } catch (error) {
        console.error('Failed to load routes:', error);
    }
}

async function loadBusesForAssignment() {
    const routeId = document.getElementById('assignmentRoute').value;
    const busSelect = document.getElementById('assignmentBus');
    
    if (!routeId) {
        busSelect.innerHTML = '<option value="">Select Route First</option>';
        busSelect.disabled = true;
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/buses?route_id=${routeId}`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (response.ok) {
            const buses = await response.json();
            busSelect.innerHTML = '<option value="">Select Bus</option>' + buses.map(b => 
                `<option value="${b.id}">${b.bus_name} - ${b.bus_number}</option>`
            ).join('');
            busSelect.disabled = false;
        }
    } catch (error) {
        console.error('Failed to load buses:', error);
    }
}

async function saveAssignment() {
    const data = {
        admin_id: parseInt(document.getElementById('assignmentAdmin').value),
        district_id: parseInt(document.getElementById('assignmentDistrict').value),
        route_id: parseInt(document.getElementById('assignmentRoute').value),
        bus_id: parseInt(document.getElementById('assignmentBus').value),
        priority: parseInt(document.getElementById('assignmentPriority').value)
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/admin-assignments`, {

            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('assignmentModal')).hide();
            showToast('Success', 'Assignment created successfully', 'success');
            loadAssignments();
        } else {
            const error = await response.json();
            showToast('Error', error.error || 'Failed to create assignment', 'danger');
        }
    } catch (error) {
        showToast('Error', 'Connection error', 'danger');
    }
}

async function deleteAssignment(id) {
    showConfirmModal(
        'Delete Assignment',
        'Are you sure you want to delete this assignment?',
        async () => {
            try {
                const response = await fetch(`${API_BASE}/api/admin-assignments/${id}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                
                if (response.ok) {
                    showToast('Success', 'Assignment deleted successfully', 'success');
                    loadAssignments();
                } else {
                    const error = await response.json();
                    showToast('Error', error.error || 'Failed to delete assignment', 'danger');
                }
            } catch (error) {
                showToast('Error', 'Connection error', 'danger');
            }
        }
    );
}

// Load management data when sections are activated
const originalSwitchSection = switchSection;
switchSection = function(section) {
    originalSwitchSection(section);
    
    // Load data for management sections
    if (section === 'district-management') {
        loadDistricts();
    } else if (section === 'route-management') {
        loadDistricts(); // For filter
        loadRoutes();
    } else if (section === 'bus-management') {
        loadRoutes(); // For filter
        loadBuses();
    } else if (section === 'admin-assignments') {
        loadDistricts();
        loadAdminsForAssignment();
        loadAssignments();
    }
};

// Show admin assignment in header banner
function showAdminAssignmentInHeader(adminId, adminName, districts, routes) {
    const banner = document.getElementById('adminAssignmentBanner');
    const nameEl = document.getElementById('adminAssignmentName');
    const districtsEl = document.getElementById('adminAssignmentDistricts');
    const routesEl = document.getElementById('adminAssignmentRoutes');
    
    if (!banner || !nameEl || !districtsEl || !routesEl) return;
    
    nameEl.textContent = adminName;
    districtsEl.textContent = districts || 'Not assigned';
    routesEl.textContent = Array.isArray(routes) ? routes.join(', ') : (routes || 'Not assigned');
    
    banner.style.display = 'block';
    
    // Smooth scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    // Add highlight animation
    banner.style.animation = 'none';
    setTimeout(() => {
        banner.style.animation = 'pulse 0.5s ease';
    }, 10);
}

// Hide admin assignment banner
function hideAdminAssignmentBanner() {
    const banner = document.getElementById('adminAssignmentBanner');
    if (banner) {
        banner.style.display = 'none';
    }
}

// Make functions globally available
window.showAdminAssignmentInHeader = showAdminAssignmentInHeader;
window.hideAdminAssignmentBanner = hideAdminAssignmentBanner;

// Initialize real-time updates when dashboard loads
document.addEventListener('DOMContentLoaded', () => {
    // --- Socket.IO real-time updates ---
    // Make sure socket.io-client is loaded in your HTML:
    // <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    
    if (typeof io !== 'undefined') {
        const socket = io(API_BASE || window.location.origin, { 
            transports: ['polling', 'websocket'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5
        });

        socket.on('connect', () => {
            console.log('[Socket.IO] Connected to real-time server');
        });

        socket.on('disconnect', () => {
            console.log('[Socket.IO] Disconnected from server');
        });

        // Complaints update
        socket.on('complaints_updated', () => {
            if (typeof loadComplaints === 'function') loadComplaints();
            console.log('[Socket.IO] Complaints updated');
        });

        // Users update
        socket.on('users_updated', () => {
            if (typeof loadAllUsers === 'function') loadAllUsers();
            if (typeof loadAdminList === 'function') loadAdminList();
            console.log('[Socket.IO] Users updated');
        });

        // Assignments update
        socket.on('assignments_updated', () => {
            if (typeof loadAssignments === 'function') loadAssignments();
            console.log('[Socket.IO] Assignments updated');
        });

        // Admin logs update
        socket.on('admin_logs_updated', () => {
            if (typeof loadAdminActivities === 'function') loadAdminActivities();
            console.log('[Socket.IO] Admin logs updated');
        });

        // Notifications update
        socket.on('notifications_updated', () => {
            if (typeof loadNotifications === 'function') loadNotifications();
            console.log('[Socket.IO] Notifications updated');
        });

        // Online users update
        socket.on('online_users_updated', () => {
            if (typeof loadOnlineUsers === 'function') loadOnlineUsers();
            console.log('[Socket.IO] Online users updated');
        });
    } else {
        console.warn('[Socket.IO] Socket.IO library not loaded. Real-time updates disabled.');
    }
});
