/**
 * Real-Time Data Updates System
 * Provides live data synchronization via WebSocket and polling fallback
 */

class RealtimeUpdateManager {
    constructor() {
        this.updateInterval = 5000; // 5 seconds
        this.activeTimers = {};
        this.updateCallbacks = {};
        this.lastUpdateTimestamps = {};
        this.isActive = true;
        this.socket = null;
        this.useWebSocket = true;
        
        // Initialize WebSocket
        this.initializeWebSocket();
    }

    /**
     * Initialize Socket.IO connection
     */
    initializeWebSocket() {
        if (typeof io === 'undefined') {
            console.warn('[RealtimeUpdate] Socket.IO not available, using polling only');
            this.useWebSocket = false;
            return;
        }
        
        const token = localStorage.getItem('token');
        if (!token) {
            console.log('[RealtimeUpdate] No token found, WebSocket disabled');
            this.useWebSocket = false;
            return;
        }
        
        const API_BASE = window.API_BASE || 'http://127.0.0.1:5000';
        console.log('[RealtimeUpdate] Connecting WebSocket to:', API_BASE);
        
        this.socket = io(API_BASE, {
            transports: ['polling', 'websocket'],
            upgrade: true,
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5,
            timeout: 20000
        });
        
        this.socket.on('connect', () => {
            console.log('[RealtimeUpdate] WebSocket connected:', this.socket.id);
            this.socket.emit('register', { token: token });
        });
        
        this.socket.on('registered', (data) => {
            console.log('[RealtimeUpdate] Registered for real-time updates:', data);
        });
        
        this.socket.on('disconnect', () => {
            console.log('[RealtimeUpdate] WebSocket disconnected');
        });
        
        this.socket.on('error', (error) => {
            console.error('[RealtimeUpdate] WebSocket error:', error);
        });
        
        // Register event listeners for real-time updates
        this.setupWebSocketEvents();
    }
    
    /**
     * Setup WebSocket event listeners
     */
    setupWebSocketEvents() {
        if (!this.socket) return;
        
        // Complaints updated
        this.socket.on('complaints_updated', (data) => {
            console.log('[RealtimeUpdate] Complaints updated via WebSocket:', data);
            this.triggerCallback('complaints');
            this.triggerCallback('dashboard');
        });
        
        // Complaint assigned
        this.socket.on('complaint_assigned', (data) => {
            console.log('[RealtimeUpdate] Complaint assigned via WebSocket:', data);
            this.triggerCallback('complaints');
            this.triggerCallback('assignments');
            this.showNotification('New complaint assigned to you!', 'info');
        });
        
        // Complaint status changed
        this.socket.on('complaint_status_changed', (data) => {
            console.log('[RealtimeUpdate] Complaint status changed via WebSocket:', data);
            this.triggerCallback('complaints');
        });
        
        // Users updated
        this.socket.on('users_updated', (data) => {
            console.log('[RealtimeUpdate] Users updated via WebSocket:', data);
            this.triggerCallback('users');
        });
        
        // Admin/staff assignments updated
        this.socket.on('assignments_updated', (data) => {
            console.log('[RealtimeUpdate] Assignments updated via WebSocket:', data);
            this.triggerCallback('assignments');
            this.triggerCallback('admins');
        });
        
        // Notifications
        this.socket.on('new_notification', (data) => {
            console.log('[RealtimeUpdate] New notification via WebSocket:', data);
            this.triggerCallback('notifications');
            if (data.message) {
                this.showNotification(data.message, 'info');
            }
        });
    }
    
