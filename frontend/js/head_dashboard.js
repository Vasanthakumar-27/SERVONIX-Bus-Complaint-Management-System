// head_dashboard.js - Real-time Dashboard with API Integration
// PERFORMANCE OPTIMIZATIONS:
// - Loading state flags prevent concurrent API calls
// - Abort controllers cancel pending requests during refresh
// - Debounced refresh functions prevent rapid successive calls
// - Auto-refresh interval increased to 30s (from 15s)
// - Passive event listeners for better scroll performance
// - Request timeout set to 10s to prevent hanging

console.log('[HEAD DASHBOARD] Script loaded');

// Global flag to prevent multiple redirects
let isRedirecting = false;
let consecutiveErrors = 0;
const MAX_CONSECUTIVE_ERRORS = 3;

// Loading state flags to prevent concurrent loads
const loadingState = {
  stats: false,
  complaints: false,
  users: false,
  admins: false,
  feedback: false
};

// Abort controllers for cancelling pending requests
const abortControllers = {
  stats: null,
  complaints: null,
  users: null,
  admins: null,
  feedback: null
};

// Debounce helper
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

// Toast notification function
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer') || document.body;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const iconMap = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    const colorMap = {
        success: '#10B981',
        error: '#EF4444',
        warning: '#F59E0B',
        info: '#3B82F6'
    };
    
    toast.innerHTML = `
        <i class="fas ${iconMap[type] || 'fa-info-circle'}" style="color: ${colorMap[type] || colorMap.info}; font-size: 18px;"></i>
        <span style="flex: 1;">${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(120%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

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
    
    // Fallback
    if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') {
        return 'http://127.0.0.1:5000';
    } else {
        return `http://${window.location.hostname}:5000`;
    }
}

// Global 401 error handler - redirect to login if unauthorized
function handle401Error(response, context = '') {
    if (response.status === 401) {
        // Prevent multiple simultaneous redirects
        if (isRedirecting) {
            console.log(`[AUTH ERROR] Already redirecting, ignoring 401 from ${context}`);
            return true;
        }
        
        isRedirecting = true;
        console.error(`[AUTH ERROR] 401 Unauthorized in ${context} - Token expired or invalid`);
        
        // Stop all real-time updates to prevent cascading errors
        if (window.realtimeManager) {
            window.realtimeManager.stopAll();
            console.log('[AUTH ERROR] Stopped all real-time updates');
        }
        
        showToast('⚠️ Session expired. Redirecting to login...', 'warning');
        
        // Clear invalid token
        localStorage.removeItem('token');
        localStorage.removeItem('userRole');
        localStorage.removeItem('userEmail');
        
        // Set flag to allow direct access to login (bypass splash)
        sessionStorage.setItem('fromSplash', 'true');
        
        // Redirect to login after 1.5 seconds
        setTimeout(() => {
            window.location.href = '/html/login.html';
        }, 1500);
        
        return true;
    }
    return false;
}

console.log('[HEAD DASHBOARD] Current host:', window.location.hostname);
console.log('[HEAD DASHBOARD] API base will be:', getAPIBase());

// Ensure logo is always 100x100px
window.addEventListener('DOMContentLoaded', function() {
  console.log('[HEAD DASHBOARD] DOMContentLoaded event fired');
  
  var logoImg = document.querySelector('.brand img');
  if (logoImg) {
    logoImg.style.width = '100px';
    logoImg.style.height = '100px';
  }
  
  // NOTE: Data loading is handled by the initialization script in head_dashboard.html
  // This prevents duplicate loading and race conditions
  console.log('[HEAD DASHBOARD] DOM ready, waiting for initialization...');
  
  // Load districts and routes for dropdowns on page load
  loadDistrictsForDropdown();
  loadRoutesForDropdown();
  
  // Setup consolidated auto-refresh with safeguard against multiple instances
  if (!window.headDashboardRefreshInterval) {
    setTimeout(function() {
      window.headDashboardRefreshInterval = setInterval(function() {
        // Skip refresh if any loading is in progress
        if (loadingState.stats || loadingState.complaints || loadingState.users || loadingState.admins) {
          console.log('[AUTO-REFRESH] Skipping - loading in progress');
          return;
        }
        
        console.log('[AUTO-REFRESH] Refreshing dashboard data...');
        if (typeof loadDashboardStats === 'function') loadDashboardStats();
        if (typeof loadComplaints === 'function') loadComplaints();
        // Reduced frequency for less critical data
        const now = Date.now();
        if (!window.lastUserRefresh || now - window.lastUserRefresh > 60000) {
          if (typeof loadAllUsers === 'function') loadAllUsers();
          if (typeof loadAdminList === 'function') loadAdminList();
          window.lastUserRefresh = now;
        }
      }, 30000); // 30 seconds interval (increased from 15s)
    }, 5000); // Start after 5 seconds (increased from 3s)
  }
  
  // Manual refresh button with debouncing
  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) {
    // Create debounced refresh function
    const debouncedRefresh = debounce(() => {
      console.log('[Refresh] Manual refresh triggered');
      
      // Skip if any loading is in progress
      if (loadingState.stats || loadingState.complaints || loadingState.users || loadingState.admins) {
        showToast('⏳ Data is already loading, please wait...', 'warning');
        return;
      }
      
      // Reset error counter
      consecutiveErrors = 0;
      
      // Resume updates if paused
      if (window.realtimeManager) {
        window.realtimeManager.resume();
      }
      
      // Animate refresh icon
      const icon = refreshBtn.querySelector('i');
      if (icon) {
        icon.style.animation = 'spin 1s linear';
        setTimeout(() => { icon.style.animation = ''; }, 1000);
      }
      
      // Reload all data including districts and routes
      loadDashboardStats();
      loadAdminList();
      loadAllUsers();
      loadComplaints();
      loadAllFeedback();
      loadDistrictsForDropdown();
      loadRoutesForDropdown();
      
      showToast('Data refreshed successfully', 'success');
    }, 1000); // 1 second debounce
    
    refreshBtn.addEventListener('click', debouncedRefresh);
  }
  
  // Real-time updates enabled - 10 second interval
  console.log('[HEAD DASHBOARD] Real-time data refresh enabled (10 second interval)');
  
  // Logout button handler
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', function() {
      console.log('[LOGOUT] Button clicked');
      localStorage.removeItem('token');
      window.location.href = '/html/login.html';
    });
  }
  
  // Create Admin modal handler
  const toggleCreateAdminBtn = document.getElementById('toggleCreateAdminBtn');
  const createAdminModal = document.getElementById('createAdminModal');
  const closeCreateAdminModal = document.getElementById('closeCreateAdminModal');
  
  if (toggleCreateAdminBtn && createAdminModal) {
    toggleCreateAdminBtn.addEventListener('click', function() {
      console.log('[CREATE ADMIN] Opening modal');
      createAdminModal.style.display = 'block';
      // Load districts and routes when opening modal
      loadDistrictsForDropdown();
      loadRoutesForDropdown();
    });
  }
  
  if (closeCreateAdminModal && createAdminModal) {
    closeCreateAdminModal.addEventListener('click', function() {
      createAdminModal.style.display = 'none';
      document.getElementById('createAdminForm')?.reset();
    });
  }
  
  // Close modal when clicking outside
  if (createAdminModal) {
    createAdminModal.addEventListener('click', function(e) {
      if (e.target === createAdminModal) {
        createAdminModal.style.display = 'none';
        document.getElementById('createAdminForm')?.reset();
      }
    });
  }
  
  // Theme toggle handler
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    // Load saved theme - default to light mode
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.className = savedTheme === 'dark' ? 'dark-theme' : 'light-theme';
    updateThemeIcon(savedTheme);
    
    themeToggle.addEventListener('click', function() {
      const currentTheme = document.body.classList.contains('dark-theme') ? 'dark' : 'light';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      document.body.className = newTheme === 'dark' ? 'dark-theme' : 'light-theme';
      localStorage.setItem('theme', newTheme);
      updateThemeIcon(newTheme);
      
      console.log('[THEME] Switched to:', newTheme);
    });
  }
  
  console.log('[HEAD DASHBOARD] Auto-refresh active (10 seconds interval)');
  
  // Setup Create Admin Form Handler
  const createAdminForm = document.getElementById('createAdminForm');
  if (createAdminForm) {
    createAdminForm.addEventListener('submit', handleCreateAdmin);
  }
  
  // Setup Refresh Buttons
  const refreshAdminsBtn = document.getElementById('refreshAdminsBtn');
  if (refreshAdminsBtn) {
    refreshAdminsBtn.addEventListener('click', loadAdminList);
  }
  
  const refreshUsersBtn = document.getElementById('refreshUsersBtn');
  if (refreshUsersBtn) {
    refreshUsersBtn.addEventListener('click', loadAllUsers);
  }
  
  const refreshComplaintsBtn = document.getElementById('refreshComplaintsBtn');
  if (refreshComplaintsBtn) {
    refreshComplaintsBtn.addEventListener('click', loadComplaints);
  }
  
  const refreshFeedbackBtn = document.getElementById('refreshFeedbackBtn');
  if (refreshFeedbackBtn) {
    refreshFeedbackBtn.addEventListener('click', loadAllFeedback);
  }
  
  // Setup Print Buttons
  const printAdminsBtn = document.getElementById('printAdminsBtn');
  if (printAdminsBtn) {
    printAdminsBtn.addEventListener('click', printAdmins);
  }
  
  const printUsersBtn = document.getElementById('printUsersBtn');
  if (printUsersBtn) {
    printUsersBtn.addEventListener('click', printUsers);
  }
  
  const printComplaintsBtn = document.getElementById('printComplaintsBtn');
  if (printComplaintsBtn) {
    printComplaintsBtn.addEventListener('click', printAllComplaints);
  }
  
  const printFeedbackBtn = document.getElementById('printFeedbackBtn');
  if (printFeedbackBtn) {
    printFeedbackBtn.addEventListener('click', printFeedback);
  }
  
  // Setup Search and Filter Handlers
  const adminSearch = document.getElementById('adminSearch');
  if (adminSearch) {
    adminSearch.addEventListener('input', filterAdmins);
  }
  
  const userSearch = document.getElementById('userSearch');
  if (userSearch) {
    userSearch.addEventListener('input', filterUsers);
  }
  
  const complaintSearch = document.getElementById('complaintSearch');
  if (complaintSearch) {
    complaintSearch.addEventListener('input', filterComplaints);
  }
  
  const complaintStatusFilter = document.getElementById('complaintStatusFilter');
  if (complaintStatusFilter) {
    complaintStatusFilter.addEventListener('change', filterComplaints);
  }
  
  const feedbackSearch = document.getElementById('feedbackSearch');
  if (feedbackSearch) {
    feedbackSearch.addEventListener('input', filterFeedback);
  }
  
  const feedbackStatusFilter = document.getElementById('feedbackStatusFilter');
  if (feedbackStatusFilter) {
    feedbackStatusFilter.addEventListener('change', filterFeedback);
  }
  
  const feedbackRatingFilter = document.getElementById('feedbackRatingFilter');
  if (feedbackRatingFilter) {
    feedbackRatingFilter.addEventListener('change', filterFeedback);
  }
  
  // Setup Modal Close Handlers
  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', function() {
      const modalId = this.getAttribute('data-close');
      const modal = document.getElementById(modalId);
      if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
        
        // Reload data when closing complaint modals to ensure data is fresh
        if (modalId === 'complaintDetailModal' || modalId === 'complaintDetailsModal') {
          console.log('[MODAL] Complaint modal closed - refreshing data');
          if (typeof loadComplaints === 'function') {
            loadComplaints();
          }
          if (typeof loadDashboardStats === 'function') {
            loadDashboardStats();
          }
        }
      }
    });
  });
  
  // Close modals when clicking outside
  document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', function(e) {
      if (e.target === this) {
        this.classList.remove('active');
        this.style.display = 'none';
        
        // Reload data when closing complaint modals to ensure data is fresh
        if (this.id === 'complaintDetailModal' || this.id === 'complaintDetailsModal') {
          console.log('[MODAL] Complaint modal closed (outside click) - refreshing data');
          if (typeof loadComplaints === 'function') {
            loadComplaints();
          }
          if (typeof loadDashboardStats === 'function') {
            loadDashboardStats();
          }
        }
      }
    });
  });
  
  // Setup Add New District Button
  const addNewDistrictBtn = document.getElementById('addNewDistrictBtn');
  if (addNewDistrictBtn) {
    addNewDistrictBtn.addEventListener('click', addNewDistrict);
  }
  
  // Setup Add New Route Button  
  const addNewRouteBtn = document.getElementById('addNewRouteBtn');
  if (addNewRouteBtn) {
    addNewRouteBtn.addEventListener('click', addNewRoute);
  }
  
  // Update routes when district changes
  const adminDistrictSelect = document.getElementById('adminDistrict');
  if (adminDistrictSelect) {
    adminDistrictSelect.addEventListener('change', function() {
      loadRoutesForDropdown(this.value);
    });
  }
});

function updateThemeIcon(theme) {
  const icon = document.querySelector('#themeToggle i');
  if (icon) {
    icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
  }
}

// Store districts and routes data globally for real-time access
let cachedDistricts = [];
let cachedRoutes = [];

// Load districts for dropdown - REAL-TIME
async function loadDistrictsForDropdown() {
  const token = localStorage.getItem('token');
  if (!token) return;
  
  try {
    const apiBase = getAPIBase();
    const response = await fetch(`${apiBase}/api/districts`, {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    
    if (handle401Error(response, 'loadDistrictsForDropdown')) return;
    
    if (response.ok) {
      const data = await response.json();
      cachedDistricts = data.districts || data || [];
      
      const select = document.getElementById('adminDistrict');
      if (select) {
        const currentValue = select.value;
        select.innerHTML = '<option value="" style="background: #1a1a2e; color: #FFD100;">Select District...</option>';
        
        cachedDistricts.forEach(district => {
          const option = document.createElement('option');
          option.value = district.id;
          option.textContent = district.name;
          option.style.background = '#1a1a2e';
          option.style.color = '#FFD100';
          option.style.fontWeight = '600';
          if (String(district.id) === currentValue) {
            option.selected = true;
          }
          select.appendChild(option);
        });
        
        console.log('[Districts] Loaded', cachedDistricts.length, 'districts');
      }
    }
  } catch (error) {
    console.error('[Districts] Error loading:', error);
  }
}

// Load routes for dropdown - REAL-TIME
async function loadRoutesForDropdown(districtId = null) {
  const token = localStorage.getItem('token');
  if (!token) return;
  
  try {
    const apiBase = getAPIBase();
    let url = `${apiBase}/api/routes`;
    if (districtId) {
      url += `?district_id=${districtId}`;
    }
    
    const response = await fetch(url, {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    
    if (handle401Error(response, 'loadRoutesForDropdown')) return;
    
    if (response.ok) {
      const data = await response.json();
      cachedRoutes = data.routes || data || [];
      
      const select = document.getElementById('adminRoutes');
      if (select) {
        // Store currently selected values
        const selectedValues = Array.from(select.selectedOptions).map(opt => opt.value);
        
        select.innerHTML = '';
        
        if (cachedRoutes.length === 0) {
          const option = document.createElement('option');
          option.value = '';
          option.textContent = 'No routes available';
          option.disabled = true;
          option.style.background = '#1a1a2e';
          option.style.color = '#FFD100';
          option.style.fontWeight = '600';
          select.appendChild(option);
        } else {
          cachedRoutes.forEach(route => {
            const option = document.createElement('option');
            option.value = route.id;
            option.textContent = `${route.name} (${route.code || 'No code'})`;
            option.style.background = '#1a1a2e';
            option.style.color = '#FFD100';
            option.style.fontWeight = '600';
            if (selectedValues.includes(String(route.id))) {
              option.selected = true;
            }
            select.appendChild(option);
          });
        }
        
        console.log('[Routes] Loaded', cachedRoutes.length, 'routes');
      }
    }
  } catch (error) {
    console.error('[Routes] Error loading:', error);
  }
}

// Add new district
async function addNewDistrict() {
  const input = document.getElementById('newDistrictInput');
  const districtName = input?.value.trim();
  
  if (!districtName) {
    showToast('Please enter a district name', 'warning');
    return;
  }
  
  const token = localStorage.getItem('token');
  if (!token) {
    showToast('Authentication required', 'error');
    return;
  }
  
  try {
    const apiBase = getAPIBase();
    // Generate unique code: take first 6 chars + timestamp + random 3 digit suffix to avoid conflicts
    const baseCode = districtName.toUpperCase().replace(/\s+/g, '_').replace(/[^A-Z0-9_]/g, '').substring(0, 6);
    const timestamp = Date.now().toString(36).slice(-4).toUpperCase();
    const randomSuffix = Math.floor(Math.random() * 999).toString().padStart(3, '0');
    const districtCode = baseCode + timestamp + randomSuffix;
    
    console.log('[Add District] Creating district:', districtName, 'with code:', districtCode);
    
    const response = await fetch(`${apiBase}/api/districts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
      },
      body: JSON.stringify({ 
        name: districtName,
        code: districtCode
      })
    });
    
    if (handle401Error(response, 'addNewDistrict')) return;
    
    const data = await response.json();
    
    if (response.ok) {
      showToast(`District "${districtName}" created successfully!`, 'success');
      input.value = '';
      // Reload districts immediately
      await loadDistrictsForDropdown();
      // Select the newly created district
      const select = document.getElementById('adminDistrict');
      if (select && data.id) {
        select.value = data.id;
        // Also load routes for this district
        loadRoutesForDropdown(data.id);
      }
    } else if (response.status === 409) {
      // Conflict - duplicate district
      showToast(`District "${districtName}" already exists in the system!`, 'warning');
      console.error('[Add District] Conflict:', data.error);
    } else {
      showToast(data.error || 'Failed to create district', 'error');
      console.error('[Add District] Error:', data.error);
    }
  } catch (error) {
    console.error('[Add District] Error:', error);
    showToast('Network error: ' + error.message, 'error');
  }
}

// Add new route
async function addNewRoute() {
  const input = document.getElementById('newRouteInput');
  const routeName = input?.value.trim();
  const districtSelect = document.getElementById('adminDistrict');
  const districtId = districtSelect?.value;
  
  if (!routeName) {
    showToast('Please enter a route name', 'warning');
    return;
  }
  
  if (!districtId) {
    showToast('Please select a district first', 'warning');
    return;
  }
  
  const token = localStorage.getItem('token');
  if (!token) {
    showToast('Authentication required', 'error');
    return;
  }
  
  try {
    const apiBase = getAPIBase();
    // Generate unique code: take first 6 chars + timestamp + random 3 digit suffix to avoid conflicts
    const baseCode = routeName.toUpperCase().replace(/\s+/g, '_').replace(/[^A-Z0-9_]/g, '').substring(0, 6);
    const timestamp = Date.now().toString(36).slice(-4).toUpperCase();
    const randomSuffix = Math.floor(Math.random() * 999).toString().padStart(3, '0');
    const routeCode = baseCode + timestamp + randomSuffix;
    
    console.log('[Add Route] Creating route:', routeName, 'with code:', routeCode);
    
    const response = await fetch(`${apiBase}/api/routes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
      },
      body: JSON.stringify({ 
        name: routeName,
        code: routeCode,
        district_id: parseInt(districtId)
      })
    });
    
    if (handle401Error(response, 'addNewRoute')) return;
    
    const data = await response.json();
    
    if (response.ok) {
      showToast(`Route "${routeName}" created successfully!`, 'success');
      input.value = '';
      // Reload routes immediately
      await loadRoutesForDropdown(districtId);
      // Select the newly created route
      const select = document.getElementById('adminRoutes');
      if (select && data.id) {
        // Find and select the new route option
        Array.from(select.options).forEach(opt => {
          if (opt.value == data.id) {
            opt.selected = true;
          }
        });
      }
    } else if (response.status === 409) {
      // Conflict - duplicate route
      showToast(`Route "${routeName}" already exists in this district!`, 'warning');
      console.error('[Add Route] Conflict:', data.error);
    } else {
      showToast(data.error || 'Failed to create route', 'error');
      console.error('[Add Route] Error:', data.error);
    }
  } catch (error) {
    console.error('[Add Route] Error:', error);
    showToast('Network error: ' + error.message, 'error');
  }
}

// Delete selected district
async function deleteSelectedDistrict() {
  const districtSelect = document.getElementById('adminDistrict');
  const districtId = districtSelect?.value;
  
  if (!districtId) {
    showToast('Please select a district to delete', 'warning');
    return;
  }
  
  const districtName = districtSelect.options[districtSelect.selectedIndex].text;
  
  if (!confirm(`Are you sure you want to delete district "${districtName}"?\n\nThis will also delete all routes and buses in this district. This action cannot be undone.`)) {
    return;
  }
  
  const token = localStorage.getItem('token');
  if (!token) {
    showToast('Authentication required', 'error');
    return;
  }
  
  try {
    const apiBase = getAPIBase();
    const response = await fetch(`${apiBase}/api/districts/${districtId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': 'Bearer ' + token
      }
    });
    
    if (handle401Error(response, 'deleteSelectedDistrict')) return;
    
    const data = await response.json();
    
    if (response.ok) {
      showToast(`District "${districtName}" deleted successfully!`, 'success');
      // Reload districts
      await loadDistrictsForDropdown();
      // Clear routes
      const routesSelect = document.getElementById('adminRoutes');
      if (routesSelect) {
        routesSelect.innerHTML = '<option value="">Select Routes...</option>';
      }
    } else {
      showToast(data.error || 'Failed to delete district', 'error');
    }
  } catch (error) {
    console.error('[Delete District] Error:', error);
    showToast('Network error: ' + error.message, 'error');
  }
}

// Delete selected routes
async function deleteSelectedRoutes() {
  const routesSelect = document.getElementById('adminRoutes');
  const selectedOptions = Array.from(routesSelect?.selectedOptions || []);
  
  if (selectedOptions.length === 0) {
    showToast('Please select route(s) to delete', 'warning');
    return;
  }
  
  const routeNames = selectedOptions.map(opt => opt.text).join(', ');
  const routeIds = selectedOptions.map(opt => opt.value);
  
  if (!confirm(`Are you sure you want to delete ${selectedOptions.length} route(s)?\n\n${routeNames}\n\nThis will also delete all buses on these routes. This action cannot be undone.`)) {
    return;
  }
  
  const token = localStorage.getItem('token');
  if (!token) {
    showToast('Authentication required', 'error');
    return;
  }
  
  try {
    const apiBase = getAPIBase();
    let successCount = 0;
    let failCount = 0;
    
    for (const routeId of routeIds) {
      try {
        const response = await fetch(`${apiBase}/api/routes/${routeId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': 'Bearer ' + token
          }
        });
        
        if (response.ok) {
          successCount++;
        } else {
          failCount++;
        }
      } catch (error) {
        console.error(`[Delete Route] Error deleting route ${routeId}:`, error);
        failCount++;
      }
    }
    
    if (successCount > 0) {
      showToast(`${successCount} route(s) deleted successfully!`, 'success');
      // Reload routes
      const districtSelect = document.getElementById('adminDistrict');
      if (districtSelect?.value) {
        await loadRoutesForDropdown(districtSelect.value);
      }
    }
    
    if (failCount > 0) {
      showToast(`Failed to delete ${failCount} route(s)`, 'error');
    }
  } catch (error) {
    console.error('[Delete Routes] Error:', error);
    showToast('Network error: ' + error.message, 'error');
  }
}

// Handle Create Admin Form Submission
async function handleCreateAdmin(e) {
  e.preventDefault();
  
  const name = document.getElementById('adminName').value.trim();
  const email = document.getElementById('adminEmail').value.trim();
  const phone = document.getElementById('adminPhone')?.value.trim() || '';
  const password = document.getElementById('adminPassword').value;
  
  // Get district ID from select dropdown
  const districtSelect = document.getElementById('adminDistrict');
  const districtId = districtSelect?.value;
  const districtName = districtSelect?.options[districtSelect.selectedIndex]?.text || '';
  
  // Get selected route IDs from multi-select
  const routesSelect = document.getElementById('adminRoutes');
  const selectedRouteIds = Array.from(routesSelect?.selectedOptions || []).map(opt => parseInt(opt.value)).filter(id => !isNaN(id));
  
  if (!name || !email || !password || !districtId || selectedRouteIds.length === 0) {
    showToast('Please fill all required fields and select at least one route', 'warning');
    return;
  }
  
  const token = localStorage.getItem('token');
  if (!token) {
    showToast('Authentication required', 'error');
    return;
  }
  
  try {
    const apiBase = getAPIBase();
    console.log('[Create Admin] Submitting...', { name, email, phone, districtId, routeIds: selectedRouteIds });
    
    const response = await fetch(`${apiBase}/api/head/create-admin`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
      },
      body: JSON.stringify({
        name: name,
        email: email,
        password: password,
        phone: phone,
        district_ids: [parseInt(districtId)],
        route_ids: selectedRouteIds
      })
    });
    
    if (handle401Error(response, 'handleCreateAdmin')) return;
    
    const data = await response.json();
    
    if (response.ok) {
      showToast(`Admin "${name}" created successfully with ${selectedRouteIds.length} route(s)!`, 'success');
      document.getElementById('createAdminForm').reset();
      document.getElementById('createAdminModal').style.display = 'none';
      // Reload admin list, stats, districts and routes immediately
      loadAdminList();
      loadDashboardStats();
      loadDistrictsForDropdown();
      loadRoutesForDropdown();
    } else if (response.status === 409) {
      // Conflict - duplicate email
      showToast(`Admin with email "${email}" already exists in the system!`, 'warning');
    } else {
      // Show specific error message
      const errorMsg = data.error || 'Failed to create admin';
      showToast(errorMsg, 'error');
    }
  } catch (error) {
    console.error('[Create Admin] Error:', error);
    showToast('Network error: ' + error.message, 'error');
  }
}

// Load dashboard statistics
async function loadDashboardStats() {
  // Skip if redirecting to login or already loading
  if (isRedirecting || loadingState.stats) {
    console.log('[Stats] Skipping - already loading');
    return;
  }
  
  loadingState.stats = true;
  
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      console.warn('[Stats] No auth token found');
      loadingState.stats = false;
      return;
    }
    
    console.log('[Stats] Loading dashboard statistics...');
    
    // Helper function to update card with smooth transition
    const updateCardValue = (selector, value) => {
      const element = document.querySelector(selector);
      if (element && element.textContent !== String(value)) {
        element.style.opacity = '0.5';
        setTimeout(() => {
          element.textContent = value;
          element.style.opacity = '1';
        }, 100);
      }
    };
    
    // Load total users
    try {
      const apiBase = getAPIBase();
      console.log('[Stats] Fetching users from:', apiBase + '/api/head/users');
      
      // Cancel any pending request
      if (abortControllers.stats) {
        abortControllers.stats.abort();
      }
      abortControllers.stats = new AbortController();
      const controller = abortControllers.stats;
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
      
      const usersRes = await fetch(`${apiBase}/api/head/users`, {
        headers: { 'Authorization': 'Bearer ' + token },
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      if (handle401Error(usersRes, 'loadDashboardStats - users')) return;
      if (usersRes.ok) {
        const usersData = await usersRes.json();
        const totalUsers = usersData.users ? usersData.users.length : 0;
        const totalUsersEl = document.querySelector('#cardTotalUsers');
        if (totalUsersEl) {
          updateCardValue('#cardTotalUsers', totalUsers);
          console.log('[Stats] Total Users:', totalUsers);
        }
      } else {
        console.error('[Stats] Users API failed:', usersRes.status);
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        console.error('[Stats] Users fetch timeout');
        showToast('Network slow - retrying...', 'warning');
      } else {
        console.error('[Stats] Users fetch error:', err);
      }
    }
    
    // Load active admins
    try {
      const apiBase = getAPIBase();
      console.log('[Stats] Fetching admins from:', apiBase + '/api/head/admins');
      const adminsRes = await fetch(`${apiBase}/api/head/admins`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (handle401Error(adminsRes, 'loadDashboardStats - admins')) return;
      if (adminsRes.ok) {
        const adminsData = await adminsRes.json();
        // API returns {admins: [...]} so extract the array
        const adminsArray = adminsData.admins || adminsData || [];
        const activeAdmins = Array.isArray(adminsArray) ? 
          adminsArray.filter(a => a.is_active === 1 || a.is_active === true).length : 0;
        const activeAdminsEl = document.querySelector('#cardActiveAdmins');
        if (activeAdminsEl) {
          activeAdminsEl.textContent = activeAdmins;
          console.log('[Stats] Active Admins:', activeAdmins, 'from', adminsArray.length, 'total');
        }
      } else {
        console.error('[Stats] Admins API failed:', adminsRes.status, await adminsRes.text());
      }
    } catch (err) {
      console.error('[Stats] Admins fetch error:', err);
    }
    
    // Load total complaints
    try {
      const apiBase = getAPIBase();
      console.log('[Stats] Fetching complaints from:', apiBase + '/api/complaints');
      const complaintsRes = await fetch(`${apiBase}/api/complaints`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (handle401Error(complaintsRes, 'loadDashboardStats - complaints')) return;
      if (complaintsRes.ok) {
        const complaintsData = await complaintsRes.json();
        const totalComplaints = complaintsData.complaints ? complaintsData.complaints.length : 0;
        const totalComplaintsEl = document.querySelector('#cardTotalComplaints');
        if (totalComplaintsEl) {
          totalComplaintsEl.textContent = totalComplaints;
          console.log('[Stats] Total Complaints:', totalComplaints);
        }
        
        // Count pending complaints
        const pendingComplaints = complaintsData.complaints ? 
          complaintsData.complaints.filter(c => c.status === 'pending').length : 0;
        const pendingComplaintsEl = document.querySelector('#cardPendingComplaints');
        if (pendingComplaintsEl) {
          pendingComplaintsEl.textContent = pendingComplaints;
          console.log('[Stats] Pending Complaints:', pendingComplaints);
        }
      } else {
        console.error('[Stats] Complaints API failed:', complaintsRes.status, await complaintsRes.text());
      }
    } catch (err) {
      console.error('[Stats] Complaints fetch error:', err);
    }
    
    // Update last refresh timestamp
    const lastRefreshEl = document.getElementById('lastRefresh');
    if (lastRefreshEl) {
      const now = new Date();
      lastRefreshEl.textContent = `Updated: ${now.toLocaleTimeString()}`;
      lastRefreshEl.style.opacity = '0.7';
      setTimeout(() => { lastRefreshEl.style.opacity = '1'; }, 200);
    }
    
    // Reset error counter on successful load
    consecutiveErrors = 0;
    
    console.log('[Stats] All dashboard stats loaded');
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('[Stats] Request cancelled');
    } else {
      console.error('[Stats] Error loading dashboard stats:', error);
      consecutiveErrors++;
      
      // If too many consecutive errors, stop updates and show warning
      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
        console.error('[Stats] Too many consecutive errors, stopping auto-updates');
        if (window.realtimeManager) {
          window.realtimeManager.pause();
        }
        showToast('⚠️ Connection issues detected. Auto-refresh paused.', 'warning');
      }
    }
  } finally {
    loadingState.stats = false;
  }
}

// Navigation link handlers
window.addEventListener('DOMContentLoaded', function() {
  // Handle sidebar navigation clicks
  var navLinks = document.querySelectorAll('.nav-link[data-target]');
  navLinks.forEach(function(link) {
    link.addEventListener('click', function() {
      var target = this.getAttribute('data-target');
      
      // Remove active class from all nav links
      navLinks.forEach(function(l) {
        l.classList.remove('active');
      });
      
      // Add active class to clicked link
      this.classList.add('active');
      
      // Hide all sections
      var sections = document.querySelectorAll('.section');
      sections.forEach(function(s) {
        s.classList.remove('active');
      });
      
      // Show target section
      var targetSection = document.getElementById(target);
      if (targetSection) {
        targetSection.classList.add('active');
      }
      
      // Load section-specific data
      loadSectionData(target);
    });
  });
  
  // Function to load section-specific data
  function loadSectionData(section) {
    switch(section) {
      case 'admin-management':
        if (window.loadAdminList) window.loadAdminList();
        break;
      case 'users-management':
        if (window.loadAllUsers) window.loadAllUsers();
        break;
      case 'complaints-log':
        if (window.loadComplaints) window.loadComplaints();
        break;
      case 'feedback-log':
        if (window.loadAllFeedback) window.loadAllFeedback();
        break;
      case 'overview':
        if (window.loadDashboardStats) window.loadDashboardStats();
        if (window.loadRecentActivity) window.loadRecentActivity();
        break;
    }
  }
});

// Load Admin List
async function loadAdminList() {
  // Skip if redirecting to login or already loading
  if (isRedirecting || loadingState.admins) {
    console.log('[Admins] Skipping - already loading');
    return;
  }
  
  loadingState.admins = true;
  
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      loadingState.admins = false;
      return;
    }
    
    const apiBase = getAPIBase();
    console.log('[Admins] Loading admin list from:', apiBase + '/api/head/admins');
    
    // Cancel any pending request
    if (abortControllers.admins) {
      abortControllers.admins.abort();
    }
    
    abortControllers.admins = new AbortController();
    const timeoutId = setTimeout(() => abortControllers.admins.abort(), 10000);
    
    const res = await fetch(`${apiBase}/api/head/admins`, {
      headers: { 'Authorization': 'Bearer ' + token },
      signal: abortControllers.admins.signal
    });
    
    clearTimeout(timeoutId);
    if (handle401Error(res, 'loadAdminList')) return;
    if (!res.ok) {
      console.error('[Admins] API failed:', res.status);
      return;
    }
    
    const admins = await res.json();
    console.log('[Admins] Loaded:', admins);
    
    // Handle both array and object response format
    const adminList = Array.isArray(admins) ? admins : (admins.admins || []);
    
    if (!Array.isArray(adminList)) {
      console.error('[Admins] Expected array, got:', typeof admins, admins);
      return;
    }
    
    const wrapper = document.getElementById('adminTableWrapper');
    if (!wrapper) {
      console.warn('[Admins] Table wrapper not found');
      return;
    }
    
    let html = `
      <table style="min-width: 1000px;">
        <thead>
          <tr>
            <th class="admin-checkbox-column" style="width: 50px; display: none;">
              <input type="checkbox" id="adminSelectAll" onchange="toggleAdminSelectAll()" style="cursor: pointer;">
            </th>
            <th>ID</th>
            <th>Name</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Info</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
    `;
    
    adminList.forEach(admin => {
      const isActive = admin.is_active === 1 || admin.is_active === true;
      
      html += `
        <tr>
          <td class="admin-checkbox-column" style="display: none;">
            <input type="checkbox" class="admin-checkbox" data-id="${admin.id}" onchange="updateAdminSelectionButtons()" style="cursor: pointer;">
          </td>
          <td>#${admin.id}</td>
          <td>${admin.name || 'N/A'}</td>
          <td>${admin.email || 'N/A'}</td>
          <td>${admin.phone || 'N/A'}</td>
          <td>
            <button class="btn btn-sm btn-primary" 
                    onclick="viewAdminInfo(${admin.id})" 
                    title="View admin information"
                    style="width: 32px; height: 32px; padding: 0; display: flex; align-items: center; justify-content: center;">
              <i class="fas fa-info-circle"></i>
            </button>
          </td>
          <td>
            <div style="display: flex; gap: 6px; justify-content: center;">
              <button class="btn btn-sm btn-primary" 
                      onclick="openMessageModal(${admin.id}, '${admin.name.replace(/'/g, "\\'")}')" 
                      title="Send message to admin"
                      style="width: 36px; height: 36px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 50%;">
                <i class="fas fa-envelope"></i>
              </button>
              <button class="btn btn-sm ${isActive ? 'btn-warning' : 'btn-success'}" 
                      onclick="toggleAdminStatus(${admin.id}, ${isActive})" 
                      title="${isActive ? 'Disable admin access' : 'Enable admin access'}"
                      style="width: 36px; height: 36px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 50%;">
                <i class="fas fa-${isActive ? 'ban' : 'check'}"></i>
              </button>
              <button class="btn btn-sm btn-danger" 
                      onclick="deleteAdmin(${admin.id})" 
                      title="Delete admin account permanently"
                      style="width: 36px; height: 36px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 50%;">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    });
    
    html += '</tbody></table>';
    wrapper.innerHTML = html;
    console.log('[Admins] Table rendered');
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('[Admins] Request cancelled');
    } else {
      console.error('[Admins] Error loading admin list:', error);
      const wrapper = document.getElementById('adminTableWrapper');
      if (wrapper) {
        wrapper.innerHTML = `
          <div style="text-align: center; padding: 40px; color: #ff4444;">
            <i class="fas fa-exclamation-triangle" style="font-size: 32px; margin-bottom: 12px;"></i>
            <p>Failed to load administrators</p>
            <button class="btn btn-primary" onclick="loadAdminList()" style="margin-top: 12px;">
              <i class="fas fa-rotate"></i> Retry
            </button>
          </div>
        `;
      }
      showToast('Failed to load administrators', 'error');
    }
  } finally {
    loadingState.admins = false;
  }
}

// Load All Users
async function loadAllUsers() {
  // Skip if redirecting to login or already loading
  if (isRedirecting || loadingState.users) {
    console.log('[Users] Skipping - already loading');
    return;
  }
  
  loadingState.users = true;
  
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      loadingState.users = false;
      return;
    }
    
    const apiBase = getAPIBase();
    console.log('[Users] Loading user list from:', apiBase + '/api/head/users');
    
    // Cancel any pending request
    if (abortControllers.users) {
      abortControllers.users.abort();
    }
    
    abortControllers.users = new AbortController();
    const timeoutId = setTimeout(() => abortControllers.users.abort(), 10000);
    
    const res = await fetch(`${apiBase}/api/head/users`, {
      headers: { 'Authorization': 'Bearer ' + token },
      signal: abortControllers.users.signal
    });
    
    clearTimeout(timeoutId);
    if (handle401Error(res, 'loadAllUsers')) return;
    if (!res.ok) {
      console.error('[Users] API failed:', res.status);
      return;
    }
    
    const data = await res.json();
    const users = data.users || [];
    console.log('[Users] Loaded:', users.length, 'users');
    
    // Fetch complaints count for each user
    const complaintsRes = await fetch(`${apiBase}/api/complaints`, {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (handle401Error(complaintsRes, 'loadAllUsers - complaints')) return;
    const complaintsData = await complaintsRes.json();
    const complaints = complaintsData.complaints || [];
    
    const wrapper = document.getElementById('usersTableWrapper');
    if (!wrapper) {
      console.warn('[Users] Table wrapper not found');
      return;
    }
    
    let html = `
      <table style="min-width: 900px;">
        <thead>
          <tr>
            <th class="user-checkbox-column" style="width: 50px; display: none;">
              <input type="checkbox" id="userSelectAll" onchange="toggleUserSelectAll()" style="cursor: pointer;">
            </th>
            <th>ID</th>
            <th>Name</th>
            <th>Email</th>
            <th>Complaints</th>
            <th>Created</th>
            <th>Info</th>
            <th>Delete</th>
          </tr>
        </thead>
        <tbody>
    `;
    
    users.forEach(user => {
      const createdDate = user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A';
      const userComplaints = complaints.filter(c => c.user_id === user.id);
      const complaintCount = userComplaints.length;
      
      html += `
        <tr>
          <td class="user-checkbox-column" style="display: none;">
            <input type="checkbox" class="user-checkbox" data-id="${user.id}" onchange="updateUserSelectionButtons()" style="cursor: pointer;">
          </td>
          <td style="cursor: pointer;" onclick="toggleRowCheckbox(this.parentElement)">#${user.id}</td>
          <td>${user.name || 'N/A'}</td>
          <td>${user.email || 'N/A'}</td>
          <td>
            <span style="background: ${complaintCount > 0 ? 'rgba(139,92,246,0.2)' : 'rgba(100,100,100,0.2)'}; color: ${complaintCount > 0 ? '#8b5cf6' : '#888'}; padding: 4px 12px; border-radius: 8px; font-weight: 600;">${complaintCount}</span>
          </td>
          <td>${createdDate}</td>
          <td>
            <button class="btn btn-sm btn-primary" 
                    onclick="event.stopPropagation(); window.viewUserInfo(${user.id})" 
                    title="View full user information"
                    style="width: 36px; height: 36px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 50%;">
              <i class="fas fa-info-circle"></i>
            </button>
          </td>
          <td>
            <button class="btn btn-sm btn-danger" 
                    onclick="event.stopPropagation(); deleteUser(${user.id})" 
                    title="Delete user account"
                    style="width: 36px; height: 36px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 50%;">
              <i class="fas fa-trash"></i>
            </button>
          </td>
        </tr>
      `;
    });
    
    html += '</tbody></table>';
    wrapper.innerHTML = html;
    console.log('[Users] Table rendered');
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('[Users] Request cancelled');
    } else {
      console.error('[Users] Error loading user list:', error);
      const wrapper = document.getElementById('usersTableWrapper');
      if (wrapper) {
        wrapper.innerHTML = `
          <div style="text-align: center; padding: 40px; color: #ff4444;">
            <i class="fas fa-exclamation-triangle" style="font-size: 32px; margin-bottom: 12px;"></i>
            <p>Failed to load users</p>
            <button class="btn btn-primary" onclick="loadAllUsers()" style="margin-top: 12px;">
              <i class="fas fa-rotate"></i> Retry
            </button>
          </div>
        `;
      }
      showToast('Failed to load users', 'error');
    }
  } finally {
    loadingState.users = false;
  }
}

// Load Complaints
async function loadComplaints() {
  // Skip if redirecting to login or already loading
  if (isRedirecting || loadingState.complaints) {
    console.log('[Complaints] Skipping - already loading');
    return;
  }
  
  loadingState.complaints = true;
  
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      loadingState.complaints = false;
      return;
    }
    
    const apiBase = getAPIBase();
    console.log('[Complaints] Loading complaints list from:', apiBase + '/api/complaints');
    
    // Cancel any pending request
    if (abortControllers.complaints) {
      abortControllers.complaints.abort();
    }
    
    abortControllers.complaints = new AbortController();
    const timeoutId = setTimeout(() => abortControllers.complaints.abort(), 10000);
    
    const res = await fetch(`${apiBase}/api/complaints`, {
      headers: { 'Authorization': 'Bearer ' + token },
      signal: abortControllers.complaints.signal
    });
    
    clearTimeout(timeoutId);
    if (handle401Error(res, 'loadComplaints')) return;
    if (!res.ok) {
      console.error('[Complaints] API failed:', res.status);
      return;
    }
    
    const data = await res.json();
    const complaints = data.complaints || [];
    console.log('[Complaints] Loaded:', complaints.length, 'complaints');
    
    const wrapper = document.getElementById('complaintsTableWrapper');
    if (!wrapper) {
      console.warn('[Complaints] Table wrapper not found');
      return;
    }
    
    let html = `
      <table id="complaintsTable">
        <thead>
          <tr>
            <th>ID</th>
            <th>Email</th>
            <th>Assigned Admin</th>
            <th>Status</th>
            <th>Assign</th>
            <th>Details</th>
            <th>Delete</th>
          </tr>
        </thead>
        <tbody>
    `;
    
    if (complaints.length === 0) {
      html += `
        <tr>
          <td colspan="5" style="text-align: center; padding: 20px; color: #888;">
            No complaints found
          </td>
        </tr>
      `;
    } else {
      complaints.forEach(complaint => {
        const assignedAdmin = complaint.assigned_admin_name || complaint.admin_name || 'Not Assigned';
        const userEmail = complaint.user_email || complaint.email || 'N/A';
        const isSelected = selectedComplaintIds.has(complaint.id) ? 'selected-row' : '';
        
        html += `
          <tr data-complaint-id="${complaint.id}" class="${isSelected}">
            <td style="position: relative;">
              <span onclick="toggleComplaintDropdown(${complaint.id}, event)" 
                    style="cursor: pointer; font-weight: 600; color: var(--primary); user-select: none;"
                    id="complaint-id-${complaint.id}">
                #${complaint.id}
              </span>
              <div id="dropdown-${complaint.id}" class="complaint-dropdown" style="display: none; position: absolute; top: 100%; left: 0; background: var(--card-bg); border: 2px solid var(--border); border-radius: 8px; padding: 8px; z-index: 1000; min-width: 120px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                <button onclick="selectComplaint(${complaint.id})" class="btn btn-sm" style="width: 100%; margin-bottom: 4px; padding: 6px 12px; font-size: 12px; background: var(--primary-soft); color: var(--primary); border: 1px solid var(--primary);">
                  <i class="fas fa-check"></i> Select
                </button>
                <button onclick="unselectComplaint(${complaint.id})" class="btn btn-sm" style="width: 100%; padding: 6px 12px; font-size: 12px; background: rgba(239, 91, 91, 0.15); color: var(--red); border: 1px solid var(--red);">
                  <i class="fas fa-times"></i> Unselect
                </button>
              </div>
            </td>
            <td>${userEmail}</td>
            <td>${assignedAdmin}</td>
            <td>${getComplaintStatusBadge(complaint.status || 'pending')}</td>
            <td>
                <button title="${assignedAdmin === 'Not Assigned' ? 'Assign to admin' : 'Reassign or unassign'}" 
                        onclick="openAssignComplaintModal(${complaint.id}, '${assignedAdmin}', ${complaint.assigned_to || 'null'})"
                        style="background: linear-gradient(135deg,${assignedAdmin === 'Not Assigned' ? '#10B981 0%,#059669 100%' : '#F59E0B 0%,#D97706 100%'}); color: white; border: none; width: 30px; height: 30px; padding: 0; display:flex;align-items:center;justify-content:center;border-radius:50%;font-size:13px;box-shadow:0 2px 8px rgba(16,185,129,0.15);">
                    <i class="fas fa-user-plus" style="font-size:12px;"></i>
                </button>
            </td>
                        <td>
                            <button title="View complaint details" onclick="viewComplaintDetails(${complaint.id})"
                                            style="background: linear-gradient(135deg,#00C8FF 0%,#0284C7 100%); color: white; border: none; width: 30px; height: 30px; padding: 0; display:flex;align-items:center;justify-content:center;border-radius:50%;font-size:13px;box-shadow:0 2px 8px rgba(0,200,255,0.15);">
                                    <i class="fas fa-info-circle" style="font-size:14px;"></i>
                            </button>
                        </td>
                        <td>
                            <button title="Delete complaint" onclick="deleteComplaint(${complaint.id})"
                                            style="background: linear-gradient(135deg,#EF4444 0%,#DC2626 100%); color:white; border:none; width: 30px; height:30px; padding:0; display:flex;align-items:center;justify-content:center;border-radius:50%;font-size:13px;box-shadow:0 2px 8px rgba(239,68,68,0.15);">
                                    <i class="fas fa-trash" style="font-size:12px;"></i>
                            </button>
                        </td>
          </tr>
        `;
      });
    }
    
    html += '</tbody></table>';
    wrapper.innerHTML = html;
    
    console.log('[Complaints] Table rendered');
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('[Complaints] Request cancelled');
    } else {
      console.error('[Complaints] Error loading complaints:', error);
      const wrapper = document.getElementById('complaintsTableWrapper');
      if (wrapper) {
        wrapper.innerHTML = `
          <div style="text-align: center; padding: 40px; color: #ff4444;">
            <i class="fas fa-exclamation-triangle" style="font-size: 32px; margin-bottom: 12px;"></i>
            <p>Failed to load complaints</p>
            <button class="btn btn-primary" onclick="loadComplaints()" style="margin-top: 12px;">
              <i class="fas fa-rotate"></i> Retry
            </button>
          </div>
        `;
      }
      showToast('Failed to load complaints', 'error');
    }
  } finally {
    loadingState.complaints = false;
  }
}

// Helper function to get status badge HTML
function getComplaintStatusBadge(status) {
    const badges = {
        pending: { color: '#FFD100', text: 'Pending', icon: 'fa-clock' },
        'in-progress': { color: '#00C8FF', text: 'In Progress', icon: 'fa-spinner' },
        'in_progress': { color: '#00C8FF', text: 'In Progress', icon: 'fa-spinner' },
        resolved: { color: '#10B981', text: 'Resolved', icon: 'fa-check-circle' },
        rejected: { color: '#EF4444', text: 'Rejected', icon: 'fa-times-circle' }
    };
    const badge = badges[status] || badges.pending;
    return `<span style="background: ${badge.color}22; color: ${badge.color}; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;"><i class="fas ${badge.icon}"></i> ${badge.text}</span>`;
}

// View Complaint Details
async function viewComplaintDetails(complaintId) {
    console.log('[VIEW] viewComplaintDetails:', complaintId);
    
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            showToast('Please login first', 'error');
            return;
        }
        
        const apiBase = getAPIBase();
        console.log('[VIEW] Fetching complaint details for ID:', complaintId);
        
        const response = await fetch(`${apiBase}/api/complaints/${complaintId}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to fetch complaint: ${response.status}`);
        }
        
        const complaint = await response.json();
        console.log('[VIEW] Complaint data:', complaint);
        
        // Store globally for delayed modal creation
        window.currentComplaintData = complaint;
        
        // Display complaint details in modal
        displayComplaintDetailsModal(complaint);
        
    } catch (error) {
        console.error('[VIEW] Error loading complaint details:', error);
        showToast('Failed to load complaint details: ' + error.message, 'error');
    }
}
window.viewComplaintDetails = viewComplaintDetails;

function displayComplaintDetailsModal(complaint) {
    console.log('[MODAL] Displaying complaint details with overlay:', complaint);
    
    // CLOSE EXISTING COMPLAINT MODALS FIRST - FORCE CLEANUP
    const existingOverlays = document.querySelectorAll('.modal-overlay');
    existingOverlays.forEach(overlay => {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 100);
    });
    
    // Create modal immediately without delay to prevent re-triggering
    createModalContent();
}

function createModalContent() {
    // This function is called to create modal content
    const complaint = window.currentComplaintData;
    if (!complaint) {
        console.warn('[MODAL] No complaint data available');
        return;
    }
    
    // Check current theme
    const isDarkMode = document.body.classList.contains('dark-theme');
    
    // Theme-aware box styling
    const boxStyle = isDarkMode 
        ? 'background: rgba(20, 20, 20, 0.8); padding: 16px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1);'
        : 'background: rgba(79, 70, 229, 0.15); padding: 16px; border-radius: 12px; border: 1px solid rgba(79, 70, 229, 0.3);';
    
    const textColor = isDarkMode ? '#C0C0C0' : '#fff';
    
    // Fixed z-index - no need to calculate dynamically
    const zIndex = 10010;
    
    // Create overlay container
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    // Set all styles at once to minimize observer triggers
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(7, 4, 16, 0.92);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: ${zIndex};
        animation: fadeIn 0.25s ease;
    `;
    
    // Close on background click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
    
    // Format date helper
    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    };
    
    // Status badge helper
    const getStatusBadge = (status) => {
        const badges = {
            pending: { color: '#FFD100', text: 'Pending', icon: 'fa-clock' },
            'in-progress': { color: '#00C8FF', text: 'In Progress', icon: 'fa-spinner' },
            'in_progress': { color: '#00C8FF', text: 'In Progress', icon: 'fa-spinner' },
            resolved: { color: '#10B981', text: 'Resolved', icon: 'fa-check-circle' },
            rejected: { color: '#EF4444', text: 'Rejected', icon: 'fa-times-circle' }
        };
        const badge = badges[status] || badges.pending;
        return `<span style="background: ${badge.color}22; color: ${badge.color}; padding: 6px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
            <i class="fas ${badge.icon}"></i> ${badge.text}
        </span>`;
    };
    
    // Build media files HTML
    let mediaHTML = '';
    if (complaint.media_files && complaint.media_files.length > 0) {
        const apiBase = window.API_BASE || 'http://127.0.0.1:5000';
        mediaHTML = `
            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
                <h4 style="margin: 0 0 15px 0; color: #C0C0C0; font-size: 15px;">
                    <i class="fas fa-paperclip"></i> Attachments (${complaint.media_files.length})
                </h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px;">
                    ${complaint.media_files.map(file => {
                        const fileUrl = file.file_path.startsWith('http') ? file.file_path : apiBase + (file.file_path.startsWith('/') ? '' : '/') + file.file_path;
                        const isImage = file.mime_type && file.mime_type.startsWith('image/');
                        return isImage ? `
                            <a href="${fileUrl}" target="_blank" style="text-decoration: none;">
                                <img src="${fileUrl}" alt="Attachment" style="width: 100%; height: 120px; object-fit: cover; border-radius: 10px; border: 2px solid rgba(0, 200, 255, 0.3);">
                            </a>
                        ` : `
                            <a href="${fileUrl}" target="_blank" style="display: flex; align-items: center; justify-content: center; height: 120px; background: rgba(0,200,255,0.1); border: 2px solid rgba(0,200,255,0.3); border-radius: 10px; text-decoration: none; color: #00C8FF;">
                                <i class="fas fa-file" style="font-size: 32px;"></i>
                            </a>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }
    
    // Create modal card
    const modalCard = document.createElement('div');
    modalCard.style.cssText = `
        background: linear-gradient(145deg, #1a1a2e 0%, #0f0f1a 100%);
        border: 2px solid rgba(0, 200, 255, 0.3);
        border-radius: 20px;
        width: min(700px, 92%);
        max-height: 85vh;
        overflow-y: auto;
        box-shadow: 0 25px 80px rgba(0, 200, 255, 0.2), 0 0 40px rgba(0, 200, 255, 0.1);
        animation: slideUp 0.3s ease;
    `;
    
    modalCard.innerHTML = `
        <div style="padding: 24px 28px; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 0; color: #00C8FF; font-size: 20px; font-weight: 700;">
                <i class="fas fa-clipboard-list"></i> Complaint #${complaint.id}
            </h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background: rgba(255,255,255,0.1); border: none; color: #fff; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center;">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div style="padding: 28px;">
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                <div style="${boxStyle}">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                        <i class="fas fa-user"></i> User
                    </div>
                    <div style="font-size: 15px; color: #FFD100; font-weight: 600;">${complaint.username || complaint.user_name || 'N/A'}</div>
                </div>
                <div style="${boxStyle}">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                        <i class="fas fa-envelope"></i> Email
                    </div>
                    <div style="font-size: 14px; color: ${textColor};">${complaint.email || 'N/A'}</div>
                </div>
                <div style="${boxStyle}">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                        <i class="fas fa-bus"></i> Bus Number
                    </div>
                    <div style="font-size: 15px; color: #00C8FF; font-weight: 600;">${complaint.bus_number || 'N/A'}</div>
                </div>
                <div style="${boxStyle}">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                        <i class="fas fa-route"></i> Route
                    </div>
                    <div style="font-size: 14px; color: ${textColor};">${complaint.route_name || complaint.route || 'N/A'}</div>
                </div>
                <div style="${boxStyle}">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                        <i class="fas fa-map-marker-alt"></i> District
                    </div>
                    <div style="font-size: 14px; color: ${textColor};">${complaint.district_name || complaint.district || 'N/A'}</div>
                </div>
                <div style="${boxStyle}">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                        <i class="fas fa-user-shield"></i> Assigned Admin
                    </div>
                    <div style="font-size: 14px; color: ${complaint.admin_name || complaint.admin_username ? '#10B981' : '#EF4444'}; font-weight: 500;">
                        ${complaint.admin_name || complaint.admin_username || 'Not Assigned'}
                    </div>
                </div>
                <div style="${boxStyle}">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                        <i class="fas fa-info-circle"></i> Status
                    </div>
                    ${getStatusBadge(complaint.status)}
                    <div style="margin-top: 8px;">
                        <select id="statusUpdateSelect-${complaint.id}" 
                                onchange="updateComplaintStatus(${complaint.id}, this.value)"
                                style="background: rgba(0,200,255,0.1); border: 1px solid rgba(0,200,255,0.3); color: #00C8FF; padding: 6px 10px; border-radius: 6px; font-size: 12px; cursor: pointer; width: 100%;">
                            <option value="" disabled selected>Change Status</option>
                            <option value="pending">Pending</option>
                            <option value="in_progress">In Progress</option>
                            <option value="resolved">Resolved</option>
                            <option value="rejected">Rejected</option>
                        </select>
                    </div>
                </div>
                <div style="${boxStyle}">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                        <i class="fas fa-calendar"></i> Created
                    </div>
                    <div style="font-size: 13px; color: #888;">${formatDate(complaint.created_at)}</div>
                </div>
            </div>
            
            <div style="margin-top: 24px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
                <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 10px; text-transform: uppercase;">
                    <i class="fas fa-align-left"></i> Description
                </div>
                <div style="background: ${isDarkMode ? 'rgba(20, 20, 20, 0.9)' : 'rgba(79, 70, 229, 0.2)'}; padding: 16px; border-radius: 12px; border: 1px solid ${isDarkMode ? 'rgba(255, 255, 255, 0.15)' : 'rgba(79, 70, 229, 0.4)'}; color: ${isDarkMode ? '#C0C0C0' : '#e5e7eb'}; font-size: 14px; line-height: 1.7; white-space: pre-wrap;">
                    ${complaint.description || 'No description provided'}
                </div>
            </div>
            
            ${mediaHTML}
        </div>
        <div style="padding: 20px 28px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: flex-end;">
            <button onclick="this.closest('.modal-overlay').remove()" style="background: linear-gradient(135deg, #6b7280, #4b5563); color: white; border: none; padding: 12px 28px; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 600;">
                <i class="fas fa-times"></i> Close
            </button>
        </div>
    `;
    
    overlay.appendChild(modalCard);
    document.body.appendChild(overlay);
}
window.displayComplaintDetailsModal = displayComplaintDetailsModal;