    /**
     * Trigger callback by key
     */
    triggerCallback(key) {
        if (this.updateCallbacks[key]) {
            this.executeUpdate(key);
        }
    }
    
    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#22c55e' : '#3b82f6'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            max-width: 350px;
            animation: slideInRight 0.3s ease;
        `;
        notification.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i> ${message}`;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.3s';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    /**
     * Register a callback for real-time updates
     * @param {string} key - Unique identifier for this update
     * @param {Function} callback - Function to call with updated data
     * @param {number} interval - Update interval in milliseconds (default: 5000)
     */
    register(key, callback, interval = 5000) {
        // Stop existing timer if any
        this.unregister(key);
        
        this.updateCallbacks[key] = callback;
        this.lastUpdateTimestamps[key] = Date.now();
        
        // Initial call
        this.executeUpdate(key);
        
        // Set up recurring updates
        this.activeTimers[key] = setInterval(() => {
            if (this.isActive) {
                this.executeUpdate(key);
            }
        }, interval);
        
        console.log(`[RealtimeUpdate] Registered: ${key} (interval: ${interval}ms)`);
    }

    /**
     * Execute update for a specific key
     */
    async executeUpdate(key) {
        try {
            const callback = this.updateCallbacks[key];
            if (callback) {
                await callback();
                this.lastUpdateTimestamps[key] = Date.now();
            }
        } catch (error) {
            console.error(`[RealtimeUpdate] Error updating ${key}:`, error);
        }
    }

    /**
     * Unregister a callback
     */
    unregister(key) {
        if (this.activeTimers[key]) {
            clearInterval(this.activeTimers[key]);
            delete this.activeTimers[key];
            delete this.updateCallbacks[key];
            delete this.lastUpdateTimestamps[key];
            console.log(`[RealtimeUpdate] Unregistered: ${key}`);
        }
    }

    /**
     * Pause all updates
     */
    pause() {
        this.isActive = false;
        console.log('[RealtimeUpdate] Paused all updates');
    }

    /**
     * Resume all updates
     */
    resume() {
        this.isActive = true;
        console.log('[RealtimeUpdate] Resumed all updates');
    }

    /**
     * Stop all updates and clear timers
     */
    stopAll() {
        Object.keys(this.activeTimers).forEach(key => {
            clearInterval(this.activeTimers[key]);
        });
        this.activeTimers = {};
        this.updateCallbacks = {};
        this.lastUpdateTimestamps = {};
        this.isActive = false;
        
        // Disconnect WebSocket
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        
        console.log('[RealtimeUpdate] Stopped all updates');
    }

    /**
     * Get status of all active updates
     */
    getStatus() {
        return Object.keys(this.activeTimers).map(key => ({
            key,
            lastUpdate: this.lastUpdateTimestamps[key],
            timeSinceUpdate: Date.now() - this.lastUpdateTimestamps[key],
            isActive: this.isActive
        }));
    }

    /**
     * Force update for a specific key
     */
    forceUpdate(key) {
        if (this.updateCallbacks[key]) {
            console.log(`[RealtimeUpdate] Force updating: ${key}`);
            this.executeUpdate(key);
        }
    }

    /**
     * Force update for all registered keys
     */
    forceUpdateAll() {
        console.log('[RealtimeUpdate] Force updating all');
        Object.keys(this.updateCallbacks).forEach(key => {
            this.executeUpdate(key);
        });
    }
}

// Create global instance
window.realtimeManager = new RealtimeUpdateManager();

// Pause updates when page is hidden (user switched tabs)
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        window.realtimeManager.pause();
    } else {
        window.realtimeManager.resume();
        // Force update when user comes back
        window.realtimeManager.forceUpdateAll();
    }
});

// Stop updates when page is about to unload
window.addEventListener('beforeunload', () => {
    window.realtimeManager.stopAll();
});

// Utility function for easy registration
window.registerRealtimeUpdate = (key, callback, interval) => {
    window.realtimeManager.register(key, callback, interval);
};

window.unregisterRealtimeUpdate = (key) => {
    window.realtimeManager.unregister(key);
};

console.log('[RealtimeUpdate] Real-time update system initialized');

// Add CSS animation for notifications
if (!document.getElementById('realtime-animations')) {
    const style = document.createElement('style');
    style.id = 'realtime-animations';
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
}