// ==================== MISSING FILTER FUNCTIONS ====================

// Filter Admins by search and status
function filterAdmins() {
  const searchInput = document.getElementById('adminSearch');
  const statusFilter = document.getElementById('adminStatusFilter');
  const table = document.querySelector('#adminTableWrapper table tbody');
  
  if (!table) return;
  
  const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
  const statusValue = statusFilter ? statusFilter.value : '';
  
  const rows = table.querySelectorAll('tr');
  
  rows.forEach(row => {
    const cells = row.querySelectorAll('td');
    if (cells.length === 0) return;
    
    const name = cells[1] ? cells[1].textContent.toLowerCase() : '';
    const email = cells[2] ? cells[2].textContent.toLowerCase() : '';
    const statusBadge = row.querySelector('.badge');
    const isActive = statusBadge && statusBadge.textContent.trim().toLowerCase() === 'active';
    
    const matchesSearch = name.includes(searchTerm) || email.includes(searchTerm);
    const matchesStatus = !statusValue || 
                         (statusValue === 'active' && isActive) || 
                         (statusValue === 'inactive' && !isActive);
    
    row.style.display = (matchesSearch && matchesStatus) ? '' : 'none';
  });
  
  console.log('[Filter] Admins filtered');
}

// Filter Users by search
function filterUsers() {
  const searchInput = document.getElementById('userSearch');
  const table = document.querySelector('#usersTableWrapper table tbody');
  
  if (!table || !searchInput) return;
  
  const searchTerm = searchInput.value.toLowerCase();
  const rows = table.querySelectorAll('tr');
  
  rows.forEach(row => {
    const cells = row.querySelectorAll('td');
    if (cells.length === 0) return;
    
    const id = cells[0] ? cells[0].textContent.toLowerCase() : '';
    const name = cells[1] ? cells[1].textContent.toLowerCase() : '';
    const email = cells[2] ? cells[2].textContent.toLowerCase() : '';
    
    const matches = id.includes(searchTerm) || name.includes(searchTerm) || email.includes(searchTerm);
    row.style.display = matches ? '' : 'none';
  });
  
  console.log('[Filter] Users filtered');
}

// Filter Complaints by search and status
function filterComplaints() {
  const searchInput = document.getElementById('complaintSearch');
  const statusFilter = document.getElementById('complaintStatusFilter');
  const table = document.querySelector('#complaintsTableWrapper table tbody');
  
  if (!table) return;
  
  const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
  const statusValue = statusFilter ? statusFilter.value : '';
  
  const rows = table.querySelectorAll('tr');
  
  rows.forEach(row => {
    const cells = row.querySelectorAll('td');
    if (cells.length === 0) return;
    
    const id = cells[0] ? cells[0].textContent.toLowerCase() : '';
    const email = cells[1] ? cells[1].textContent.toLowerCase() : '';
    const admin = cells[2] ? cells[2].textContent.toLowerCase() : '';
    
    const matchesSearch = id.includes(searchTerm) || email.includes(searchTerm) || admin.includes(searchTerm);
    
    // For status filter, we need to fetch the actual complaint data or use data attributes
    const complaintId = row.getAttribute('data-complaint-id');
    const matchesStatus = !statusValue; // For now, show all if no status filter
    
    row.style.display = (matchesSearch && matchesStatus) ? '' : 'none';
  });
  
  console.log('[Filter] Complaints filtered');
}

// Filter Feedback by search, status, and rating
function filterFeedback() {
  const searchInput = document.getElementById('feedbackSearch');
  const statusFilter = document.getElementById('feedbackStatusFilter');
  const ratingFilter = document.getElementById('feedbackRatingFilter');
  const table = document.querySelector('#feedbackTableWrapper table tbody');
  
  if (!table) return;
  
  const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
  const statusValue = statusFilter ? statusFilter.value : '';
  const ratingValue = ratingFilter ? ratingFilter.value : '';
  
  const rows = table.querySelectorAll('tr');
  
  rows.forEach(row => {
    const cells = row.querySelectorAll('td');
    if (cells.length === 0) return;
    
    const text = Array.from(cells).map(cell => cell.textContent.toLowerCase()).join(' ');
    const matchesSearch = text.includes(searchTerm);
    
    // Add status and rating matching logic here if needed
    row.style.display = matchesSearch ? '' : 'none';
  });
  
  console.log('[Filter] Feedback filtered');
}

// ==================== MISSING MODAL CLOSE FUNCTION ====================

// Close complaint details modal (for user complaints view)
function closeComplaintDetailsFromUser() {
  const modal = document.getElementById('complaintDetailsFromUserModal');
  if (modal) {
    modal.style.display = 'none';
    modal.classList.remove('active');
    modal.style.zIndex = '';
  }
  console.log('[Modal] Complaint details from user modal closed');
}

// Alias function - use viewComplaintDetails for both
function showComplaintDetailsFromUser(complaintId) {
  return viewComplaintDetails(complaintId);
}

// ==================== EXPORT ALL FUNCTIONS ====================
window.filterAdmins = filterAdmins;
window.filterUsers = filterUsers;
window.filterComplaints = filterComplaints;
window.filterFeedback = filterFeedback;
window.showComplaintDetailsFromUser = showComplaintDetailsFromUser;
window.closeComplaintDetailsFromUser = closeComplaintDetailsFromUser;

//# sourceMappingURL=head_dashboard.js.map


// Export functions to global scope
window.printAdmins = typeof printAdmins !== 'undefined' ? printAdmins : function(){};
window.loadAllFeedback = typeof loadAllFeedback !== 'undefined' ? loadAllFeedback : function(){};
window.printUsers = typeof printUsers !== 'undefined' ? printUsers : function(){};
window.printAllComplaints = typeof printAllComplaints !== 'undefined' ? printAllComplaints : function(){};
window.printFeedback = typeof printFeedback !== 'undefined' ? printFeedback : function(){};

// ============================================
// MISSING FUNCTIONS - COMPLETE IMPLEMENTATION
// ============================================

// Print Admins with professional PDF formatting
function printAdmins() {
    console.log('[PRINT] Downloading admins PDF report');
    
    const token = localStorage.getItem('token');
    if (!token) {
        showToast('Please login again', 'error');
        return;
    }
    
    // Show loading
    const printBtn = document.getElementById('printAdminsBtn');
    if (printBtn) {
        const originalText = printBtn.innerHTML;
        printBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
        printBtn.disabled = true;
        
        // Download PDF from backend
        fetch(`${getAPIBase()}/api/head/export/admins-pdf`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to generate PDF');
            }
            return response.blob();
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `admins_report_${new Date().getTime()}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast('PDF downloaded successfully!', 'success');
        })
        .catch(error => {
            console.error('PDF generation error:', error);
            showToast('Failed to generate PDF', 'error');
        })
        .finally(() => {
            if (printBtn) {
                printBtn.innerHTML = originalText;
                printBtn.disabled = false;
            }
        });
    }
}

// Load All Feedback
async function loadAllFeedback() {
    console.log('[FEEDBACK] loadAllFeedback called');
    try {
        const response = await fetch(`${getAPIBase()}/api/head/feedback`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        const feedbackList = Array.isArray(data) ? data : (data.feedback || []);
        
        console.log('[FEEDBACK] Loaded:', feedbackList.length);
        displayFeedback(feedbackList);
        
    } catch (error) {
        console.error('[FEEDBACK] Error:', error);
        showToast('Failed to load feedback', 'error');
    }
}

// Display Feedback
function displayFeedback(feedbackList) {
    const container = document.getElementById('feedbackContainer');
    if (!container) return;
    
    if (feedbackList.length === 0) {
        container.innerHTML = '<p style="text-align:center; padding:20px; color:#999;">No feedback yet</p>';
        return;
    }
    
    container.innerHTML = feedbackList.map(fb => `
        <div class="feedback-item" style="border:1px solid #ddd; padding:15px; margin:10px 0; border-radius:8px;">
            <div><strong>${fb.user_name || 'Anonymous'}</strong> (${fb.user_email || 'N/A'})</div>
            <div>Rating: ${''.repeat(fb.rating || 0)}</div>
            <div>${fb.message || ''}</div>
            <div style="font-size:0.85em; color:#666;">${new Date(fb.created_at).toLocaleString()}</div>
        </div>
    `).join('');
}

// Show Confirm Modal - Custom styled modal instead of browser confirm
function showConfirmModal(title, message, onConfirm, confirmText = 'Confirm', cancelText = 'Cancel', type = 'warning') {
    console.log('[MODAL] showConfirmModal:', title);
    
    // Remove any existing confirm modal
    const existingModal = document.getElementById('customConfirmModal');
    if (existingModal) existingModal.remove();
    
    // Color schemes based on type
    const colors = {
        warning: { bg: 'rgba(255,209,0,0.2)', border: '#FFD100', icon: 'fa-exclamation-triangle', iconColor: '#FFD100' },
        danger: { bg: 'rgba(239,68,68,0.2)', border: '#EF4444', icon: 'fa-trash-alt', iconColor: '#EF4444' },
        info: { bg: 'rgba(0,200,255,0.2)', border: '#00C8FF', icon: 'fa-info-circle', iconColor: '#00C8FF' },
        success: { bg: 'rgba(16,185,129,0.2)', border: '#10B981', icon: 'fa-check-circle', iconColor: '#10B981' }
    };
    const color = colors[type] || colors.warning;
    
    const modal = document.createElement('div');
    modal.id = 'customConfirmModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(7, 4, 16, 0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        animation: fadeIn 0.2s ease;
    `;
    
    modal.innerHTML = `
        <div style="
            background: linear-gradient(145deg, #1a1a2e 0%, #0f0f1a 100%);
            border: 2px solid ${color.border};
            border-radius: 20px;
            width: min(450px, 90%);
            box-shadow: 0 25px 80px rgba(0,0,0,0.5), 0 0 40px ${color.border}33;
            animation: slideUp 0.25s ease;
            overflow: hidden;
        ">
            <div style="padding: 28px 28px 20px; text-align: center;">
                <div style="
                    width: 70px;
                    height: 70px;
                    background: ${color.bg};
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 20px;
                    border: 2px solid ${color.border}44;
                ">
                    <i class="fas ${color.icon}" style="font-size: 32px; color: ${color.iconColor};"></i>
                </div>
                <h3 style="margin: 0 0 12px; color: #fff; font-size: 20px; font-weight: 700;">${title}</h3>
                <p style="margin: 0; color: #9ca3af; font-size: 15px; line-height: 1.5;">${message}</p>
            </div>
            <div style="padding: 20px 28px 28px; display: flex; gap: 12px;">
                <button id="confirmModalCancel" style="
                    flex: 1;
                    padding: 14px 20px;
                    background: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.2);
                    color: #fff;
                    border-radius: 12px;
                    font-size: 15px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                ">${cancelText}</button>
                <button id="confirmModalConfirm" style="
                    flex: 1;
                    padding: 14px 20px;
                    background: linear-gradient(135deg, ${color.iconColor} 0%, ${color.iconColor}cc 100%);
                    border: none;
                    color: ${type === 'warning' ? '#000' : '#fff'};
                    border-radius: 12px;
                    font-size: 15px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                ">${confirmText}</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Handle cancel
    document.getElementById('confirmModalCancel').onclick = () => {
        modal.remove();
    };
    
    // Handle confirm
    document.getElementById('confirmModalConfirm').onclick = () => {
        modal.remove();
        if (typeof onConfirm === 'function') {
            onConfirm();
        }
    };
    
    // Close on backdrop click
    modal.onclick = (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    };
    
    // Close on Escape key
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            modal.remove();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

// Print Users with professional PDF formatting
function printUsers() {
    console.log('[PRINT] Downloading users PDF report');
    
    const token = localStorage.getItem('token');
    if (!token) {
        showToast('Please login again', 'error');
        return;
    }
    
    // Show loading
    const printBtn = document.getElementById('printUsersBtn');
    if (printBtn) {
        const originalText = printBtn.innerHTML;
        printBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
        printBtn.disabled = true;
        
        // Download PDF from backend
        fetch(`${getAPIBase()}/api/head/export/users-pdf`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to generate PDF');
            }
            return response.blob();
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `users_report_${new Date().getTime()}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast('PDF downloaded successfully!', 'success');
        })
        .catch(error => {
            console.error('PDF generation error:', error);
            showToast('Failed to generate PDF', 'error');
        })
        .finally(() => {
            if (printBtn) {
                printBtn.innerHTML = originalText;
                printBtn.disabled = false;
            }
        });
    }
}

// Print Complaints with professional PDF formatting
function printAllComplaints() {
    console.log('[PRINT] Downloading complaints PDF report');
    
    const token = localStorage.getItem('token');
    if (!token) {
        showToast('Please login again', 'error');
        return;
    }
    
    // Show loading
    const printBtn = document.getElementById('printComplaintsBtn');
    if (printBtn) {
        const originalText = printBtn.innerHTML;
        printBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
        printBtn.disabled = true;
        
        // Download PDF from backend
        fetch(`${getAPIBase()}/api/head/export/complaints-pdf`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to generate PDF');
            }
            return response.blob();
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `complaints_report_${new Date().getTime()}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast('PDF downloaded successfully!', 'success');
        })
        .catch(error => {
            console.error('PDF generation error:', error);
            showToast('Failed to generate PDF', 'error');
        })
        .finally(() => {
            if (printBtn) {
                printBtn.innerHTML = originalText;
                printBtn.disabled = false;
            }
        });
    }
}

// Print Feedback
function printFeedback() {
    console.log('[PRINT] printFeedback called');
    const printContent = document.getElementById('feedbackContainer');
    if (!printContent) {
        showToast('Feedback container not found', 'error');
        return;
    }
    window.print();
}

// Delete User - REMOVED DUPLICATE (See line 2741 for the correct implementation)

// Delete Admin
async function deleteAdmin(adminId) {
    console.log('[DELETE] deleteAdmin:', adminId);
    
    showConfirmModal(
        'Delete Admin',
        'Are you sure you want to delete this admin? This action cannot be undone.',
        async () => {
            try {
                const response = await fetch(`${getAPIBase()}/api/head/admins/${adminId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });
                
                if (response.ok) {
                    showToast('✅ Admin deleted successfully', 'success');
                    loadAdminList();
                    loadDashboardStats();
                } else {
                    const error = await response.json();
                    showToast(error.error || 'Failed to delete admin', 'error');
                }
            } catch (error) {
                console.error('[DELETE] Error:', error);
                showToast('Failed to delete admin', 'error');
            }
        },
        'Delete',
        'Cancel',
        'danger'
    );
}

// Delete Admin - Original implementation removed, using showConfirmModal above
async function deleteAdminOriginal(adminId) {
    // Placeholder to avoid duplicate function errors
    return;
    try {
        const response = await fetch(`${getAPIBase()}/api/head/admins/${adminId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (response.ok) {
            showToast('✅ Admin deleted successfully', 'success');
            // Reload admin list and stats immediately
            loadAdminList();
            loadDashboardStats();
        } else {
            const error = await response.json();
            showToast(error.error || 'Failed to delete admin', 'error');
        }
    } catch (error) {
        console.error('[DELETE] Error:', error);
        showToast('Failed to delete admin', 'error');
    }
}

// Toggle Admin Status
async function toggleAdminStatus(adminId, currentStatus) {
    console.log('[TOGGLE] toggleAdminStatus:', adminId, currentStatus);
    const newStatus = !currentStatus;
    const action = newStatus ? 'enable' : 'disable';
    const actionPast = newStatus ? 'enabled' : 'disabled';
    
    showConfirmModal(
        `${newStatus ? 'Enable' : 'Disable'} Admin`,
        `Are you sure you want to ${action} this admin?`,
        async () => {
            try {
                const response = await fetch(`${getAPIBase()}/api/head/admins/${adminId}/toggle`, {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    showToast(`Admin ${actionPast} successfully`, 'success');
                    loadAdminList();
                    loadDashboardStats();
                } else {
                    throw new Error(`Failed to ${action} admin`);
                }
            } catch (error) {
                console.error('[TOGGLE] Error:', error);
                showToast(`Failed to ${action} admin`, 'error');
            }
        },
        newStatus ? 'Enable' : 'Disable',
        'Cancel',
        newStatus ? 'success' : 'warning'
    );
}

// View Admin Info
async function viewAdminInfo(adminId) {
    try {
        const token = localStorage.getItem('token');
        
        // Fetch admin details and complaints
        const [adminResponse, complaintsResponse] = await Promise.all([
            fetch(`${getAPIBase()}/api/head/admins`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            }),
            fetch(`${getAPIBase()}/api/complaints`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            })
        ]);

        if (adminResponse.status === 401) {
            handle401Error(adminResponse, 'viewAdminInfo');
            return;
        }

        if (!adminResponse.ok) {
            throw new Error('Failed to fetch admin data');
        }

        const adminData = await adminResponse.json();
        const admin = adminData.admins.find(a => a.id === adminId);
        
        if (!admin) {
            showToast('Admin not found', 'error');
            return;
        }
        
        // Debug logging to track district/routes data
        console.log('[ADMIN INFO] Admin data received:', {
            id: admin.id,
            name: admin.name,
            district: admin.district,
            routes: admin.routes
        });
        
        const complaintsData = await complaintsResponse.json();
        const assignedComplaints = (complaintsData.complaints || []).filter(c => c.assigned_to === adminId);
        
        // Get admin assignments from admin data (now included in /admins response)
        const adminDistrict = admin.district || 'Not assigned';
        const adminRoutes = admin.routes || 'Not assigned';
        
        console.log('[ADMIN INFO] Final display values:', { adminDistrict, adminRoutes });
        
        // Calculate z-index based on existing overlays
        const existingOverlays = document.querySelectorAll('.modal-overlay');
        const zIndex = 10005 + (existingOverlays.length * 2);
        
        // Use dark mode styling for both modes (user prefers dark background in all modes)
        const boxBg = 'rgba(0,0,0,0.3)';
        const boxBorder = 'rgba(255,255,255,0.1)';
        
        // Build profile photo URL with full backend API base to avoid 404 on frontend port
        let profilePicUrl = null;
        if (admin.profile_pic) {
            const apiBase = getAPIBase();
            if (admin.profile_pic.startsWith('http')) {
                profilePicUrl = admin.profile_pic;
            } else {
                profilePicUrl = admin.profile_pic.startsWith('/') 
                    ? `${apiBase}${admin.profile_pic}` 
                    : `${apiBase}/${admin.profile_pic}`;
            }
        }
        
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.zIndex = zIndex;
        modal.innerHTML = `
            <div class="modal-content" style="background: linear-gradient(145deg, #1a1a2e 0%, #0f0f1a 100%); border: 2px solid rgba(139, 92, 246, 0.4); border-radius: 20px; padding: 0; max-width: 900px; max-height: 90vh; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.5);">
                <div class="modal-header" style="background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);">
                    <h3>👨‍💼 Admin Details - ${admin.name}</h3>
                    <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">&times;</button>
                </div>
                <div class="modal-body" style="overflow-y: auto;">
                    <!-- Profile Photo Section -->
                    <div style="text-align: center; margin-bottom: 20px;">
                        <div style="width: 100px; height: 100px; margin: 0 auto 10px; border-radius: 50%; overflow: hidden; border: 3px solid #8b5cf6; background: rgba(139, 92, 246, 0.2);">
                            ${profilePicUrl 
                                ? `<img src="${profilePicUrl}" alt="${escapeHtml(admin.name)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                                   <div style="width: 100%; height: 100%; display: none; align-items: center; justify-content: center; font-size: 40px; color: #8b5cf6;">👤</div>`
                                : `<div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 40px; color: #8b5cf6;">👤</div>`
                            }
                        </div>
                        <div style="color: #FFD100; font-weight: 700; font-size: 18px;">${escapeHtml(admin.name)}</div>
                        <div style="color: #9ca3af; font-size: 13px;">${escapeHtml(admin.email)}</div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px;">
                        <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 12px; border: 1px solid ${boxBorder};">
                            <label style="font-weight: 600; color: #9ca3af; display: block; margin-bottom: 8px; font-size: 12px; text-transform: uppercase;">
                                <i class="fas fa-user"></i> Name
                            </label>
                            <div style="color: #FFD100; font-weight: 600; font-size: 16px;">${escapeHtml(admin.name)}</div>
                        </div>
                        <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 12px; border: 1px solid ${boxBorder};">
                            <label style="font-weight: 600; color: #9ca3af; display: block; margin-bottom: 8px; font-size: 12px; text-transform: uppercase;">
                                <i class="fas fa-envelope"></i> Email
                            </label>
                            <div style="color: #00C8FF; font-weight: 500; font-size: 14px; word-break: break-all;">${escapeHtml(admin.email)}</div>
                        </div>
                        <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 12px; border: 1px solid ${boxBorder};">
                            <label style="font-weight: 600; color: #9ca3af; display: block; margin-bottom: 8px; font-size: 12px; text-transform: uppercase;">
                                <i class="fas fa-phone"></i> Phone
                            </label>
                            <div style="color: #8b5cf6; font-weight: 500; font-size: 14px;">${escapeHtml(admin.phone) || 'Not provided'}</div>
                        </div>
                        <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 12px; border: 1px solid ${boxBorder};">
                            <label style="font-weight: 600; color: #9ca3af; display: block; margin-bottom: 8px; font-size: 12px; text-transform: uppercase;">
                                <i class="fas fa-toggle-on"></i> Status
                            </label>
                            <div>
                                <span style="
                                    background: ${admin.is_active ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'};
                                    color: ${admin.is_active ? '#10B981' : '#EF4444'};
                                    padding: 6px 14px;
                                    border-radius: 8px;
                                    font-size: 13px;
                                    font-weight: 600;
                                ">
                                    ${admin.is_active ? '✓ Active' : '✗ Inactive'}
                                </span>
                            </div>
                        </div>
                        <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 12px; border: 1px solid ${boxBorder};">
                            <label style="font-weight: 600; color: #9ca3af; display: block; margin-bottom: 8px; font-size: 12px; text-transform: uppercase;">
                                <i class="fas fa-map-marker-alt"></i> District
                            </label>
                            <div style="color: #FFA500; font-weight: 500; font-size: 14px;">${escapeHtml(adminDistrict)}</div>
                        </div>
                        <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 12px; border: 1px solid ${boxBorder};">
                            <label style="font-weight: 600; color: #9ca3af; display: block; margin-bottom: 8px; font-size: 12px; text-transform: uppercase;">
                                <i class="fas fa-route"></i> Routes
                            </label>
                            <div style="color: #00FF7F; font-weight: 500; font-size: 14px;">${escapeHtml(adminRoutes)}</div>
                        </div>
                        <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 12px; border: 1px solid ${boxBorder};">
                            <label style="font-weight: 600; color: #9ca3af; display: block; margin-bottom: 8px; font-size: 12px; text-transform: uppercase;">
                                <i class="fas fa-calendar"></i> Created
                            </label>
                            <div style="color: #10B981; font-weight: 500; font-size: 14px;">${new Date(admin.created_at).toLocaleDateString()}</div>
                        </div>
                        <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 12px; border: 1px solid ${boxBorder};">
                            <label style="font-weight: 600; color: #9ca3af; display: block; margin-bottom: 8px; font-size: 12px; text-transform: uppercase;">
                                <i class="fas fa-tasks"></i> Total Complaints
                            </label>
                            <div style="color: #8b5cf6; font-weight: 700; font-size: 20px;">${assignedComplaints.length}</div>
                        </div>
                    </div>
                    
                    <h4 style="margin: 20px 0 15px; color: #C0C0C0; font-size: 16px; display: flex; align-items: center; gap: 10px;">
                        <i class="fas fa-clipboard-list"></i> Assigned Complaints
                    </h4>
                    ${assignedComplaints.length > 0 ? `
                        <div style="max-height: 300px; overflow-y: auto; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                            <table style="width: 100%; border-collapse: collapse;">
                                <thead style="background: rgba(139,92,246,0.2); position: sticky; top: 0;">
                                    <tr>
                                        <th style="padding: 12px; text-align: left; color: #C0C0C0; font-size: 12px;">ID</th>
                                        <th style="padding: 12px; text-align: left; color: #C0C0C0; font-size: 12px;">Type</th>
                                        <th style="padding: 12px; text-align: left; color: #C0C0C0; font-size: 12px;">Bus #</th>
                                        <th style="padding: 12px; text-align: left; color: #C0C0C0; font-size: 12px;">Status</th>
                                        <th style="padding: 12px; text-align: left; color: #C0C0C0; font-size: 12px;">Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${assignedComplaints.map(c => `
                                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                            <td style="padding: 12px; color: #FFD100; font-weight: 600;">#${c.id}</td>
                                            <td style="padding: 12px; color: #fff;">${c.complaint_type || 'General'}</td>
                                            <td style="padding: 12px; color: #00C8FF;">${c.bus_number || 'N/A'}</td>
                                            <td style="padding: 12px;">
                                                <span style="
                                                    padding: 4px 10px;
                                                    border-radius: 6px;
                                                    font-size: 11px;
                                                    font-weight: 600;
                                                    background: ${c.status === 'resolved' ? 'rgba(16,185,129,0.2)' : c.status === 'in-progress' ? 'rgba(0,200,255,0.2)' : 'rgba(255,209,0,0.2)'};
                                                    color: ${c.status === 'resolved' ? '#10B981' : c.status === 'in-progress' ? '#00C8FF' : '#FFD100'};
                                                ">${(c.status || 'pending').toUpperCase()}</span>
                                            </td>
                                            <td style="padding: 12px; color: #888; font-size: 13px;">${new Date(c.created_at).toLocaleDateString()}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    ` : '<p style="text-align: center; color: #666; padding: 30px;"><i class="fas fa-inbox" style="font-size: 32px; margin-bottom: 10px; display: block; opacity: 0.5;"></i>No complaints assigned yet</p>'}
                </div>
                <div class="modal-footer" style="display: flex; gap: 10px; justify-content: flex-end; flex-wrap: wrap;">
                    <button style="padding: 10px 20px; background: linear-gradient(135deg, #10B981, #059669); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;" onclick="editAdminDetails(${admin.id}, '${admin.name.replace(/'/g, "\\'")}', '${admin.email.replace(/'/g, "\\'")}', '${(admin.phone || '').replace(/'/g, "\\'")}')">
                        <i class="fas fa-user-edit"></i> Edit Details
                    </button>
                    <button style="padding: 10px 20px; background: linear-gradient(135deg, #FFD100, #FFA500); color: #1a1a2e; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;" onclick="editAdminRoutes(${admin.id}, '${admin.name.replace(/'/g, "\\'")}')">
                        <i class="fas fa-route"></i> Edit Routes
                    </button>
                    <button style="padding: 10px 20px; background: linear-gradient(135deg, #EF4444, #DC2626); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;" onclick="deleteAdminAssignments(${admin.id}, '${admin.name.replace(/'/g, "\\'")}')">
                        <i class="fas fa-trash-alt"></i> Remove Assignments
                    </button>
                    <button style="padding: 10px 20px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; border-radius: 8px; cursor: pointer;" onclick="this.closest('.modal-overlay').remove()">Close</button>
                </div>
            </div>
        `;
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        document.body.appendChild(modal);
        
    } catch (error) {
        console.error('[ADMIN INFO] Error:', error);
        showToast('Failed to load admin info', 'error');
    }
}

window.viewAdminInfo = viewAdminInfo;

// Edit Admin Details - Name, Email, Phone
function editAdminDetails(adminId, currentName, currentEmail, currentPhone) {
    const existingOverlays = document.querySelectorAll('.modal-overlay');
    const zIndex = 10010 + (existingOverlays.length * 2);
    
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.zIndex = zIndex;
    modal.innerHTML = `
        <div class="modal-content" style="background: linear-gradient(145deg, #1a1a2e 0%, #0f0f1a 100%); border: 2px solid rgba(16, 185, 129, 0.4); border-radius: 20px; padding: 0; max-width: 500px; box-shadow: 0 20px 60px rgba(0,0,0,0.5);">
            <div class="modal-header" style="background: linear-gradient(135deg, #10B981 0%, #059669 100%);">
                <h3><i class="fas fa-user-edit"></i> Edit Admin Details</h3>
                <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">&times;</button>
            </div>
            <div class="modal-body" style="padding: 25px;">
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #9ca3af; font-size: 13px;">
                        <i class="fas fa-user"></i> Name
                    </label>
                    <input type="text" id="editAdminName" value="${escapeHtml(currentName)}" 
                        style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff; font-size: 14px;">
                </div>
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #9ca3af; font-size: 13px;">
                        <i class="fas fa-envelope"></i> Email
                    </label>
                    <input type="email" id="editAdminEmail" value="${escapeHtml(currentEmail)}" 
                        style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff; font-size: 14px;">
                </div>
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #9ca3af; font-size: 13px;">
                        <i class="fas fa-phone"></i> Phone
                    </label>
                    <input type="tel" id="editAdminPhone" value="${escapeHtml(currentPhone)}" 
                        style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff; font-size: 14px;">
                </div>
            </div>
            <div class="modal-footer" style="display: flex; gap: 10px; justify-content: flex-end; padding: 20px;">
                <button style="padding: 12px 24px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; border-radius: 8px; cursor: pointer;" onclick="this.closest('.modal-overlay').remove()">
                    Cancel
                </button>
                <button id="saveAdminDetailsBtn" style="padding: 12px 24px; background: linear-gradient(135deg, #10B981, #059669); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                    <i class="fas fa-save"></i> Save Changes
                </button>
            </div>
        </div>
    `;
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
    
    document.body.appendChild(modal);
    
    // Add save handler
    document.getElementById('saveAdminDetailsBtn').addEventListener('click', async () => {
        const name = document.getElementById('editAdminName').value.trim();
        const email = document.getElementById('editAdminEmail').value.trim();
        const phone = document.getElementById('editAdminPhone').value.trim();
        
        if (!name && !email && !phone) {
            showToast('Please enter at least one field to update', 'warning');
            return;
        }
        
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${getAPIBase()}/api/head/admins/${adminId}/details`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, email, phone })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showToast('Admin details updated successfully!', 'success');
                modal.remove();
                // Close parent admin info modal and refresh
                document.querySelectorAll('.modal-overlay').forEach(m => m.remove());
                loadAdminList();
            } else if (response.status === 409) {
                showToast('Email already in use by another user!', 'warning');
            } else {
                showToast(data.error || 'Failed to update admin details', 'error');
            }
        } catch (error) {
            console.error('[Edit Admin] Error:', error);
            showToast('Failed to update admin details', 'error');
        }
    });
}
window.editAdminDetails = editAdminDetails;

// Delete Admin Assignments (District & Routes)
function deleteAdminAssignments(adminId, adminName) {
    const existingOverlays = document.querySelectorAll('.modal-overlay');
    const zIndex = 10010 + (existingOverlays.length * 2);
    
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.zIndex = zIndex;
    modal.innerHTML = `
        <div class="modal-content" style="background: linear-gradient(145deg, #1a1a2e 0%, #0f0f1a 100%); border: 2px solid rgba(239, 68, 68, 0.4); border-radius: 20px; padding: 0; max-width: 450px; box-shadow: 0 20px 60px rgba(0,0,0,0.5);">
            <div class="modal-header" style="background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);">
                <h3><i class="fas fa-exclamation-triangle"></i> Remove Assignments</h3>
                <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">&times;</button>
            </div>
            <div class="modal-body" style="padding: 30px; text-align: center;">
                <i class="fas fa-trash-alt" style="font-size: 48px; color: #EF4444; margin-bottom: 20px;"></i>
                <p style="color: #fff; font-size: 16px; margin-bottom: 10px;">
                    Are you sure you want to remove all district and route assignments for:
                </p>
                <p style="color: #FFD100; font-size: 18px; font-weight: 600;">
                    ${escapeHtml(adminName)}
                </p>
                <p style="color: #9ca3af; font-size: 13px; margin-top: 15px;">
                    This admin will no longer receive any complaint assignments.
                </p>
            </div>
            <div class="modal-footer" style="display: flex; gap: 10px; justify-content: center; padding: 20px;">
                <button style="padding: 12px 24px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; border-radius: 8px; cursor: pointer;" onclick="this.closest('.modal-overlay').remove()">
                    Cancel
                </button>
                <button id="confirmDeleteAssignmentsBtn" style="padding: 12px 24px; background: linear-gradient(135deg, #EF4444, #DC2626); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                    <i class="fas fa-trash-alt"></i> Remove All Assignments
                </button>
            </div>
        </div>
    `;
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
    
    document.body.appendChild(modal);
    
    // Add confirm handler
    document.getElementById('confirmDeleteAssignmentsBtn').addEventListener('click', async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${getAPIBase()}/api/head/admins/${adminId}/assignments`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showToast(`All assignments removed for ${adminName}!`, 'success');
                modal.remove();
                // Close parent admin info modal and refresh
                document.querySelectorAll('.modal-overlay').forEach(m => m.remove());
                loadAdminList();
            } else {
                showToast(data.error || 'Failed to remove assignments', 'error');
            }
        } catch (error) {
            console.error('[Delete Assignments] Error:', error);
            showToast('Failed to remove assignments', 'error');
        }
    });
}
window.deleteAdminAssignments = deleteAdminAssignments;

// Edit Admin Routes - Allows head to assign/update routes for an admin
async function editAdminRoutes(adminId, adminName) {
    try {
        const token = localStorage.getItem('token');
        
        // Fetch routes, districts, and current admin assignments
        const [routesResponse, districtsResponse, assignmentsResponse] = await Promise.all([
            fetch(`${getAPIBase()}/api/routes`, {
                headers: { 'Authorization': `Bearer ${token}` }
            }),
            fetch(`${getAPIBase()}/api/districts`, {
                headers: { 'Authorization': `Bearer ${token}` }
            }),
            fetch(`${getAPIBase()}/api/head/admin-assignments/${adminId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
        ]);

        const routesData = await routesResponse.json();
        const districtsData = await districtsResponse.json();
        const assignmentsData = await assignmentsResponse.json();
        
        const routes = routesData.routes || [];
        const districts = districtsData.districts || [];
        const currentAssignments = assignmentsData.assignments || [];
        
        // Store data globally for use in dynamic functions
        window._editRoutesData = { routes, districts, adminId };
        
        // Calculate z-index
        const existingOverlays = document.querySelectorAll('.modal-overlay');
        const zIndex = 10010 + (existingOverlays.length * 2);
        
        // Create edit modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'editAdminRoutesModal';
        modal.style.zIndex = zIndex;
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px; max-height: 85vh; overflow: hidden;">
                <div class="modal-header">
                    <h3><i class="fas fa-route"></i> Edit Routes for ${adminName}</h3>
                    <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">&times;</button>
                </div>
                <div class="modal-body" style="overflow-y: auto; max-height: 60vh;">
                    <p style="margin-bottom: 15px; color: #9ca3af; font-size: 14px;">
                        Add or modify route assignments for this admin. Select district first, then choose the route.
                    </p>
                    
                    <div id="routeAssignmentsContainer" style="display: flex; flex-direction: column; gap: 12px;">
                        <!-- Dynamic route entries will be added here -->
                    </div>
                    
                    <button type="button" onclick="addRouteAssignmentEntry()" style="
                        margin-top: 15px;
                        padding: 12px 20px;
                        background: linear-gradient(135deg, #10B981, #059669);
                        color: #fff;
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        font-size: 14px;
                        transition: all 0.2s;
                    " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                        <i class="fas fa-plus-circle"></i> Add Another Route
                    </button>
                    
                    <div style="margin-top: 15px; padding: 12px; background: rgba(255,209,0,0.1); border-radius: 8px; border: 1px solid rgba(255,209,0,0.3);">
                        <p style="color: #FFD100; font-size: 13px; margin: 0;">
                            <i class="fas fa-info-circle"></i> <strong>Note:</strong> At least one route must be assigned. The admin will only receive complaints that match their assigned routes.
                        </p>
                    </div>
                </div>
                <div class="modal-footer" style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button class="btn-secondary" style="padding: 10px 20px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; border-radius: 8px; cursor: pointer;" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                    <button id="saveAdminRoutesBtn" class="btn-primary" style="padding: 10px 20px; background: linear-gradient(135deg, #00C8FF, #0088FF); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;" onclick="saveAdminRoutes(${adminId})">
                        <i class="fas fa-save"></i> Save Routes
                    </button>
                </div>
            </div>
        `;
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        document.body.appendChild(modal);
        
        // Add existing assignments as entries
        if (currentAssignments.length > 0) {
            currentAssignments.forEach(assignment => {
                addRouteAssignmentEntry(assignment.district_id, assignment.route_id);
            });
        } else {
            // Add one empty entry if no assignments
            addRouteAssignmentEntry();
        }
        
    } catch (error) {
        console.error('[EDIT ADMIN ROUTES] Error:', error);
        showToast('Failed to load route options', 'error');
    }
}

// Add a new route assignment entry
function addRouteAssignmentEntry(selectedDistrictId = null, selectedRouteId = null) {
    const container = document.getElementById('routeAssignmentsContainer');
    if (!container) return;
    
    const { routes, districts } = window._editRoutesData || { routes: [], districts: [] };
    const entryId = 'route-entry-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    
    const entry = document.createElement('div');
    entry.id = entryId;
    entry.className = 'route-assignment-entry';
    entry.style.cssText = 'display: flex; gap: 12px; align-items: center; padding: 15px; background: rgba(0,0,0,0.3); border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);';
    
    entry.innerHTML = `
        <div style="flex: 1;">
            <label style="display: block; color: #9ca3af; font-size: 12px; margin-bottom: 5px;">District</label>
            <select class="district-select" onchange="updateRouteOptions('${entryId}')" style="
                width: 100%;
                padding: 10px 12px;
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 8px;
                color: #fff;
                font-size: 14px;
                cursor: pointer;
            ">
                <option value="">-- Select District --</option>
                ${districts.map(d => `<option value="${d.id}" ${d.id === selectedDistrictId ? 'selected' : ''}>${d.name}</option>`).join('')}
            </select>
        </div>
        <div style="flex: 1;">
            <label style="display: block; color: #9ca3af; font-size: 12px; margin-bottom: 5px;">Route</label>
            <select class="route-select" style="
                width: 100%;
                padding: 10px 12px;
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 8px;
                color: #fff;
                font-size: 14px;
                cursor: pointer;
            ">
                <option value="">-- Select Route --</option>
            </select>
        </div>
        <button type="button" onclick="removeRouteAssignmentEntry('${entryId}')" style="
            padding: 10px 12px;
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            color: #EF4444;
            cursor: pointer;
            font-size: 14px;
            margin-top: 20px;
            transition: all 0.2s;
        " onmouseover="this.style.background='rgba(239,68,68,0.4)'" onmouseout="this.style.background='rgba(239,68,68,0.2)'" title="Remove this route">
            <i class="fas fa-trash"></i>
        </button>
    `;
    
    container.appendChild(entry);
    
    // If district is pre-selected, update routes
    if (selectedDistrictId) {
        updateRouteOptions(entryId, selectedRouteId);
    }
}

// Update route options based on selected district
function updateRouteOptions(entryId, preSelectedRouteId = null) {
    const entry = document.getElementById(entryId);
    if (!entry) return;
    
    const { routes } = window._editRoutesData || { routes: [] };
    const districtSelect = entry.querySelector('.district-select');
    const routeSelect = entry.querySelector('.route-select');
    
    const districtId = parseInt(districtSelect.value);
    
    // Filter routes by district
    const filteredRoutes = districtId ? routes.filter(r => r.district_id === districtId) : [];
    
    routeSelect.innerHTML = `
        <option value="">-- Select Route --</option>
        ${filteredRoutes.map(r => `<option value="${r.id}" ${r.id === preSelectedRouteId ? 'selected' : ''}>${r.name}</option>`).join('')}
    `;
}

// Remove a route assignment entry
function removeRouteAssignmentEntry(entryId) {
    const container = document.getElementById('routeAssignmentsContainer');
    const entry = document.getElementById(entryId);
    
    if (container && entry) {
        // Ensure at least one entry remains
        const entries = container.querySelectorAll('.route-assignment-entry');
        if (entries.length <= 1) {
            showToast('At least one route assignment is required', 'warning');
            return;
        }
        entry.remove();
    }
}

// Make functions globally available
window.addRouteAssignmentEntry = addRouteAssignmentEntry;
window.updateRouteOptions = updateRouteOptions;
window.removeRouteAssignmentEntry = removeRouteAssignmentEntry;

window.editAdminRoutes = editAdminRoutes;

// Save Admin Routes
async function saveAdminRoutes(adminId) {
    try {
        const token = localStorage.getItem('token');
        
        // Get all route entries from the dynamic form
        const container = document.getElementById('routeAssignmentsContainer');
        const entries = container.querySelectorAll('.route-assignment-entry');
        const routeIds = [];
        
        entries.forEach(entry => {
            const routeSelect = entry.querySelector('.route-select');
            if (routeSelect && routeSelect.value) {
                const routeId = parseInt(routeSelect.value);
                if (routeId && !routeIds.includes(routeId)) {
                    routeIds.push(routeId);
                }
            }
        });
        
        if (routeIds.length === 0) {
            showToast('Please select at least one route', 'warning');
            return;
        }
        
        // Show loading
        const saveBtn = document.getElementById('saveAdminRoutesBtn');
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        saveBtn.disabled = true;
        
        const response = await fetch(`${getAPIBase()}/api/head/admins/${adminId}/routes`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ route_ids: routeIds })
        });
        
        if (response.ok) {
            const result = await response.json();
            showToast(`Routes updated successfully! ${result.assigned_routes} route(s) assigned.`, 'success');
            
            // Close the edit modal
            const editModal = document.getElementById('editAdminRoutesModal');
            if (editModal) editModal.remove();
            
            // Close the info modal too and refresh admin list
            const infoModals = document.querySelectorAll('.modal-overlay');
            infoModals.forEach(m => m.remove());
            
            // Refresh admin list - use the correct function name
            if (typeof loadAdminList === 'function') {
                await loadAdminList();
                console.log('[SAVE ADMIN ROUTES] Admin list refreshed after route update');
            }
        } else {
            const error = await response.json();
            showToast(error.error || 'Failed to update routes', 'error');
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
        }
        
    } catch (error) {
        console.error('[SAVE ADMIN ROUTES] Error:', error);
        showToast('Failed to save routes', 'error');
        
        // Reset button
        const saveBtn = document.getElementById('saveAdminRoutesBtn');
        if (saveBtn) {
            saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Routes';
            saveBtn.disabled = false;
        }
    }
}

window.saveAdminRoutes = saveAdminRoutes;

function displayAdminInfoModal(admin) {
    const modal = document.getElementById('adminProfileModal');
    const body = document.getElementById('adminProfileBody');
    const header = modal.querySelector('.modal-header h3');
    
    if (!modal || !body) return;
    
    // Update modal title for admin
    if (header) header.textContent = 'Admin Information';

    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getStatusBadge = (status) => {
        const isActive = status === 'active' || status === true || status === 1;
        return `
            <span style="
                background: ${isActive ? '#10B98122' : '#EF444422'};
                color: ${isActive ? '#10B981' : '#EF4444'};
                padding: 6px 14px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            ">
                <i class="fas fa-${isActive ? 'check-circle' : 'times-circle'}"></i>
                ${isActive ? 'Active' : 'Inactive'}
            </span>
        `;
    };

    // Determine if in dark mode for box styling
    const isDarkMode = document.body.classList.contains('dark-mode');
    const boxBg = isDarkMode ? 'rgba(0,0,0,0.2)' : 'rgba(79, 70, 229, 0.1)'; // Indigo blue for light mode
    const boxBorder = isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(79, 70, 229, 0.3)'; // Indigo border for light mode

    body.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 20px;">
            <!-- Admin Header -->
            <div style="
                background: linear-gradient(135deg, rgba(255, 209, 0, 0.15) 0%, rgba(255, 165, 0, 0.15) 100%);
                border-left: 4px solid #FFD100;
                padding: 20px;
                border-radius: 12px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h4 style="margin: 0 0 8px 0; color: #FFD100; font-size: 20px; font-weight: 700;">
                            ${admin.name || 'N/A'}
                        </h4>
                        <p style="margin: 0; color: #9ca3af; font-size: 14px;">
                            <i class="fas fa-id-badge"></i> Admin ID: #${admin.id}
                        </p>
                    </div>
                    <div>
                        ${getStatusBadge(admin.status)}
                    </div>
                </div>
            </div>

            <!-- Admin Details Grid -->
            <div style="
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
            ">
                <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 10px; border: 1px solid ${boxBorder};">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;">
                        <i class="fas fa-envelope"></i> EMAIL
                    </div>
                    <div style="color: #00C8FF; font-weight: 600; font-size: 14px; word-break: break-all;">
                        ${admin.email || 'N/A'}
                    </div>
                </div>
                <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 10px; border: 1px solid ${boxBorder};">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;">
                        <i class="fas fa-map-marker-alt"></i> DISTRICT
                    </div>
                    <div style="color: #FFD100; font-weight: 600; font-size: 14px;">
                        ${admin.district || 'N/A'}
                    </div>
                </div>
                <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 10px; border: 1px solid ${boxBorder};">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;">
                        <i class="fas fa-route"></i> ROUTES
                    </div>
                    <div style="color: #8b5cf6; font-weight: 600; font-size: 14px;">
                        ${admin.routes || 'N/A'}
                    </div>
                </div>
                <div class="admin-detail-box" style="background: ${boxBg}; padding: 16px; border-radius: 10px; border: 1px solid ${boxBorder};">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;">
                        <i class="fas fa-calendar"></i> REGISTERED
                    </div>
                    <div style="color: #fff; font-weight: 500; font-size: 13px;">
                        ${formatDate(admin.created_at)}
                    </div>
                </div>
            </div>
        </div>
    `;

    modal.classList.add('active');
}

// Open Message Modal
function openMessageModal(adminId, adminName) {
    const modal = document.getElementById('adminMessageModal');
    const title = document.getElementById('messageModalTitle');
    const meta = document.getElementById('messageRecipientMeta');
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendMessageBtn');
    
    if (!modal) return;

    // Set modal title and meta info
    if (title) title.textContent = `Message to ${adminName}`;
    if (meta) meta.innerHTML = `<i class="fas fa-user"></i> Admin ID: #${adminId}`;
    if (input) input.value = '';

    // Update send button click handler
    if (sendBtn) {
        sendBtn.onclick = () => sendMessageToAdmin(adminId, adminName);
    }

    modal.classList.add('active');
}
window.openMessageModal = openMessageModal;

async function sendMessageToAdmin(adminId, adminName) {
    const input = document.getElementById('messageInput');
    const message = input?.value?.trim();

    if (!message) {
        showToast('Please enter a message', 'warning');
        return;
    }

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${getAPIBase()}/api/messages/send`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recipient_id: adminId,
                recipient_type: 'admin',
                message: message
            })
        });

        if (response.status === 401) {
            handle401Error(response, 'sendMessageToAdmin');
            return;
        }

        if (response.ok) {
            showToast(`Message sent to ${adminName}`, 'success');
            document.getElementById('adminMessageModal').classList.remove('active');
            if (input) input.value = '';
        } else {
            const error = await response.json();
            showToast(error.error || 'Failed to send message', 'error');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        showToast('Failed to send message', 'error');
    }
}

// View User Info
async function viewUserInfo(userId) {
    try {
        const token = localStorage.getItem('token');
        
        // Fetch user info and complaints
        const [userResponse, complaintsResponse] = await Promise.all([
            fetch(`${getAPIBase()}/api/head/users`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            }),
            fetch(`${getAPIBase()}/api/head/complaints`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            })
        ]);

        if (userResponse.status === 401 || complaintsResponse.status === 401) {
            handle401Error(userResponse, 'viewUserInfo');
            return;
        }

        if (!userResponse.ok || !complaintsResponse.ok) {
            throw new Error('Failed to fetch user data');
        }

        const userData = await userResponse.json();
        const complaintsData = await complaintsResponse.json();

        // Find the specific user
        const user = userData.users?.find(u => u.id === userId);
        if (!user) {
            showToast('User not found', 'error');
            return;
        }

        // Filter complaints for this user
        const userComplaints = complaintsData.complaints?.filter(c => c.user_id === userId) || [];

        // Display user info modal
        displayUserInfoModal(user, userComplaints);
    } catch (error) {
        console.error('Error loading user info:', error);
        showToast('Failed to load user information', 'error');
    }
}
window.viewUserInfo = viewUserInfo;

function displayUserInfoModal(user, complaints) {
    console.log('[MODAL] Displaying user info with overlay:', user);
    
    // Calculate z-index for stacking
    const existingOverlays = document.querySelectorAll('.modal-overlay');
    const zIndex = 10010 + (existingOverlays.length * 2);
    
    // Create overlay container
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay user-info-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(7, 4, 16, 0.92);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: ${zIndex};
        animation: fadeIn 0.25s ease;
    `;
    
    // Close on background click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });

    const totalComplaints = complaints.length;
    
    const getStatusBadge = (status) => {
        const badges = {
            pending: { color: '#FFD100', text: 'Pending', icon: 'fa-clock' },
            'in-progress': { color: '#00C8FF', text: 'In Progress', icon: 'fa-spinner' },
            'in_progress': { color: '#00C8FF', text: 'In Progress', icon: 'fa-spinner' },
            resolved: { color: '#10B981', text: 'Resolved', icon: 'fa-check-circle' },
            rejected: { color: '#EF4444', text: 'Rejected', icon: 'fa-times-circle' }
        };
        const badge = badges[status] || badges.pending;
        return `<span style="background: ${badge.color}22; color: ${badge.color}; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
            <i class="fas ${badge.icon}"></i> ${badge.text}
        </span>`;
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    };

    // Create modal card
    const modalCard = document.createElement('div');
    modalCard.style.cssText = `
        background: linear-gradient(145deg, #1a1a2e 0%, #0f0f1a 100%);
        border: 2px solid rgba(139, 92, 246, 0.4);
        border-radius: 20px;
        width: min(700px, 92%);
        max-height: 85vh;
        overflow-y: auto;
        box-shadow: 0 25px 80px rgba(139, 92, 246, 0.2), 0 0 40px rgba(139, 92, 246, 0.1);
        animation: slideUp 0.3s ease;
    `;
    
    modalCard.innerHTML = `
        <div style="padding: 24px 28px; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 0; color: #8b5cf6; font-size: 20px; font-weight: 700;">
                <i class="fas fa-user"></i> User Information
            </h3>
            <button class="close-user-modal-btn" style="background: rgba(255,255,255,0.1); border: none; color: #fff; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; transition: all 0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.2)'" onmouseout="this.style.background='rgba(255,255,255,0.1)'">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div style="padding: 28px;">
            <!-- User Info Grid -->
            <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%); border: 2px solid rgba(139, 92, 246, 0.4); border-radius: 16px; padding: 24px; margin-bottom: 20px;">
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                    <div>
                        <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                            <i class="fas fa-user"></i> User Name
                        </div>
                        <div style="font-size: 16px; color: #FFD100; font-weight: 600;">${user.name || 'N/A'}</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                            <i class="fas fa-envelope"></i> Email
                        </div>
                        <div style="font-size: 14px; color: #fff; font-weight: 500;">${user.email || 'N/A'}</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                            <i class="fas fa-phone"></i> Phone
                        </div>
                        <div style="font-size: 14px; color: #00C8FF; font-weight: 500;">${user.phone || 'N/A'}</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                            <i class="fas fa-exclamation-circle"></i> Total Complaints
                        </div>
                        <div style="font-size: 16px; color: #8b5cf6; font-weight: 700;">${totalComplaints}</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                            <i class="fas fa-user-tag"></i> Role
                        </div>
                        <div style="font-size: 14px; color: #fff; font-weight: 500;">User</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase;">
                            <i class="fas fa-calendar"></i> Registration Date
                        </div>
                        <div style="font-size: 13px; color: #888; font-weight: 500;">${formatDate(user.created_at)}</div>
                    </div>
                </div>
            </div>

            <!-- Complaints History -->
            <div style="background: rgba(0, 0, 0, 0.2); border: 2px solid rgba(139, 92, 246, 0.3); border-radius: 16px; padding: 24px;">
                <h4 style="margin: 0 0 20px 0; color: #C0C0C0; font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 10px;">
                    <i class="fas fa-history"></i> Complaint History
                    <span style="background: rgba(139, 92, 246, 0.3); color: #8b5cf6; padding: 4px 12px; border-radius: 8px; font-size: 14px; font-weight: 700;">
                        ${totalComplaints} Total
                    </span>
                </h4>
                ${totalComplaints === 0 ? `
                    <div style="text-align: center; padding: 40px 20px; color: #666;">
                        <i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 16px; opacity: 0.3;"></i>
                        <p style="font-size: 16px; margin: 0;">No complaints found</p>
                    </div>
                ` : `
                    <div style="overflow-x: auto; max-height: 300px; overflow-y: auto;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: rgba(139, 92, 246, 0.1); border-bottom: 2px solid rgba(139, 92, 246, 0.3);">
                                    <th style="padding: 12px; text-align: left; font-size: 13px; color: #9ca3af; font-weight: 600;">#</th>
                                    <th style="padding: 12px; text-align: left; font-size: 13px; color: #9ca3af; font-weight: 600;">Date</th>
                                    <th style="padding: 12px; text-align: left; font-size: 13px; color: #9ca3af; font-weight: 600;">Category</th>
                                    <th style="padding: 12px; text-align: left; font-size: 13px; color: #9ca3af; font-weight: 600;">Status</th>
                                    <th style="padding: 12px; text-align: center; font-size: 13px; color: #9ca3af; font-weight: 600;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${complaints.map((complaint, index) => `
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                                        <td style="padding: 12px; color: #fff; font-weight: 600;">${complaint.id}</td>
                                        <td style="padding: 12px; color: #888; font-size: 12px;">${formatDate(complaint.created_at)}</td>
                                        <td style="padding: 12px; color: #FFD100; font-weight: 500;">${complaint.category || 'N/A'}</td>
                                        <td style="padding: 12px;">${getStatusBadge(complaint.status)}</td>
                                        <td style="padding: 12px; text-align: center;">
                                            <button onclick="viewComplaintFromUserOverlay(${complaint.id})"
                                                title="View details"
                                                style="background: linear-gradient(135deg,#00C8FF 0%,#0284C7 100%); color:white; border:none; width:30px; height:30px; padding:0; display:inline-flex; align-items:center; justify-content:center; border-radius:50%; font-size:13px; cursor:pointer;">
                                                <i class="fas fa-info-circle" style="font-size:14px;"></i>
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `}
            </div>
        </div>
        <div style="padding: 20px 28px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; gap: 12px;">
            <button class="delete-user-btn" data-user-id="${user.id}" 
                style="background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 600; flex: 1; transition: all 0.3s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(239,68,68,0.4)'" onmouseout="this.style.transform=''; this.style.boxShadow=''">
                <i class="fas fa-trash-alt"></i> Delete User
            </button>
            <button class="close-user-modal-btn" 
                style="background: linear-gradient(135deg, #6b7280, #4b5563); color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 600; flex: 1; transition: all 0.3s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform=''">
                <i class="fas fa-times"></i> Close
            </button>
        </div>
    `;
    
    overlay.appendChild(modalCard);
    document.body.appendChild(overlay);

    // Wire up close buttons (created via innerHTML, need explicit listeners)
    modalCard.querySelectorAll('.close-user-modal-btn').forEach(btn => {
        btn.addEventListener('click', () => overlay.remove());
    });
    // Wire up delete user button
    const deleteUserBtn = modalCard.querySelector('.delete-user-btn');
    if (deleteUserBtn) {
        deleteUserBtn.addEventListener('click', () => {
            const userId = parseInt(deleteUserBtn.getAttribute('data-user-id'));
            if (userId) deleteUser(userId);
        });
    }
}

// View complaint from user modal - keeps user modal open, shows on top
async function viewComplaintFromUserOverlay(complaintId) {
    console.log('[VIEW] viewComplaintFromUserOverlay:', complaintId);
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${getAPIBase()}/api/complaints/${complaintId}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.status === 401) {
            handle401Error(response, 'viewComplaintFromUserOverlay');
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to fetch complaint details');
        }

        const complaint = await response.json();
        displayComplaintInUserOverlay(complaint);
    } catch (error) {
        console.error('Error loading complaint details:', error);
        showToast('Failed to load complaint details', 'error');
    }
}
window.viewComplaintFromUserOverlay = viewComplaintFromUserOverlay;

// Display complaint details in overlay above user modal
function displayComplaintInUserOverlay(complaint) {
    const modal = document.getElementById('complaintDetailsFromUserModal');
    const body = document.getElementById('complaintDetailsFromUserBody');
    
    if (!modal || !body) return;

    const getStatusBadge = (status) => {
        const badges = {
            pending: { color: '#FFD100', text: 'Pending', icon: 'fa-clock' },
            'in-progress': { color: '#00C8FF', text: 'In Progress', icon: 'fa-spinner' },
            'in_progress': { color: '#00C8FF', text: 'In Progress', icon: 'fa-spinner' },
            resolved: { color: '#10B981', text: 'Resolved', icon: 'fa-check-circle' },
            rejected: { color: '#EF4444', text: 'Rejected', icon: 'fa-times-circle' }
        };
        const badge = badges[status] || badges.pending;
        return `
            <span style="
                background: ${badge.color}22;
                color: ${badge.color};
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            ">
                <i class="fas ${badge.icon}"></i>
                ${badge.text}
            </span>
        `;
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const buildMediaGallery = () => {
        if (!complaint.media_files || complaint.media_files.length === 0) {
            return '<p style="color: #666; text-align: center; padding: 20px;">No media files attached</p>';
        }

        return complaint.media_files.map(file => {
            // CRITICAL FIX: Use file_path (hashed) instead of file_name (original) for fetching
            // The file_path in database holds the actual path needed by the server
            const filePath = typeof file === 'string' ? file : (file.file_path || file.file_name || file.filename || '');
            
            if (!filePath || typeof filePath !== 'string') {
                console.warn('[MEDIA] Invalid file format:', file);
                return '';
            }
            
            // Build full URL. Ensure no double slashes and correct prefix
            let fileUrl = filePath;
            if (!fileUrl.startsWith('http')) {
                const apiBase = getAPIBase();
                // If it already has uploads/ prefix, just append it to apiBase
                if (fileUrl.startsWith('uploads/')) {
                    fileUrl = `${apiBase}/${fileUrl}`;
                } else {
                    fileUrl = `${apiBase}/uploads/${fileUrl.startsWith('/') ? fileUrl.substring(1) : fileUrl}`;
                }
            }
            const fileExt = fileName.split('.').pop().toLowerCase();
            
            if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fileExt)) {
                return `
                    <div style="position: relative; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" class="media-container">
                        <img src="${fileUrl}" alt="Evidence" style="width: 100%; height: 200px; object-fit: cover; cursor: pointer;" onclick="window.open('${fileUrl}', '_blank')" onerror="this.style.display='none'; this.nextElementSibling.style.display='none'; const err = document.createElement('div'); err.style.cssText='padding:20px;text-align:center;color:#ef4444'; err.innerHTML='<i class=&quot;fas fa-exclamation-circle&quot; style=&quot;font-size:32px;margin-bottom:8px&quot;></i><p>Image not found</p>'; this.parentElement.appendChild(err);">
                        <div style="position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.7); padding: 4px 8px; border-radius: 6px; font-size: 11px;">
                            <i class="fas fa-image"></i> Image
                        </div>
                    </div>
                `;
            } else if (fileExt === 'pdf') {
                return `
                    <div style="background: rgba(239, 68, 68, 0.1); border: 2px solid #ef4444; border-radius: 12px; padding: 20px; text-align: center; cursor: pointer;" onclick="window.open('${fileUrl}', '_blank')">
                        <i class="fas fa-file-pdf" style="font-size: 48px; color: #ef4444; margin-bottom: 12px;"></i>
                        <p style="margin: 0; color: #ef4444; font-weight: 600; font-size: 14px;">View PDF Document</p>
                    </div>
                `;
            } else if (['mp4', 'webm', 'mov'].includes(fileExt)) {
                return `
                    <div style="border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" class="media-container">
                        <video controls style="width: 100%; max-height: 300px; background: #000;" onerror="this.style.display='none'; const err = document.createElement('div'); err.style.cssText='padding:20px;text-align:center;color:#ef4444'; err.innerHTML='<i class=&quot;fas fa-exclamation-circle&quot; style=&quot;font-size:32px;margin-bottom:8px&quot;></i><p>Video not found</p>'; this.parentElement.appendChild(err);">
                            <source src="${fileUrl}" type="video/${fileExt}">
                            Your browser does not support video playback.
                        </video>
                    </div>
                `;
            } else {
                return `
                    <div style="background: rgba(100, 116, 139, 0.1); border: 2px solid #64748b; border-radius: 12px; padding: 20px; text-align: center; cursor: pointer;" onclick="window.open('${fileUrl}', '_blank')">
                        <i class="fas fa-file" style="font-size: 48px; color: #64748b; margin-bottom: 12px;"></i>
                        <p style="margin: 0; color: #64748b; font-weight: 600; font-size: 14px;">Download File</p>
                    </div>
                `;
            }
        }).join('');
    };

    // Calculate appropriate z-index (higher than user info modal)
    const userOverlays = document.querySelectorAll('.user-info-overlay');
    const baseZIndex = userOverlays.length > 0 ? parseInt(getComputedStyle(userOverlays[userOverlays.length - 1]).zIndex || '10010') : 10010;
    const complaintModalZIndex = baseZIndex + 100;
    
    body.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 24px;">
            <!-- Complaint Header -->
            <div style="background: linear-gradient(135deg, rgba(255, 209, 0, 0.15) 0%, rgba(255, 165, 0, 0.15) 100%); border-left: 4px solid #FFD100; padding: 20px; border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px;">
                    <div>
                        <h4 style="margin: 0 0 8px 0; color: #FFD100; font-size: 20px; font-weight: 700;">Complaint #${complaint.id}</h4>
                        <p style="margin: 0; color: #9ca3af; font-size: 14px;"><i class="fas fa-user"></i> ${complaint.user_name || complaint.name || 'Anonymous'}</p>
                    </div>
                    <div style="text-align: right;">
                        ${getStatusBadge(complaint.status)}
                        <p style="margin: 8px 0 0 0; font-size: 13px; color: #888;"><i class="fas fa-calendar"></i> ${formatDate(complaint.created_at)}</p>
                    </div>
                </div>
            </div>

            <!-- Complaint Details Grid -->
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;"><i class="fas fa-envelope"></i> EMAIL</div>
                    <div style="color: #fff; font-weight: 500; font-size: 14px;">${complaint.email || 'N/A'}</div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;"><i class="fas fa-tag"></i> CATEGORY</div>
                    <div style="color: #FFD100; font-weight: 600; font-size: 15px;">${complaint.category || 'N/A'}</div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;"><i class="fas fa-map-marker-alt"></i> DISTRICT</div>
                    <div style="color: #00C8FF; font-weight: 600; font-size: 15px;">${complaint.district || 'N/A'}</div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;"><i class="fas fa-route"></i> ROUTE</div>
                    <div style="color: #10B981; font-weight: 600; font-size: 15px;">${complaint.route || 'N/A'}</div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;"><i class="fas fa-bus"></i> BUS NO</div>
                    <div style="color: #f59e0b; font-weight: 600; font-size: 15px;">${complaint.bus_no || 'N/A'}</div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;"><i class="fas fa-user-tie"></i> ASSIGNED ADMIN</div>
                    <div style="color: #8b5cf6; font-weight: 600; font-size: 15px;">${complaint.admin_name || 'Unassigned'}</div>
                </div>
            </div>

            <!-- Description -->
            <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="font-size: 13px; color: #9ca3af; font-weight: 600; margin-bottom: 12px; text-transform: uppercase;"><i class="fas fa-align-left"></i> Description</div>
                <p style="color: #d1d5db; line-height: 1.7; margin: 0; font-size: 15px;">${complaint.description || 'No description provided'}</p>
            </div>

            <!-- Media Gallery -->
            <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="font-size: 13px; color: #9ca3af; font-weight: 600; margin-bottom: 16px; text-transform: uppercase;"><i class="fas fa-images"></i> Media Files</div>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px;">
                    ${buildMediaGallery()}
                </div>
            </div>
        </div>
    `;

    // Show the modal with proper display and z-index ABOVE user info modal
    modal.style.display = 'grid';
    modal.style.zIndex = complaintModalZIndex;
    modal.classList.add('active');
    
    // Add click handler to close when clicking outside modal-card
    modal.onclick = function(e) {
        if (e.target === modal) {
            closeComplaintDetailsFromUser();
        }
    };
    
    console.log('[MODAL] Complaint details modal opened from user info with z-index:', complaintModalZIndex);
}
window.displayComplaintInUserOverlay = displayComplaintInUserOverlay;

// Close modal helper function
function closeUserInfoModal() {
    // Remove dynamic overlay if exists
    const overlay = document.querySelector('.user-info-overlay');
    if (overlay) {
        overlay.remove();
        return;
    }
    // Fallback to old modal
    const modal = document.getElementById('adminProfileModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
}
window.closeUserInfoModal = closeUserInfoModal;

// View complaint from user modal - DON'T close user modal, stack on top
function viewComplaintFromUser(complaintId) {
    console.log('[VIEW] viewComplaintFromUser:', complaintId);
    // Show complaint details as overlay on top of user modal
    viewComplaintDetails(complaintId);
}
window.viewComplaintFromUser = viewComplaintFromUser;


// ============================================


// ============================================
// ADDITIONAL MISSING FUNCTIONS - COMPLETE SET
// ============================================

// HEAD SELECTION MODE FUNCTIONS
function toggleHeadSelectionMode() {
    console.log('[HEAD] toggleHeadSelectionMode');
    const checkboxes = document.querySelectorAll('.head-checkbox-column');
    const deleteBtn = document.getElementById('deleteHeadSelectedBtn');
    const printBtn = document.getElementById('printHeadSelectedBtn');
    const cancelBtn = document.getElementById('cancelHeadSelectionBtn');
    const toggleBtn = document.getElementById('toggleHeadSelectionBtn');
    
    const isHidden = checkboxes[0]?.style.display === 'none';
    
    checkboxes.forEach(cb => cb.style.display = isHidden ? 'table-cell' : 'none');
    
    if (isHidden) {
        deleteBtn.style.display = 'none';
        printBtn.style.display = 'none';
        cancelBtn.style.display = 'inline-block';
        toggleBtn.textContent = 'Selection Mode: ON';
    } else {
        deleteBtn.style.display = 'none';
        printBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
        toggleBtn.textContent = 'Select Items';
        document.querySelectorAll('.head-complaint-checkbox').forEach(cb => cb.checked = false);
    }
}

function cancelHeadSelectionMode() {
    console.log('[HEAD] cancelHeadSelectionMode');
    toggleHeadSelectionMode();
}

function toggleHeadSelectAll() {
    console.log('[HEAD] toggleHeadSelectAll');
    const selectAll = document.getElementById('headSelectAll');
    const checkboxes = document.querySelectorAll('.head-complaint-checkbox');
    checkboxes.forEach(cb => cb.checked = selectAll.checked);
    updateHeadDeleteButton();
}

function updateHeadDeleteButton() {
    const checked = document.querySelectorAll('.head-complaint-checkbox:checked');
    const deleteBtn = document.getElementById('deleteHeadSelectedBtn');
    const printBtn = document.getElementById('printHeadSelectedBtn');
    const count = checked.length;
    
    if (count > 0) {
        deleteBtn.style.display = 'inline-block';
        deleteBtn.innerHTML = `<i class="fas fa-trash"></i> Delete Selected (${count})`;
        printBtn.style.display = 'inline-block';
        printBtn.innerHTML = `<i class="fas fa-print"></i> Print Selected (${count})`;
    } else {
        deleteBtn.style.display = 'none';
        printBtn.style.display = 'none';
    }
}

async function deleteHeadSelectedComplaints() {
    console.log('[HEAD] deleteHeadSelectedComplaints');
    const checked = Array.from(document.querySelectorAll('.head-complaint-checkbox:checked'));
    const ids = checked.map(cb => cb.dataset.id);
    
    if (ids.length === 0) {
        showToast('No complaints selected', 'warning');
        return;
    }
    
    showConfirmModal(
        'Delete Selected Complaints',
        `Are you sure you want to delete ${ids.length} complaint(s)? This action cannot be undone.`,
        async () => {
            try {
                for (const id of ids) {
                    await fetch(`${getAPIBase()}/api/complaints/${id}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                    });
                }
                showToast(`${ids.length} complaint(s) deleted`, 'success');
                loadComplaints();
                loadDashboardStats();
            } catch (error) {
                console.error('[HEAD] Delete error:', error);
                showToast('Failed to delete complaints', 'error');
            }
        },
        'Delete All',
        'Cancel',
        'danger'
    );
}

function printHeadSelectedComplaints() {
    console.log('[HEAD] printHeadSelectedComplaints');
    const checked = document.querySelectorAll('.head-complaint-checkbox:checked');
    if (checked.length === 0) {
        showToast('No complaints selected', 'warning');
        return;
    }
    window.print();
}

// MENU AND MODAL FUNCTIONS
function toggleComplaintMenu(complaintId, event) {
    console.log('[MENU] toggleComplaintMenu:', complaintId);
    event?.stopPropagation();
    
    closeAllMenus();
    const menu = document.getElementById(`menu-${complaintId}`);
    if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    }
}

function closeAllMenus() {
    document.querySelectorAll('.complaint-dropdown-menu').forEach(menu => {
        menu.style.display = 'none';
    });
}

function toggleMedia(complaintId) {
    console.log('[MEDIA] toggleMedia:', complaintId);
    const mediaRow = document.getElementById(`media-${complaintId}`);
    if (mediaRow) {
        mediaRow.style.display = mediaRow.style.display === 'none' ? 'table-row' : 'none';
    }
}

// INLINE STATUS UPDATE
function showInlineStatusUpdater(complaintId) {
    console.log('[STATUS] showInlineStatusUpdater:', complaintId);
    closeAllMenus();
    
    const updater = document.createElement('div');
    updater.id = 'inline-status-updater';
    updater.style.cssText = `
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background: linear-gradient(135deg, #1a0a4a, #2a1a60); border: 2px solid #00FFFF;
        border-radius: 16px; padding: 30px; z-index: 10000; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        min-width: 350px;
    `;
    updater.innerHTML = `
        <h3 style="color: #00FFFF; margin-bottom: 20px;"><i class="fas fa-exchange-alt"></i> Update Status</h3>
        <select id="newStatusSelect" style="width: 100%; padding: 12px; border-radius: 8px; border: 2px solid #00FFFF; background: rgba(0,0,0,0.3); color: white; font-size: 16px; margin-bottom: 20px;">
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
        </select>
        <div style="display: flex; gap: 10px; justify-content: flex-end;">
            <button onclick="document.getElementById('inline-status-updater').remove()" style="padding: 10px 20px; border: none; border-radius: 8px; background: #6b7280; color: white; cursor: pointer;">Cancel</button>
            <button onclick="submitInlineStatus(${complaintId})" style="padding: 10px 20px; border: none; border-radius: 8px; background: linear-gradient(135deg, #10B981, #059669); color: white; cursor: pointer;">Update</button>
        </div>
    `;
    document.body.appendChild(updater);
}

async function submitInlineStatus(complaintId) {
    console.log('[STATUS] submitInlineStatus:', complaintId);
    const select = document.getElementById('newStatusSelect');
    const newStatus = select.value;
    
    const validStatuses = ['pending', 'in_progress', 'resolved'];
    if (!validStatuses.includes(newStatus)) {
        showToast('Invalid status selected', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${getAPIBase()}/api/complaints/${complaintId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (response.ok) {
            showToast('Status updated successfully', 'success');
            document.getElementById('inline-status-updater')?.remove();
            // Reload complaints and stats immediately
            loadComplaints();
            loadDashboardStats();
        } else {
            throw new Error('Update failed');
        }
    } catch (error) {
        console.error('[STATUS] Error:', error);
        showToast('Failed to update status', 'error');
    }
}

// QUICK REPLY AND MESSAGING
function quickReply(complaintId) {
    console.log('[REPLY] quickReply:', complaintId);
    const message = prompt('Enter your message:');
    if (!message || !message.trim()) return;
    
    sendQuickReplyMessage(complaintId, message);
}

async function sendQuickReplyMessage(complaintId, message) {
    console.log('[REPLY] sendQuickReplyMessage:', complaintId);
    try {
        const response = await fetch(`${getAPIBase()}/api/complaints/${complaintId}/reply`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message.trim() })
        });
        
        if (response.ok) {
            showToast('Message sent successfully', 'success');
        } else {
            throw new Error('Send failed');
        }
    } catch (error) {
        console.error('[REPLY] Error:', error);
        showToast('Failed to send message', 'error');
    }
}

// Removed: sendMessage stub - use sendMessageToAdmin instead
// Add sendMessage as alias for sendMessageToAdmin for backward compatibility
async function sendMessage(userId, message) {
    console.log('[MESSAGE] sendMessage (alias):', userId);
    return sendMessageToAdmin(userId, message);
}

// sendHeadMessage - sends a message from head dashboard
async function sendHeadMessage() {
    console.log('[MESSAGE] sendHeadMessage');
    const receiverSelect = document.getElementById('headMessageReceiver');
    const subjectInput = document.getElementById('headMessageSubject');
    const bodyInput = document.getElementById('headMessageBody');
    
    if (!receiverSelect || !subjectInput || !bodyInput) {
        showToast('Message form not found', 'error');
        return;
    }
    
    const receiverId = receiverSelect.value;
    const subject = subjectInput.value.trim();
    const body = bodyInput.value.trim();
    
    if (!receiverId || !subject || !body) {
        showToast('Please fill in all fields', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${getAPIBase()}/api/messages/send`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                receiver_id: parseInt(receiverId),
                subject: subject,
                body: body
            })
        });
        
        if (response.ok) {
            showToast('Message sent successfully', 'success');
            closeHeadMessageModal();
            // Clear form
            receiverSelect.value = '';
            subjectInput.value = '';
            bodyInput.value = '';
        } else {
            const error = await response.json();
            showToast(error.error || 'Failed to send message', 'error');
        }
    } catch (error) {
        console.error('[MESSAGE] Error:', error);
        showToast('Failed to send message', 'error');
    }
}

function closeHeadMessageModal() {
    console.log('[MODAL] closeHeadMessageModal');
    const modal = document.getElementById('headMessageModal');
    if (modal) modal.style.display = 'none';
}

// FEEDBACK FUNCTIONS
async function deleteFeedback(feedbackId) {
    console.log('[FEEDBACK] deleteFeedback:', feedbackId);
    
    showConfirmModal(
        'Delete Feedback',
        'Are you sure you want to delete this feedback?',
        async () => {
            try {
                const response = await fetch(`${getAPIBase()}/api/feedback/${feedbackId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                
                if (response.ok) {
                    showToast('Feedback deleted', 'success');
                    loadAllFeedback();
                    loadDashboardStats();
                } else {
                    throw new Error('Delete failed');
                }
            } catch (error) {
                console.error('[FEEDBACK] Error:', error);
                showToast('Failed to delete feedback', 'error');
            }
        },
        'Delete',
        'Cancel',
        'danger'
    );
}

// Removed: openEditFeedbackModal stub - feedback is not editable
function openEditFeedbackModal() {
    showToast('Feedback cannot be edited', 'info');
}

// Removed: openAddFeedbackModal stub - only users can submit feedback
function openAddFeedbackModal() {
    showToast('Only users can submit feedback', 'info');
}

function closeFeedbackModal() {
    console.log('[MODAL] closeFeedbackModal');
    const modal = document.getElementById('feedbackModal');
    if (modal) modal.style.display = 'none';
}

function deleteComplaintFeedback(complaintId) {
    console.log('[FEEDBACK] deleteComplaintFeedback:', complaintId);
    deleteFeedback(complaintId);
}

// VIEW AND DETAIL FUNCTIONS
function viewComplaint(complaintId) {
    console.log('[VIEW] viewComplaint:', complaintId);
    viewComplaintDetails(complaintId);
}

function viewComplaintDetail(complaintId) {
    console.log('[VIEW] viewComplaintDetail:', complaintId);
    viewComplaintDetails(complaintId);
}

// MESSAGE FUNCTIONS - Now with proper API calls
async function replyToMessage(messageId) {
    console.log('[MESSAGE] replyToMessage:', messageId);
    const reply = prompt('Enter your reply:');
    if (!reply || !reply.trim()) return;
    
    // In a real implementation, this would send to the original sender
    // For now we show it's not fully implemented
    showToast('Message reply feature requires sender context', 'warning');
}

async function deleteMessage(messageId) {
    console.log('[MESSAGE] deleteMessage:', messageId);
    
    showConfirmModal(
        'Delete Message',
        'Are you sure you want to delete this message?',
        async () => {
            try {
                const response = await fetch(`${getAPIBase()}/api/messages/${messageId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                
                if (response.ok) {
                    showToast('Message deleted', 'success');
                    loadMessages();
                } else {
                    throw new Error('Delete failed');
                }
            } catch (error) {
                console.error('[MESSAGE] Error:', error);
                showToast('Failed to delete message', 'error');
            }
        },
        'Delete',
        'Cancel',
        'danger'
    );
}

// deleteMessage original continuation removed
function deleteMessageOriginal(messageId) {
    return;
    try {
        const response = { ok: true };
        if (response.ok) {
            showToast('Message deleted', 'success');
        } else {
            throw new Error('Delete failed');
        }
    } catch (error) {
        console.error('[MESSAGE] Error:', error);
        showToast('Failed to delete message', 'error');
    }
}

async function markAsRead(messageId) {
    console.log('[MESSAGE] markAsRead:', messageId);
    try {
        const response = await fetch(`${getAPIBase()}/api/messages/${messageId}/read`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (response.ok) {
            showToast('Message marked as read', 'success');
        } else {
            throw new Error('Mark as read failed');
        }
    } catch (error) {
        console.error('[MESSAGE] Error:', error);
        showToast('Failed to mark message as read', 'error');
    }
}

// MODAL FUNCTIONS
function closeComplaintModal() {
    console.log('[MODAL] closeComplaintModal');
    const modal = document.getElementById('complaintModal');
    if (modal) modal.style.display = 'none';
}

// Removed: switchTab and showPage stubs - dashboard uses section-based navigation

// Toggle row checkbox when clicking on row
function toggleRowCheckbox(rowElement) {
    const checkbox = rowElement.querySelector('input[type="checkbox"]');
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        // Trigger any associated change handlers
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

// switchTab - compatibility function for tab-based navigation
function switchTab(tabName) {
    console.log('[NAV] switchTab called with:', tabName);
    // Map tab names to section IDs
    const tabSectionMap = {
        'dashboard': 'dashboard',
        'complaints': 'complaint-management',
        'users': 'user-management', 
        'admins': 'admin-management',
        'messages': 'messages',
        'feedback': 'feedback',
        'settings': 'settings'
    };
    
    const sectionId = tabSectionMap[tabName] || tabName;
    if (typeof showSection === 'function') {
        showSection(sectionId);
    }
}

// showPage - compatibility function for pagination/navigation
function showPage(pageNum) {
    console.log('[NAV] showPage called with:', pageNum);
    // This is typically used for complaint detail pages
    // Redirect to appropriate section or modal
}


// ============================================
// EXPORT ALL FUNCTIONS (UPDATED COMPLETE LIST)
// ============================================
window.printAdmins = printAdmins;
window.loadAllFeedback = loadAllFeedback;
window.showConfirmModal = showConfirmModal;
window.printUsers = printUsers;
window.printAllComplaints = printAllComplaints;
window.printFeedback = printFeedback;
window.deleteUser = deleteUser;
window.deleteAdmin = deleteAdmin;
window.toggleAdminStatus = toggleAdminStatus;

// Global variable to store complaint ID for deletion
let pendingDeleteComplaintId = null;

// Export deleteComplaint to window BEFORE it's defined
window.deleteComplaint = null;

async function deleteComplaint(complaintId) {
    console.log('[DELETE] deleteComplaint called with ID:', complaintId, 'type:', typeof complaintId);
    
    // Validate complaint ID
    if (!complaintId || complaintId === 'null' || complaintId === 'undefined' || isNaN(complaintId)) {
        console.error('[DELETE] Invalid complaint ID:', complaintId);
        showToast('Invalid complaint ID', 'error');
        return;
    }
    
    // Create confirmation modal overlay
    showDeleteConfirmationModal(complaintId);
}

function showDeleteConfirmationModal(complaintId) {
    console.log('[DELETE MODAL] Creating confirmation modal for complaint ID:', complaintId);
    
    // Remove any existing delete modals
    document.querySelectorAll('.delete-confirm-overlay').forEach(el => el.remove());
    
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'delete-confirm-overlay modal-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.85);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        animation: fadeIn 0.2s ease;
    `;
    
    // Create modal card
    const modalCard = document.createElement('div');
    modalCard.style.cssText = `
        background: linear-gradient(145deg, #1a1a2e 0%, #0f0f1a 100%);
        border: 2px solid rgba(239, 68, 68, 0.5);
        border-radius: 20px;
        width: min(480px, 92%);
        box-shadow: 0 25px 80px rgba(239, 68, 68, 0.3), 0 0 40px rgba(0, 0, 0, 0.5);
        animation: slideUp 0.3s ease;
    `;
    
    modalCard.innerHTML = `
        <div style="padding: 24px 28px; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 0; color: #ef4444; font-size: 20px; font-weight: 700; display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-exclamation-triangle"></i> Delete Complaint
            </h3>
        </div>
        <div style="padding: 32px 28px; text-align: center;">
            <div style="font-size: 64px; color: #ef4444; margin-bottom: 20px;">
                <i class="fas fa-trash-alt"></i>
            </div>
            <p style="color: #C0C0C0; font-size: 16px; margin-bottom: 12px; line-height: 1.6;">
                Are you sure you want to delete this complaint?
            </p>
            <p style="color: #FFD100; font-size: 20px; font-weight: 700; margin-bottom: 16px;">
                Complaint #${complaintId}
            </p>
            <p style="color: #ef4444; font-size: 14px; font-weight: 600; background: rgba(239, 68, 68, 0.1); padding: 12px; border-radius: 8px; border: 1px solid rgba(239, 68, 68, 0.3);">
                <i class="fas fa-exclamation-circle"></i> This action cannot be undone!
            </p>
        </div>
        <div style="padding: 20px 28px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; gap: 12px; justify-content: flex-end;">
            <button class="cancel-delete-btn" style="background: linear-gradient(135deg, #6b7280, #4b5563); color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-size: 15px; font-weight: 600; transition: all 0.3s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform=''">
                <i class="fas fa-times"></i> Cancel
            </button>
            <button class="confirm-delete-btn" style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-size: 15px; font-weight: 600; transition: all 0.3s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(239,68,68,0.5)'" onmouseout="this.style.transform=''; this.style.boxShadow=''">
                <i class="fas fa-trash-alt"></i> Delete
            </button>
        </div>
    `;
    
    overlay.appendChild(modalCard);
    document.body.appendChild(overlay);
    
    // Add event listeners
    const cancelBtn = modalCard.querySelector('.cancel-delete-btn');
    const confirmBtn = modalCard.querySelector('.confirm-delete-btn');
    
    const closeModal = () => {
        overlay.remove();
    };
    
    cancelBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });
    
    confirmBtn.addEventListener('click', async () => {
        console.log('[DELETE MODAL] Confirm clicked for complaint ID:', complaintId);
        closeModal();
        await performDelete(complaintId);
    });
    
    console.log('[DELETE MODAL] Modal created and displayed');
}

async function performDelete(complaintId) {
    console.log('[DELETE] performDelete called with ID:', complaintId, 'type:', typeof complaintId);
    
    // Validate complaint ID
    if (!complaintId || complaintId === 'null' || complaintId === 'undefined' || isNaN(complaintId)) {
        console.error('[DELETE] Invalid complaint ID for deletion:', complaintId);
        showToast('Invalid complaint ID', 'error');
        return;
    }
    
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            showToast('Please login first', 'error');
            return;
        }
        
        const apiBase = getAPIBase();
        console.log('[DELETE] Deleting complaint:', complaintId, 'API:', apiBase);
        
        const response = await fetch(`${apiBase}/api/head/complaints/${complaintId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        console.log('[DELETE] Response status:', response.status);
        
        if (response.status === 401) {
            handle401Error(response, 'deleteComplaint');
            return;
        }
        
        if (response.ok) {
            const result = await response.json();
            showToast(result.message || 'Complaint deleted successfully', 'success');
            loadComplaints();
            if (typeof loadDashboardStats === 'function') loadDashboardStats();
        } else {
            const error = await response.json().catch(() => ({}));
            showToast(`Failed to delete: ${error.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Delete complaint error:', error);
        showToast('Network error while deleting complaint', 'error');
    }
}

// Export delete functions
window.deleteComplaint = deleteComplaint;
window.showDeleteConfirmationModal = showDeleteConfirmationModal;
window.performDelete = performDelete;

// Legacy function for compatibility (now simplified)
function confirmDelete() {
    console.warn('[DELETE] confirmDelete called - this is legacy, modal system should handle deletion');
}
window.confirmDelete = confirmDelete;

// Legacy function for compatibility
function closeDeleteModal() {
    console.log('[DELETE] closeDeleteModal called - removing any delete modals');
    // Remove dynamic delete modals
    document.querySelectorAll('.delete-confirm-overlay').forEach(el => el.remove());
    // Also close old static modal if it exists
    const oldModal = document.getElementById('deleteConfirmModal');
    if (oldModal) {
        oldModal.style.display = 'none';
        oldModal.classList.remove('active');
    }
}
window.closeDeleteModal = closeDeleteModal;

// Media Viewer Functions
function openMediaViewer(fileUrl, mimeType, fileName) {
    const modal = document.getElementById('mediaViewerModal');
    const body = document.getElementById('mediaViewerBody');
    const title = document.getElementById('mediaViewerTitle');
    const info = document.getElementById('mediaViewerInfo');
    
    if (!modal || !body) {
        console.error('Media viewer modal not found');
        return;
    }
    
    // Set title
    if (title) {
        title.textContent = fileName || 'Media Viewer';
    }
    
    // Set info
    if (info) {
        const fileType = mimeType ? mimeType.split('/')[0].toUpperCase() : 'FILE';
        info.innerHTML = `<i class=\"fas fa-file\"></i> ${fileType} - ${fileName || 'Attachment'}`;
    }
    
    // Determine media type and create appropriate viewer
    const isImage = mimeType && mimeType.startsWith('image/');
    const isPDF = mimeType && mimeType.includes('pdf');
    const isVideo = mimeType && mimeType.startsWith('video/');
    
    let content = '';
    
    if (isImage) {
        content = `
            <div style=\"padding: 20px; background: rgba(0,0,0,0.8);\">
                <img src=\"${fileUrl}\" alt=\"${fileName}\" 
                     style=\"max-width: 100%; max-height: 65vh; object-fit: contain; border-radius: 8px;\"
                     onerror=\"this.parentElement.innerHTML='<div style=padding:40px;color:#dc3545;><i class=fas fa-exclamation-triangle style=font-size:48px;></i><p style=margin-top:16px;>Failed to load image</p></div>'\">
            </div>
        `;
    } else if (isVideo) {
        content = `
            <div style=\"padding: 20px; background: rgba(0,0,0,0.8);\">
                <video controls style=\"max-width: 100%; max-height: 65vh; border-radius: 8px;\">
                    <source src=\"${fileUrl}\" type=\"${mimeType}\">
                    Your browser does not support the video tag.
                </video>
            </div>
        `;
    } else if (isPDF) {
        content = `
            <div style=\"padding: 0; background: rgba(0,0,0,0.8); height: 65vh;\">
                <iframe src=\"${fileUrl}\" 
                        style=\"width: 100%; height: 100%; border: none; border-radius: 8px;\"
                        onerror=\"this.parentElement.innerHTML='<div style=padding:40px;color:#dc3545;><i class=fas fa-exclamation-triangle style=font-size:48px;></i><p style=margin-top:16px;>Failed to load PDF</p></div>'\">
                </iframe>
            </div>
        `;
    } else {
        // Generic file - provide download option
        content = `
            <div style=\"padding: 60px; text-align: center;\">
                <i class=\"fas fa-file-alt\" style=\"font-size: 80px; color: #FFD700; margin-bottom: 24px;\"></i>
                <p style=\"font-size: 16px; color: var(--text-100); margin-bottom: 8px;\">${fileName || 'Attachment'}</p>
                <p style=\"font-size: 13px; color: var(--text-300); margin-bottom: 24px;\">This file type cannot be previewed</p>
                <a href=\"${fileUrl}\" download=\"${fileName}\" class=\"btn btn-primary\" style=\"display: inline-flex; align-items: center; gap: 8px;\">
                    <i class=\"fas fa-download\"></i> Download File
                </a>
            </div>
        `;
    }
    
    body.innerHTML = content;
    modal.style.display = 'flex';
    modal.classList.add('active');
}

function closeMediaViewer() {
    const modal = document.getElementById('mediaViewerModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}

window.deleteComplaint = deleteComplaint;
window.confirmDelete = confirmDelete;
window.closeDeleteModal = closeDeleteModal;
window.openMediaViewer = openMediaViewer;
window.closeMediaViewer = closeMediaViewer;

// Update complaint status (HEAD)
async function updateComplaintStatus(complaintId, newStatus) {
    if (!newStatus) return;
    
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            showToast('Please login first', 'error');
            return;
        }

        const apiBase = getAPIBase();
        const response = await fetch(`${apiBase}/api/complaints/${complaintId}/status`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (!response.ok) {
            throw new Error('Failed to update status');
        }

        showToast('Status updated successfully', 'success');
        
        // Close modal and refresh
        document.querySelectorAll('.modal-overlay').forEach(overlay => overlay.remove());
        if (typeof loadComplaints === 'function') {
            loadComplaints();
        }
        if (typeof loadDashboardStats === 'function') {
            loadDashboardStats();
        }
    } catch (error) {
        console.error('Error updating status:', error);
        showToast('Failed to update status', 'error');
    }
}
window.updateComplaintStatus = updateComplaintStatus;

// Open assign complaint modal
async function openAssignComplaintModal(complaintId, currentAdminName, currentAdminId) {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            showToast('Please login first', 'error');
            return;
        }

        // Fetch all admins
        const apiBase = getAPIBase();
        const response = await fetch(`${apiBase}/api/head/admins`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to fetch admins');
        }

        const admins = await response.json();
        
        // Create modal
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(7, 4, 16, 0.92);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10020;
            animation: fadeIn 0.25s ease;
        `;
        
        const modalCard = document.createElement('div');
        modalCard.style.cssText = `
            background: linear-gradient(145deg, #1a1a2e 0%, #0f0f1a 100%);
            border: 2px solid rgba(0, 200, 255, 0.3);
            border-radius: 20px;
            width: min(500px, 90%);
            box-shadow: 0 25px 80px rgba(0, 200, 255, 0.2);
        `;
        
        modalCard.innerHTML = `
            <div style="padding: 24px 28px; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; color: #00C8FF; font-size: 18px; font-weight: 700;">
                    <i class="fas fa-user-plus"></i> ${currentAdminId ? 'Reassign' : 'Assign'} Complaint #${complaintId}
                </h3>
                <button onclick="this.closest('.modal-overlay').remove()" style="background: rgba(255,255,255,0.1); border: none; color: #fff; width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 14px;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div style="padding: 28px;">
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 13px; color: #9ca3af; margin-bottom: 8px;">Current Admin:</div>
                    <div style="font-size: 15px; color: ${currentAdminId ? '#10B981' : '#EF4444'}; font-weight: 600;">${currentAdminName}</div>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; font-size: 13px; color: #9ca3af; margin-bottom: 8px; font-weight: 600;">Select Admin:</label>
                    <select id="assignAdminSelect" style="width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(0,200,255,0.3); color: #fff; padding: 12px; border-radius: 10px; font-size: 14px;">
                        <option value="" disabled selected>Choose an admin...</option>
                        ${admins.map(admin => `
                            <option value="${admin.id}" ${admin.id === currentAdminId ? 'selected' : ''}>
                                ${admin.name} (${admin.email}) ${admin.district_names ? `- ${admin.district_names}` : ''}
                            </option>
                        `).join('')}
                    </select>
                </div>
            </div>
            <div style="padding: 20px 28px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; gap: 12px; justify-content: flex-end;">
                ${currentAdminId ? `
                    <button onclick="unassignComplaint(${complaintId})" style="background: linear-gradient(135deg, #EF4444, #DC2626); color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 600;">
                        <i class="fas fa-user-minus"></i> Unassign
                    </button>
                ` : ''}
                <button onclick="this.closest('.modal-overlay').remove()" style="background: linear-gradient(135deg, #6b7280, #4b5563); color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 600;">
                    <i class="fas fa-times"></i> Cancel
                </button>
                <button onclick="assignComplaintToAdmin(${complaintId})" style="background: linear-gradient(135deg, #10B981, #059669); color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 600;">
                    <i class="fas fa-check"></i> Assign
                </button>
            </div>
        `;
        
        overlay.appendChild(modalCard);
        document.body.appendChild(overlay);
        
    } catch (error) {
        console.error('Error opening assign modal:', error);
        showToast('Failed to load admins', 'error');
    }
}
window.openAssignComplaintModal = openAssignComplaintModal;

// Assign complaint to selected admin
async function assignComplaintToAdmin(complaintId) {
    const select = document.getElementById('assignAdminSelect');
    const adminId = select?.value;
    
    if (!adminId) {
        showToast('Please select an admin', 'error');
        return;
    }
    
    try {
        const token = localStorage.getItem('token');
        const apiBase = getAPIBase();
        
        const response = await fetch(`${apiBase}/api/head/complaints/${complaintId}/assign`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ admin_id: parseInt(adminId) })
        });

        if (!response.ok) {
            throw new Error('Failed to assign complaint');
        }

        const data = await response.json();
        showToast(`Complaint assigned to ${data.admin_name}`, 'success');
        
        // Close modal and refresh
        document.querySelectorAll('.modal-overlay').forEach(overlay => overlay.remove());
        if (typeof loadComplaints === 'function') {
            loadComplaints();
        }
        if (typeof loadDashboardStats === 'function') {
            loadDashboardStats();
        }
    } catch (error) {
        console.error('Error assigning complaint:', error);
        showToast('Failed to assign complaint', 'error');
    }
}
window.assignComplaintToAdmin = assignComplaintToAdmin;

// Unassign complaint from admin
async function unassignComplaint(complaintId) {
    showConfirmModal(
        'Unassign Complaint',
        `Are you sure you want to unassign complaint #${complaintId}?`,
        async () => {
            try {
                const token = localStorage.getItem('token');
                const apiBase = getAPIBase();
                
                const response = await fetch(`${apiBase}/api/head/complaints/${complaintId}/unassign`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error('Failed to unassign complaint');
                }

                showToast('Complaint unassigned successfully', 'success');
                
                // Close modal and refresh
                document.querySelectorAll('.modal-overlay').forEach(overlay => overlay.remove());
                if (typeof loadComplaints === 'function') {
                    loadComplaints();
                }
                if (typeof loadDashboardStats === 'function') {
                    loadDashboardStats();
                }
            } catch (error) {
                console.error('Error unassigning complaint:', error);
                showToast('Failed to unassign complaint', 'error');
            }
        }
    );
}
window.unassignComplaint = unassignComplaint;

window.loadComplaints = loadComplaints;
window.loadDashboardStats = loadDashboardStats;
window.loadAdminList = loadAdminList;
window.loadAllUsers = loadAllUsers;
window.toggleHeadSelectionMode = toggleHeadSelectionMode;
window.cancelHeadSelectionMode = cancelHeadSelectionMode;
window.toggleHeadSelectAll = toggleHeadSelectAll;
window.updateHeadDeleteButton = updateHeadDeleteButton;
window.deleteHeadSelectedComplaints = deleteHeadSelectedComplaints;
window.printHeadSelectedComplaints = printHeadSelectedComplaints;
window.toggleComplaintMenu = toggleComplaintMenu;
window.closeAllMenus = closeAllMenus;
window.toggleMedia = toggleMedia;
window.showInlineStatusUpdater = showInlineStatusUpdater;
window.submitInlineStatus = submitInlineStatus;
window.quickReply = quickReply;
window.sendQuickReplyMessage = sendQuickReplyMessage;
window.sendMessage = sendMessage;
window.sendHeadMessage = sendHeadMessage;
window.closeHeadMessageModal = closeHeadMessageModal;
window.deleteFeedback = deleteFeedback;
window.openEditFeedbackModal = openEditFeedbackModal;
window.openAddFeedbackModal = openAddFeedbackModal;
window.closeFeedbackModal = closeFeedbackModal;
window.deleteComplaintFeedback = deleteComplaintFeedback;
window.viewComplaint = viewComplaint;
window.viewComplaintDetail = viewComplaintDetail;
window.replyToMessage = replyToMessage;
window.deleteMessage = deleteMessage;
window.markAsRead = markAsRead;
window.closeComplaintModal = closeComplaintModal;
window.switchTab = switchTab;
window.showPage = showPage;
window.toggleRowCheckbox = toggleRowCheckbox;

console.log(' ALL FUNCTIONS EXPORTED - Total:', Object.keys(window).filter(k => typeof window[k] === 'function').length);


// Delete complaint

// Delete user
async function deleteUser(userId) {
    showConfirmModal(
        'Delete User',
        'Are you sure you want to delete this user? All their complaints will remain.',
        async () => {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch(`${getAPIBase()}/api/head/users/${userId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.status === 401) {
                    handle401Error(response, 'deleteUser');
                    return;
                }
                
                if (response.ok) {
                    showToast('✅ User deleted successfully', 'success');
                    closeUserInfoModal();
                    if (typeof loadAllUsers === 'function') {
                        loadAllUsers();
                    }
                    if (typeof loadDashboardStats === 'function') {
                        loadDashboardStats();
                    }
                } else {
                    const error = await response.json();
                    showToast(`Failed to delete user: ${error.error || 'Unknown error'}`, 'error');
                }
            } catch (error) {
                console.error('Delete user error:', error);
                showToast('Network error while deleting user', 'error');
            }
        },
        'Delete',
        'Cancel',
        'danger'
    );
}

// ==================== FEEDBACK MANAGEMENT ====================

async function loadFeedback() {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${getAPIBase()}/api/head/feedback`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.status === 401) {
            handle401Error(response, 'loadFeedback');
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to fetch feedback');
        }

        const data = await response.json();
        displayFeedback(data.feedback || []);
    } catch (error) {
        console.error('Error loading feedback:', error);
        showToast('Failed to load feedback', 'error');
    }
}

function displayFeedback(feedbackList) {
    const wrapper = document.getElementById('feedbackTableWrapper');
    if (!wrapper) return;

    if (feedbackList.length === 0) {
        wrapper.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; color: #888;">
                <i class="fas fa-comment-dots" style="font-size: 48px; margin-bottom: 20px; opacity: 0.3;"></i>
                <p style="font-size: 18px; margin: 0;">No feedback received yet</p>
            </div>
        `;
        return;
    }

    const getStars = (rating) => {
        let stars = '';
        for (let i = 1; i <= 5; i++) {
            stars += `<i class="fas fa-star" style="color: ${i <= rating ? '#FFD100' : '#444'};"></i> `;
        }
        return stars;
    };

    const getStatusBadge = (status) => {
        const badges = {
            sent: { color: '#FFD100', text: 'New', icon: 'fa-envelope' },
            reviewed: { color: '#00C8FF', text: 'Reviewed', icon: 'fa-check-circle' },
            archived: { color: '#888', text: 'Archived', icon: 'fa-archive' }
        };
        const badge = badges[status] || badges.sent;
        return `
            <span style="
                background: ${badge.color}22;
                color: ${badge.color};
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            ">
                <i class="fas ${badge.icon}"></i>
                ${badge.text}
            </span>
        `;
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const table = `
        <table>
            <thead>
                <tr>
                        <th style="width: 5%;">#</th>
                            <th style="width: 15%;">User</th>
                            <th style="width: 18%;">Email</th>
                            <th style="width: 10%;">Rating</th>
                            <th style="width: 22%;">Message</th>
                            <th style="width: 8%;">Status</th>
                            <th style="width: 12%;">Date</th>
                            <th style="width: 10%; text-align: center;">Delete</th>
                </tr>
            </thead>
            <tbody>
                ${feedbackList.map((f, index) => `
                    <tr>
                        <td>${index + 1}</td>
                        <td style="font-weight: 600; color: #FFD100;">${f.user_name || 'Anonymous'}</td>
                        <td style="color: #00C8FF;">${f.user_email || 'N/A'}</td>
                        <td>${getStars(f.rating)}</td>
                        <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer;" onclick="viewFeedbackDetails(${f.id})">
                            ${f.message || ''}
                        </td>
                        <td>${getStatusBadge(f.status)}</td>
                        <td style="font-size: 13px; color: #888;">${formatDate(f.created_at)}</td>
                        <td style="text-align: center;">
                            <button onclick="deleteFeedback(${f.id})"
                                title="Delete feedback"
                                style="background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
                                       color: white;
                                       border: none;
                                       width: 28px;
                                       height: 28px;
                                       border-radius: 50%;
                                       cursor: pointer;
                                       font-size: 14px;
                                       display: inline-flex;
                                       align-items: center;
                                       justify-content: center;
                                       transition: all 0.2s ease;
                                       box-shadow: 0 2px 6px rgba(220, 38, 38, 0.25);">
                                <i class="fas fa-trash" style="font-size:12px;"></i>
                            </button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    wrapper.innerHTML = table;
}

async function viewFeedbackDetails(feedbackId) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${getAPIBase()}/api/head/feedback`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            handle401Error(response, 'viewFeedbackDetails');
            return;
        }

        let data = await response.json();
        const list = Array.isArray(data) ? data : (data.feedback || []);
        const fid = Number(feedbackId);
        const feedback = list.find(f => Number(f.id) === fid);

        if (!feedback) {
            showToast('Feedback not found', 'error');
            return;
        }

        const getStars = (rating) => {
            let stars = '';
            for (let i = 1; i <= 5; i++) {
                stars += `<i class="fas fa-star" style="color: ${i <= rating ? '#FFD100' : '#444'}; font-size: 20px;"></i> `;
            }
            return stars;
        };

        const modal = document.getElementById('feedbackModal');
        const body = document.getElementById('feedbackBody');
        
        if (!modal || !body) return;

        body.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 20px;">
                <div style="background: rgba(255,209,0,0.1); padding: 20px; border-radius: 12px; border-left: 4px solid #FFD100;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                        <div>
                            <h4 style="margin: 0 0 8px 0; color: #FFD100; font-size: 18px;">${feedback.user_name || 'Anonymous'}</h4>
                            <p style="margin: 0; color: #00C8FF; font-size: 14px;">${feedback.user_email || 'N/A'}</p>
                        </div>
                        <div style="text-align: right;">
                            ${getStars(feedback.rating)}
                            <p style="margin: 8px 0 0 0; font-size: 13px; color: #888;">
                                ${new Date(feedback.created_at).toLocaleString()}
                            </p>
                        </div>
                    </div>
                </div>

                <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px;">
                    <h4 style="margin: 0 0 12px 0; color: #C0C0C0; font-size: 16px;">
                        <i class="fas fa-comment-dots"></i> Feedback Message
                    </h4>
                    <p style="margin: 0; line-height: 1.6; color: #fff; white-space: pre-wrap;">${feedback.message || ''}</p>
                </div>

                <div style="display: flex; gap: 12px; padding-top: 10px;">
                    <button class="btn btn-primary" onclick="markFeedbackAsReviewed(${feedback.id})" style="flex: 1;">
                        <i class="fas fa-check-circle"></i> Mark as Reviewed
                    </button>
                    <button class="btn btn-secondary" onclick="archiveFeedback(${feedback.id})" style="flex: 1;">
                        <i class="fas fa-archive"></i> Archive
                    </button>
                </div>
            </div>
        `;

        modal.classList.add('active');
    } catch (error) {
        console.error('Error viewing feedback details:', error);
        showToast('Failed to load feedback details', 'error');
    }
}

async function markFeedbackAsReviewed(feedbackId) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${getAPIBase()}/api/head/feedback/${feedbackId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: 'reviewed' })
        });

        if (response.status === 401) {
            handle401Error(response, 'markFeedbackAsReviewed');
            return;
        }

        if (response.ok) {
            showToast('✅ Feedback marked as reviewed', 'success');
            document.getElementById('feedbackModal').classList.remove('active');
            setTimeout(() => loadFeedback(), 500);
        } else {
            const error = await response.json();
            showToast(`Failed to update: ${error.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Error updating feedback:', error);
        showToast('Network error while updating feedback', 'error');
    }
}

async function archiveFeedback(feedbackId) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${getAPIBase()}/api/head/feedback/${feedbackId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: 'archived' })
        });

        if (response.status === 401) {
            handle401Error(response, 'archiveFeedback');
            return;
        }

        if (response.ok) {
            showToast('✅ Feedback archived', 'success');
            document.getElementById('feedbackModal').classList.remove('active');
            setTimeout(() => loadFeedback(), 500);
        } else {
            const error = await response.json();
            showToast(`Failed to archive: ${error.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Error archiving feedback:', error);
        showToast('Network error while archiving feedback', 'error');
    }
}

// Add event listeners for feedback section
document.addEventListener('DOMContentLoaded', function() {
    const refreshFeedbackBtn = document.getElementById('refreshFeedbackBtn');
    if (refreshFeedbackBtn) {
        refreshFeedbackBtn.addEventListener('click', loadFeedback);
    }

    const feedbackSearch = document.getElementById('feedbackSearch');
    if (feedbackSearch) {
        feedbackSearch.addEventListener('input', filterFeedback);
    }

    const feedbackStatusFilter = document.getElementById('feedbackStatusFilter');
    if (feedbackStatusFilter) {
        feedbackStatusFilter.addEventListener('change', filterFeedback);
    }

    const feedbackRatingFilter = document.getElementById('feedbackRatingFilter');
    if (feedbackRatingFilter) {
        feedbackRatingFilter.addEventListener('change', filterFeedback);
    }
});

function filterFeedback() {
    // Client-side filtering implementation (optional)
    loadFeedback();
}

// ==================== USER DETAILS & COMPLAINT HISTORY ====================

async function viewUserDetails(userId, userName) {
    if (userId === undefined || userId === null || userId === '' || Number.isNaN(Number(userId))) {
        showToast('User information not available', 'error');
        return;
    }

    try {
        const token = localStorage.getItem('token');
        
        // Fetch user info and complaints
        const [userResponse, complaintsResponse] = await Promise.all([
            fetch(`${getAPIBase()}/api/head/users`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            }),
            fetch(`${getAPIBase()}/api/head/complaints`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            })
        ]);

        if (userResponse.status === 401 || complaintsResponse.status === 401) {
            handle401Error(userResponse, 'viewUserDetails');
            return;
        }

        if (!userResponse.ok || !complaintsResponse.ok) {
            throw new Error('Failed to fetch user data');
        }

        let userData = await userResponse.json();
        let complaintsData = await complaintsResponse.json();

        // Normalize payloads
        const usersArr = Array.isArray(userData) ? userData : (userData.users || []);
        const complaintsArr = Array.isArray(complaintsData) ? complaintsData : (complaintsData.complaints || []);

        // Find the specific user (numeric compare tolerant)
        const uid = Number(userId);
        const user = usersArr.find(u => Number(u.id) === uid);
        if (!user) {
            showToast('User not found', 'error');
            return;
        }

        // Filter complaints for this user
        const userComplaints = complaintsArr.filter(c => Number(c.user_id) === uid);

        // Display user details modal
        displayUserDetailsModal(user, userComplaints);
    } catch (error) {
        console.error('Error loading user details:', error);
        showToast('Failed to load user details', 'error');
    }
}

function displayUserDetailsModal(user, complaints) {
    const modal = document.getElementById('userDetailsModal');
    const body = document.getElementById('userDetailsBody');
    
    if (!modal || !body) return;

    // Defensive defaults
    user = user || { name: 'N/A', email: 'N/A', id: 'N/A' };
    complaints = Array.isArray(complaints) ? complaints : [];

    const totalComplaints = complaints.length;
    
    // Status counts
    const statusCounts = {
        pending: complaints.filter(c => c.status === 'pending').length,
        'in-progress': complaints.filter(c => c.status === 'in-progress').length,
        resolved: complaints.filter(c => c.status === 'resolved').length,
        rejected: complaints.filter(c => c.status === 'rejected').length
    };

    const getStatusBadge = (status) => {
        const badges = {
            pending: { color: '#FFD100', text: 'Pending', icon: 'fa-clock' },
            'in-progress': { color: '#00C8FF', text: 'In Progress', icon: 'fa-spinner' },
            resolved: { color: '#10B981', text: 'Resolved', icon: 'fa-check-circle' },
            rejected: { color: '#EF4444', text: 'Rejected', icon: 'fa-times-circle' }
        };
        const badge = badges[status] || badges.pending;
        return `
            <span style="
                background: ${badge.color}22;
                color: ${badge.color};
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 4px;
            ">
                <i class="fas ${badge.icon}"></i>
                ${badge.text}
            </span>
        `;
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    body.innerHTML = `
        <div style="padding: 30px;">
            <!-- User Information Box with Gradient -->
            <div style="
                background: linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%);
                border: 2px solid rgba(139, 92, 246, 0.4);
                border-radius: 16px;
                padding: 24px;
                margin-bottom: 0;
            ">
                <div style="
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                ">
                    <div>
                        <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">
                            <i class="fas fa-user"></i> User Name
                        </div>
                        <div style="font-size: 16px; color: #FFD100; font-weight: 600;">
                            ${user.name || 'N/A'}
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">
                            <i class="fas fa-id-card"></i> User ID
                        </div>
                        <div style="font-size: 16px; color: #00C8FF; font-weight: 600;">
                            #${user.id}
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">
                            <i class="fas fa-envelope"></i> Email
                        </div>
                        <div style="font-size: 14px; color: #fff; font-weight: 500;">
                            ${user.email || 'N/A'}
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">
                            <i class="fas fa-exclamation-circle"></i> Total Complaints
                        </div>
                        <div style="font-size: 16px; color: #8b5cf6; font-weight: 700;">
                            ${totalComplaints}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Complaints History Table (Seamless Integration) -->
            <div style="
                background: rgba(0, 0, 0, 0.2);
                border: 2px solid rgba(139, 92, 246, 0.3);
                border-top: none;
                border-radius: 0 0 16px 16px;
                padding: 24px;
            ">
                <h4 style="
                    margin: 0 0 20px 0;
                    color: #C0C0C0;
                    font-size: 18px;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                ">
                    <i class="fas fa-history"></i>
                    Complaint History
                    <span style="
                        background: rgba(139, 92, 246, 0.3);
                        color: #8b5cf6;
                        padding: 4px 12px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: 700;
                    ">
                        ${totalComplaints} Total
                    </span>
                </h4>

                ${totalComplaints === 0 ? `
                    <div style="text-align: center; padding: 40px 20px; color: #666;">
                        <i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 16px; opacity: 0.3;"></i>
                        <p style="font-size: 16px; margin: 0;">No complaints found</p>
                    </div>
                ` : `
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: rgba(139, 92, 246, 0.1); border-bottom: 2px solid rgba(139, 92, 246, 0.3);">
                                    <th style="padding: 12px; text-align: left; font-size: 13px; color: #9ca3af; font-weight: 600;">#</th>
                                    <th style="padding: 12px; text-align: left; font-size: 13px; color: #9ca3af; font-weight: 600;">Category</th>
                                    <th style="padding: 12px; text-align: left; font-size: 13px; color: #9ca3af; font-weight: 600;">Description</th>
                                    <th style="padding: 12px; text-align: left; font-size: 13px; color: #9ca3af; font-weight: 600;">Status</th>
                                    <th style="padding: 12px; text-align: left; font-size: 13px; color: #9ca3af; font-weight: 600;">Date</th>
                                    <th style="padding: 12px; text-align: center; font-size: 13px; color: #9ca3af; font-weight: 600;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${complaints.map((complaint, index) => `
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05); transition: background 0.2s;">
                                        <td style="padding: 12px; color: #fff; font-weight: 600;">${index + 1}</td>
                                        <td style="padding: 12px; color: #FFD100; font-weight: 500;">${complaint.category || 'N/A'}</td>
                                        <td style="padding: 12px; color: #C0C0C0; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                            ${complaint.description || 'No description'}
                                        </td>
                                        <td style="padding: 12px;">${getStatusBadge(complaint.status)}</td>
                                        <td style="padding: 12px; color: #888; font-size: 12px;">${formatDate(complaint.created_at)}</td>
                                        <td style="padding: 12px; text-align: center;">
                                            <button onclick="viewComplaintFromUser(${complaint.id})" 
                                                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 16px rgba(0, 200, 255, 0.5)'"
                                                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(0, 200, 255, 0.3)'"
                                                style="
                                                    background: linear-gradient(135deg, #00C8FF 0%, #0284C7 100%);
                                                    color: white;
                                                    border: none;
                                                    padding: 6px 14px;
                                                    border-radius: 6px;
                                                    cursor: pointer;
                                                    font-size: 12px;
                                                    font-weight: 600;
                                                    transition: all 0.3s ease;
                                                    box-shadow: 0 2px 8px rgba(0, 200, 255, 0.3);
                                                ">
                                                <i class="fas fa-eye"></i> View
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `}
            </div>
        </div>
    `;

    modal.classList.add('active');
}

async function viewComplaintFromUser(complaintId) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${getAPIBase()}/api/head/complaints`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.status === 401) {
            handle401Error(response, 'viewComplaintFromUser');
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to fetch complaint details');
        }

        let data = await response.json();
        const list = Array.isArray(data) ? data : (data.complaints || []);
        const cid = Number(complaintId);
        const complaint = list.find(c => Number(c.id) === cid);

        if (!complaint) {
            showToast('Complaint not found', 'error');
            return;
        }

        displayComplaintDetailsBox(complaint);
    } catch (error) {
        console.error('Error loading complaint details:', error);
        showToast('Failed to load complaint details', 'error');
    }
}

function displayComplaintDetailsBox(complaint) {
    const modal = document.getElementById('complaintFromUserModal');
    const body = document.getElementById('complaintFromUserBody');
    
    if (!modal || !body) return;

    const getStatusBadge = (status) => {
        const badges = {
            pending: { color: '#FFD100', text: 'Pending', icon: 'fa-clock' },
            'in-progress': { color: '#00C8FF', text: 'In Progress', icon: 'fa-spinner' },
            resolved: { color: '#10B981', text: 'Resolved', icon: 'fa-check-circle' },
            rejected: { color: '#EF4444', text: 'Rejected', icon: 'fa-times-circle' }
        };
        const badge = badges[status] || badges.pending;
        return `
            <span style="
                background: ${badge.color}22;
                color: ${badge.color};
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            ">
                <i class="fas ${badge.icon}"></i>
                ${badge.text}
            </span>
        `;
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    body.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 20px;">
            <!-- Complaint Header -->
            <div style="
                background: linear-gradient(135deg, rgba(255, 209, 0, 0.15) 0%, rgba(255, 165, 0, 0.15) 100%);
                border-left: 4px solid #FFD100;
                padding: 20px;
                border-radius: 12px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px;">
                    <div>
                        <h4 style="margin: 0 0 8px 0; color: #FFD100; font-size: 20px; font-weight: 700;">
                            Complaint #${complaint.id}
                        </h4>
                        <p style="margin: 0; color: #9ca3af; font-size: 14px;">
                            <i class="fas fa-user"></i> ${complaint.user_name || 'Anonymous'}
                        </p>
                    </div>
                    <div style="text-align: right;">
                        ${getStatusBadge(complaint.status)}
                        <p style="margin: 8px 0 0 0; font-size: 13px; color: #888;">
                            <i class="fas fa-calendar"></i> ${formatDate(complaint.created_at)}
                        </p>
                    </div>
                </div>
            </div>

            <!-- Complaint Details Grid -->
            <div style="
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
            ">
                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;">
                        <i class="fas fa-tag"></i> CATEGORY
                    </div>
                    <div style="color: #FFD100; font-weight: 600; font-size: 15px;">
                        ${complaint.category || 'N/A'}
                    </div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;">
                        <i class="fas fa-map-marker-alt"></i> DISTRICT
                    </div>
                    <div style="color: #00C8FF; font-weight: 600; font-size: 15px;">
                        ${complaint.district || 'N/A'}
                    </div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;">
                        <i class="fas fa-user-tie"></i> ASSIGNED ADMIN
                    </div>
                    <div style="color: #8b5cf6; font-weight: 600; font-size: 15px;">
                        ${complaint.admin_name || 'Unassigned'}
                    </div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 6px;">
                        <i class="fas fa-exclamation-circle"></i> PRIORITY
                    </div>
                    <div style="color: ${complaint.priority === 'high' ? '#EF4444' : complaint.priority === 'medium' ? '#FFD100' : '#10B981'}; font-weight: 600; font-size: 15px; text-transform: capitalize;">
                        ${complaint.priority || 'Normal'}
                    </div>
                </div>
            </div>

            <!-- Description -->
            <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                <h4 style="margin: 0 0 12px 0; color: #C0C0C0; font-size: 16px; font-weight: 600;">
                    <i class="fas fa-align-left"></i> Description
                </h4>
                <p style="margin: 0; line-height: 1.7; color: #fff; white-space: pre-wrap; font-size: 14px;">
                    ${complaint.description || 'No description provided'}
                </p>
            </div>

            <!-- Proof/Attachments -->
            ${complaint.proof_path ? `
                <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                    <h4 style="margin: 0 0 12px 0; color: #C0C0C0; font-size: 16px; font-weight: 600;">
                        <i class="fas fa-paperclip"></i> Proof/Attachment
                    </h4>
                    <button onclick="window.open('${getAPIBase()}/api/media/${complaint.proof_path}', '_blank')" 
                        style="
                            background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                            color: white;
                            border: none;
                            padding: 10px 20px;
                            border-radius: 8px;
                            cursor: pointer;
                            font-weight: 600;
                            transition: all 0.3s ease;
                        ">
                        <i class="fas fa-download"></i> View Attachment
                    </button>
                </div>
            ` : ''}

            <!-- Response Section -->
            ${complaint.admin_response ? `
                <div style="background: rgba(0, 200, 255, 0.1); padding: 20px; border-radius: 12px; border-left: 4px solid #00C8FF;">
                    <h4 style="margin: 0 0 12px 0; color: #00C8FF; font-size: 16px; font-weight: 600;">
                        <i class="fas fa-reply"></i> Admin Response
                    </h4>
                    <p style="margin: 0; line-height: 1.7; color: #fff; white-space: pre-wrap; font-size: 14px;">
                        ${complaint.admin_response}
                    </p>
                    ${complaint.response_date ? `
                        <p style="margin: 12px 0 0 0; font-size: 12px; color: #888;">
                            <i class="fas fa-clock"></i> Responded on ${formatDate(complaint.response_date)}
                        </p>
                    ` : ''}
                </div>
            ` : ''}
        </div>
    `;

    modal.classList.add('active');
}

// ==================== COMPLAINT SELECTION FUNCTIONS ====================

// Store selected complaint IDs
let selectedComplaintIds = new Set();

// Close all dropdowns
function closeAllComplaintDropdowns() {
  document.querySelectorAll('.complaint-dropdown').forEach(dropdown => {
    dropdown.style.display = 'none';
  });
}

// Toggle complaint dropdown
function toggleComplaintDropdown(complaintId, event) {
  event.stopPropagation();
  
  const dropdown = document.getElementById(`dropdown-${complaintId}`);
  if (!dropdown) return;
  
  // Close other dropdowns
  document.querySelectorAll('.complaint-dropdown').forEach(d => {
    if (d.id !== `dropdown-${complaintId}`) {
      d.style.display = 'none';
    }
  });
  
  // Toggle this dropdown
  dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
}

// Select complaint
function selectComplaint(complaintId) {
  const row = document.querySelector(`tr[data-complaint-id="${complaintId}"]`);
  if (!row) return;
  
  selectedComplaintIds.add(complaintId);
  row.classList.add('selected-row');
  closeAllComplaintDropdowns();
  showToast(`Complaint #${complaintId} selected`, 'success');
  
  console.log('[Selection] Selected complaints:', Array.from(selectedComplaintIds));
}

// Unselect complaint
function unselectComplaint(complaintId) {
  const row = document.querySelector(`tr[data-complaint-id="${complaintId}"]`);
  if (!row) return;
  
  selectedComplaintIds.delete(complaintId);
  row.classList.remove('selected-row');
  closeAllComplaintDropdowns();
  showToast(`Complaint #${complaintId} unselected`, 'info');
  
  console.log('[Selection] Selected complaints:', Array.from(selectedComplaintIds));
}

// Close dropdowns when clicking outside (optimized with event delegation)
document.addEventListener('click', function(event) {
  // Skip if clicking on dropdown or id element
  if (event.target.closest('.complaint-dropdown') || event.target.closest('[id^="complaint-id-"]')) {
    return;
  }
  
  // Efficiently close all dropdowns
  const dropdowns = document.querySelectorAll('.complaint-dropdown[style*="display: block"]');
  if (dropdowns.length > 0) {
    dropdowns.forEach(dropdown => {
      dropdown.style.display = 'none';
    });
  }
}, { passive: true });

// ==================== GLOBAL DATA REFRESH FUNCTION ====================
// Force refresh all data across the dashboard
function refreshAllData() {
  console.log('[REFRESH] Refreshing all dashboard data...');
  
  try {
    // Reload dashboard statistics
    if (typeof loadDashboardStats === 'function') {
      loadDashboardStats();
    }
    
    // Reload admin list
    if (typeof loadAdminList === 'function') {
      loadAdminList();
    }
    
    // Reload user list
    if (typeof loadAllUsers === 'function') {
      loadAllUsers();
    }
    
    // Reload complaints
    if (typeof loadComplaints === 'function') {
      loadComplaints();
    }
    
    // Reload feedback
    if (typeof loadAllFeedback === 'function') {
      loadAllFeedback();
    }
    
    console.log('[REFRESH] All data refresh initiated');
    showToast('Dashboard data refreshed', 'success');
  } catch (error) {
    console.error('[REFRESH] Error refreshing data:', error);
    showToast('Error refreshing data', 'error');
  }
}

// ==================== ADMIN SELECTION MODE FUNCTIONS ====================
function toggleAdminSelectionMode() {
    console.log('[ADMIN] toggleAdminSelectionMode');
    const checkboxes = document.querySelectorAll('.admin-checkbox-column');
    const deleteBtn = document.getElementById('deleteSelectedAdminsBtn');
    const printBtn = document.getElementById('printSelectedAdminsBtn');
    const toggleBtn = document.getElementById('toggleAdminSelectionBtn');
    
    const isHidden = checkboxes[0]?.style.display === 'none';
    
    checkboxes.forEach(cb => cb.style.display = isHidden ? 'table-cell' : 'none');
    
    if (isHidden) {
        // Entering selection mode
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (printBtn) printBtn.style.display = 'none';
        if (toggleBtn) {
            toggleBtn.innerHTML = '<i class="fas fa-times"></i> Cancel';
            toggleBtn.classList.remove('btn-secondary');
            toggleBtn.classList.add('btn-warning');
        }
    } else {
        // Exiting selection mode
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (printBtn) printBtn.style.display = 'none';
        if (toggleBtn) {
            toggleBtn.innerHTML = '<i class="fas fa-check-square"></i> Select';
            toggleBtn.classList.remove('btn-warning');
            toggleBtn.classList.add('btn-secondary');
        }
        document.querySelectorAll('.admin-checkbox').forEach(cb => cb.checked = false);
    }
}

function toggleAdminSelectAll() {
    console.log('[ADMIN] toggleAdminSelectAll');
    const selectAll = document.getElementById('adminSelectAll');
    const checkboxes = document.querySelectorAll('.admin-checkbox');
    checkboxes.forEach(cb => cb.checked = selectAll.checked);
    updateAdminSelectionButtons();
}

function updateAdminSelectionButtons() {
    const checked = document.querySelectorAll('.admin-checkbox:checked');
    const deleteBtn = document.getElementById('deleteSelectedAdminsBtn');
    const printBtn = document.getElementById('printSelectedAdminsBtn');
    const count = checked.length;
    
    if (count > 0) {
        if (deleteBtn) {
            deleteBtn.style.display = 'inline-block';
            deleteBtn.innerHTML = `<i class=\"fas fa-trash\"></i> Delete Selected (${count})`;
        }
        if (printBtn) {
            printBtn.style.display = 'inline-block';
            printBtn.innerHTML = `<i class=\"fas fa-file-pdf\"></i> Print Selected (${count})`;
        }
    } else {
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (printBtn) printBtn.style.display = 'none';
    }
}

function printSelectedAdmins() {
    console.log('[ADMIN] printSelectedAdmins');
    const checked = document.querySelectorAll('.admin-checkbox:checked');
    if (checked.length === 0) {
        showToast('No admins selected', 'warning');
        return;
    }
    
    const ids = Array.from(checked).map(cb => cb.dataset.id);
    
    const token = localStorage.getItem('token');
    if (!token) {
        showToast('Please login again', 'error');
        return;
    }
    
    const printBtn = document.getElementById('printSelectedAdminsBtn');
    if (printBtn) {
        const originalText = printBtn.innerHTML;
        printBtn.innerHTML = '<i class=\"fas fa-spinner fa-spin\"></i> Generating PDF...';
        printBtn.disabled = true;
        
        fetch(`${getAPIBase()}/api/head/export/admins-pdf?ids=${ids.join(',')}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to generate PDF');
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `selected_admins_${new Date().getTime()}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast(`PDF with ${ids.length} admin(s) downloaded!`, 'success');
        })
        .catch(error => {
            console.error('PDF generation error:', error);
            showToast('Failed to generate PDF', 'error');
        })
        .finally(() => {
            if (printBtn) {
                printBtn.innerHTML = originalText;
                printBtn.disabled = false;
            }
        });
    }
}

function deleteSelectedAdmins() {
    console.log('[ADMIN] deleteSelectedAdmins');
    const checked = document.querySelectorAll('.admin-checkbox:checked');
    if (checked.length === 0) {
        showToast('No admins selected', 'warning');
        return;
    }
    
    const ids = Array.from(checked).map(cb => cb.dataset.id);
    
    showConfirmModal(
        'Delete Selected Admins',
        `Are you sure you want to delete ${ids.length} admin(s)? This action cannot be undone.`,
        async () => {
            try {
                const token = localStorage.getItem('token');
                for (const id of ids) {
                    await fetch(`${getAPIBase()}/api/head/admins/${id}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                }
                showToast(`${ids.length} admin(s) deleted`, 'success');
                loadAdminList();
                toggleAdminSelectionMode(); // Exit selection mode
            } catch (error) {
                console.error('[ADMIN] Delete error:', error);
                showToast('Failed to delete admins', 'error');
            }
        },
        'Delete All',
        'Cancel',
        'danger'
    );
}

function deleteSelectedUsers() {
    console.log('[USER] deleteSelectedUsers');
    const checked = document.querySelectorAll('.user-checkbox:checked');
    if (checked.length === 0) {
        showToast('No users selected', 'warning');
        return;
    }
    
    const ids = Array.from(checked).map(cb => cb.dataset.id);
    
    showConfirmModal(
        'Delete Selected Users',
        `Are you sure you want to delete ${ids.length} user(s)? This action cannot be undone.`,
        async () => {
            try {
                const token = localStorage.getItem('token');
                for (const id of ids) {
                    await fetch(`${getAPIBase()}/api/head/users/${id}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                }
                showToast(`${ids.length} user(s) deleted`, 'success');
                loadAllUsers();
                toggleUserSelectionMode(); // Exit selection mode
            } catch (error) {
                console.error('[USER] Delete error:', error);
                showToast('Failed to delete users', 'error');
            }
        },
        'Delete All',
        'Cancel',
        'danger'
    );
}

// ==================== USER SELECTION MODE FUNCTIONS ====================
function toggleUserSelectionMode() {
    console.log('[USER] toggleUserSelectionMode');
    const checkboxes = document.querySelectorAll('.user-checkbox-column');
    const deleteBtn = document.getElementById('deleteSelectedUsersBtn');
    const printBtn = document.getElementById('printSelectedUsersBtn');
    const toggleBtn = document.getElementById('toggleUserSelectionBtn');
    
    const isHidden = checkboxes[0]?.style.display === 'none';
    
    checkboxes.forEach(cb => cb.style.display = isHidden ? 'table-cell' : 'none');
    
    if (isHidden) {
        // Entering selection mode
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (printBtn) printBtn.style.display = 'none';
        if (toggleBtn) {
            toggleBtn.innerHTML = '<i class="fas fa-times"></i> Cancel';
            toggleBtn.classList.remove('btn-secondary');
            toggleBtn.classList.add('btn-warning');
        }
    } else {
        // Exiting selection mode
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (printBtn) printBtn.style.display = 'none';
        if (toggleBtn) {
            toggleBtn.innerHTML = '<i class="fas fa-check-square"></i> Select';
            toggleBtn.classList.remove('btn-warning');
            toggleBtn.classList.add('btn-secondary');
        }
        document.querySelectorAll('.user-checkbox').forEach(cb => cb.checked = false);
    }
}

function toggleUserSelectAll() {
    console.log('[USER] toggleUserSelectAll');
    const selectAll = document.getElementById('userSelectAll');
    const checkboxes = document.querySelectorAll('.user-checkbox');
    checkboxes.forEach(cb => cb.checked = selectAll.checked);
    updateUserSelectionButtons();
}

function updateUserSelectionButtons() {
    const checked = document.querySelectorAll('.user-checkbox:checked');
    const deleteBtn = document.getElementById('deleteSelectedUsersBtn');
    const printBtn = document.getElementById('printSelectedUsersBtn');
    const count = checked.length;
    
    if (count > 0) {
        if (deleteBtn) {
            deleteBtn.style.display = 'inline-block';
            deleteBtn.innerHTML = `<i class=\"fas fa-trash\"></i> Delete Selected (${count})`;
        }
        if (printBtn) {
            printBtn.style.display = 'inline-block';
            printBtn.innerHTML = `<i class=\"fas fa-file-pdf\"></i> Print Selected (${count})`;
        }
    } else {
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (printBtn) printBtn.style.display = 'none';
    }
}

function printSelectedUsers() {
    console.log('[USER] printSelectedUsers');
    const checked = document.querySelectorAll('.user-checkbox:checked');
    if (checked.length === 0) {
        showToast('No users selected', 'warning');
        return;
    }
    
    const ids = Array.from(checked).map(cb => cb.dataset.id);
    
    const token = localStorage.getItem('token');
    if (!token) {
        showToast('Please login again', 'error');
        return;
    }
    
    const printBtn = document.getElementById('printSelectedUsersBtn');
    if (printBtn) {
        const originalText = printBtn.innerHTML;
        printBtn.innerHTML = '<i class=\"fas fa-spinner fa-spin\"></i> Generating PDF...';
        printBtn.disabled = true;
        
        fetch(`${getAPIBase()}/api/head/export/users-pdf?ids=${ids.join(',')}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to generate PDF');
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `selected_users_${new Date().getTime()}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast(`PDF with ${ids.length} user(s) downloaded!`, 'success');
        })
        .catch(error => {
            console.error('PDF generation error:', error);
            showToast('Failed to generate PDF', 'error');
        })
        .finally(() => {
            if (printBtn) {
                printBtn.innerHTML = originalText;
                printBtn.disabled = false;
            }
        });
    }
}

// Make functions globally accessible
window.toggleAdminSelectionMode = toggleAdminSelectionMode;
window.toggleAdminSelectAll = toggleAdminSelectAll;
window.updateAdminSelectionButtons = updateAdminSelectionButtons;
window.printSelectedAdmins = printSelectedAdmins;
window.deleteSelectedAdmins = deleteSelectedAdmins;

// ============================================
// NEW FEATURES: Media Gallery, User Complaints, Mobile Menu
// ============================================

// View complaint media in full gallery modal
async function viewComplaintMedia(complaintId) {
    const modal = document.getElementById('mediaGalleryModal');
    const body = document.getElementById('mediaGalleryBody');
    const title = document.getElementById('mediaGalleryTitle');
    
    if (!modal || !body) {
        console.error('Media gallery modal not found');
        return;
    }
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${getAPIBase()}/api/complaints/${complaintId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) throw new Error('Failed to load complaint');
        
        const complaint = await response.json();
        
        if (!complaint.media_files || complaint.media_files.length === 0) {
            body.innerHTML = '<div style="text-align: center; padding: 40px; color: #888;"><i class="fas fa-image" style="font-size: 48px; margin-bottom: 16px; opacity: 0.3;"></i><p>No media attachments</p></div>';
        } else {
            title.textContent = `Media Gallery - Complaint #${complaintId}`;
            
            const mediaHTML = complaint.media_files.map((file, index) => {
                let fileUrl = file.file_path;
                if (!fileUrl.startsWith('http')) {
                    const apiBase = getAPIBase();
                    // Robust path handling: check if uploads/ already exists in the path
                    if (fileUrl.startsWith('uploads/')) {
                        fileUrl = `${apiBase}/${fileUrl}`;
                    } else {
                        fileUrl = fileUrl.startsWith('/') 
                            ? `${apiBase}/uploads${fileUrl}` 
                            : `${apiBase}/uploads/${fileUrl}`;
                    }
                }
                
                const isImage = file.mime_type && file.mime_type.startsWith('image/');
                const isPDF = file.mime_type && file.mime_type.includes('pdf');
                const isVideo = file.mime_type && file.mime_type.startsWith('video/');
                
                return `
                    <div style="background: var(--card-bg); border: 2px solid rgba(255,215,0,0.3); border-radius: 16px; overflow: hidden; margin-bottom: 20px;">
                        <div style="padding: 16px; background: rgba(0,0,0,0.3); border-bottom: 1px solid rgba(255,215,0,0.2);">
                            <h4 style="margin: 0; color: #FFD700; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                                <i class="fas fa-${isPDF ? 'file-pdf' : isVideo ? 'video' : 'image'}"></i>
                                ${file.file_name || `Attachment ${index + 1}`}
                            </h4>
                        </div>
                        <div style="padding: 20px; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.5); min-height: 300px;">
                            ${isImage ? `
                                <img src="${fileUrl}" alt="${file.file_name}" 
                                     style="max-width: 100%; max-height: 500px; object-fit: contain; border-radius: 8px; cursor: pointer;"
                                     onclick="openMediaViewer('${fileUrl}', '${file.mime_type}', '${file.file_name}')"
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">
                                <div style="display: none; flex-direction: column; align-items: center; gap: 16px; color: #dc3545;">
                                    <i class="fas fa-exclamation-triangle" style="font-size: 48px;"></i>
                                    <p>Failed to load image</p>
                                </div>
                            ` : isVideo ? `
                                <video controls style="max-width: 100%; max-height: 500px; border-radius: 8px;">
                                    <source src="${fileUrl}" type="${file.mime_type}">
                                    Your browser does not support the video tag.
                                </video>
                            ` : isPDF ? `
                                <iframe src="${fileUrl}" style="width: 100%; height: 500px; border: none; border-radius: 8px;"></iframe>
                            ` : `
                                <div style="text-align: center; padding: 40px;">
                                    <i class="fas fa-file-alt" style="font-size: 64px; color: #FFD700; margin-bottom: 16px;"></i>
                                    <p style="color: var(--text-200); margin-bottom: 16px;">${file.file_name}</p>
                                    <a href="${fileUrl}" download="${file.file_name}" class="btn btn-primary">
                                        <i class="fas fa-download"></i> Download
                                    </a>
                                </div>
                            `}
                        </div>
                    </div>
                `;
            }).join('');
            
            body.innerHTML = `
                <div style="display: grid; gap: 20px;">
                    ${mediaHTML}
                </div>
            `;
        }
        
        modal.style.display = 'grid';
        modal.classList.add('active');
    } catch (error) {
        console.error('Error loading media:', error);
        showToast('Failed to load media files', 'error');
    }
}

function closeMediaGalleryModal() {
    const modal = document.getElementById('mediaGalleryModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}

// View user complaints in user management
async function viewUserComplaints(userId, userName) {
    const modal = document.getElementById('userComplaintsModal');
    const body = document.getElementById('userComplaintsBody');
    const title = document.getElementById('userComplaintsModalTitle');
    
    if (!modal || !body) {
        console.error('User complaints modal not found');
        return;
    }
    
    title.textContent = `Complaints by ${userName}`;
    body.innerHTML = '<div style="text-align: center; padding: 40px; color: #888;"><i class="fas fa-spinner fa-spin" style="font-size: 32px; margin-bottom: 12px;"></i><p>Loading complaints...</p></div>';
    
    modal.style.display = 'grid';
    modal.classList.add('active');
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${getAPIBase()}/api/complaints`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) throw new Error('Failed to load complaints');
        
        const allComplaints = await response.json();
        const userComplaints = allComplaints.filter(c => c.user_id === userId);
        
        if (userComplaints.length === 0) {
            body.innerHTML = `
                <div style="text-align: center; padding: 60px 20px; color: #888;">
                    <i class="fas fa-clipboard-list" style="font-size: 64px; margin-bottom: 20px; opacity: 0.3;"></i>
                    <p style="font-size: 18px; color: var(--text-200);">No complaints found</p>
                    <p style="font-size: 14px; color: var(--text-400);">This user hasn't filed any complaints yet</p>
                </div>
            `;
        } else {
            const complaintsHTML = userComplaints.map(complaint => {
                const statusColors = {
                    'PENDING': { bg: '#ef5b5b', text: '#fff' },
                    'IN_PROGRESS': { bg: '#3b82f6', text: '#fff' },
                    'RESOLVED': { bg: '#16c782', text: '#fff' }
                };
                const status = complaint.status ? complaint.status.toUpperCase() : 'PENDING';
                const colors = statusColors[status] || statusColors['PENDING'];
                
                return `
                    <div style="background: var(--card-bg); border: 2px solid rgba(255,215,0,0.2); border-radius: 16px; padding: 20px; margin-bottom: 16px; transition: all 0.3s ease; cursor: pointer;"
                         onmouseover="this.style.borderColor='rgba(255,215,0,0.5)'; this.style.transform='translateY(-2px)'"
                         onmouseout="this.style.borderColor='rgba(255,215,0,0.2)'; this.style.transform='translateY(0)'"
                         onclick="window.HeadComplaintActions.viewComplaint(${complaint.id})">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                            <div>
                                <h4 style="color: #FFD700; margin: 0 0 8px 0; font-size: 18px;">
                                    <i class="fas fa-hashtag"></i> Complaint #${complaint.id}
                                </h4>
                                <p style="color: var(--text-300); margin: 0; font-size: 13px;">
                                    <i class="fas fa-calendar"></i> ${new Date(complaint.created_at).toLocaleDateString()}
                                </p>
                            </div>
                            <span style="background: ${colors.bg}; color: ${colors.text}; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; white-space: nowrap;">
                                ${status}
                            </span>
                        </div>
                        <div style="margin-bottom: 12px;">
                            <p style="color: var(--text-200); margin: 0 0 8px 0; font-size: 14px;">
                                <strong style="color: var(--text-100);"><i class="fas fa-route"></i> Route:</strong> ${complaint.route || 'N/A'}
                            </p>
                            <p style="color: var(--text-200); margin: 0 0 8px 0; font-size: 14px;">
                                <strong style="color: var(--text-100);"><i class="fas fa-bus"></i> Bus:</strong> ${complaint.bus_number || 'N/A'}
                            </p>
                            <p style="color: var(--text-200); margin: 0; font-size: 14px;">
                                <strong style="color: var(--text-100);"><i class="fas fa-tag"></i> Category:</strong> ${complaint.category || complaint.complaint_type || 'General'}
                            </p>
                        </div>
                        ${complaint.description ? `
                            <p style="color: var(--text-300); margin: 12px 0 0 0; font-size: 13px; line-height: 1.6; border-left: 3px solid rgba(255,215,0,0.3); padding-left: 12px;">
                                ${complaint.description.substring(0, 150)}${complaint.description.length > 150 ? '...' : ''}
                            </p>
                        ` : ''}
                        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,215,0,0.1); display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: var(--text-400); font-size: 12px;">
                                <i class="fas fa-user-shield"></i> ${complaint.admin_name || 'Not assigned'}
                            </span>
                            <span style="color: var(--primary); font-size: 12px; font-weight: 600;">
                                Click to view details <i class="fas fa-arrow-right"></i>
                            </span>
                        </div>
                    </div>
                `;
            }).join('');
            
            body.innerHTML = `
                <div style="margin-bottom: 16px; padding: 16px; background: rgba(255,215,0,0.1); border-radius: 12px; border-left: 4px solid #FFD700;">
                    <p style="margin: 0; color: var(--text-100); font-size: 15px;">
                        <strong>${userComplaints.length}</strong> complaint${userComplaints.length !== 1 ? 's' : ''} found
                    </p>
                </div>
                ${complaintsHTML}
            `;
        }
    } catch (error) {
        console.error('Error loading user complaints:', error);
        body.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #dc3545;">
                <i class="fas fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 16px;"></i>
                <p>Failed to load complaints</p>
            </div>
        `;
    }
}

function closeUserComplaintsModal() {
    const modal = document.getElementById('userComplaintsModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}

// Mobile menu toggle
function toggleMobileMenu() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.mobile-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('active');
    }
}

function closeMobileMenu() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.mobile-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.remove('mobile-open');
        overlay.classList.remove('active');
    }
}

// Make new functions globally accessible
window.viewComplaintMedia = viewComplaintMedia;
window.closeMediaGalleryModal = closeMediaGalleryModal;
window.viewUserComplaints = viewUserComplaints;
window.closeUserComplaintsModal = closeUserComplaintsModal;
window.toggleMobileMenu = toggleMobileMenu;
window.closeMobileMenu = closeMobileMenu;
window.toggleUserSelectionMode = toggleUserSelectionMode;
window.toggleUserSelectAll = toggleUserSelectAll;
window.updateUserSelectionButtons = updateUserSelectionButtons;
window.printSelectedUsers = printSelectedUsers;
window.deleteSelectedUsers = deleteSelectedUsers;
window.deleteSelectedDistrict = deleteSelectedDistrict;
window.deleteSelectedRoutes = deleteSelectedRoutes;

// Make functions global
window.toggleComplaintDropdown = toggleComplaintDropdown;
window.selectComplaint = selectComplaint;
window.unselectComplaint = unselectComplaint;
window.refreshAllData = refreshAllData;
