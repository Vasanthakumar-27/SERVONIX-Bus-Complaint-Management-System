// Dashboard Loading Animation Utility
class DashboardLoader {
    constructor(userName, userRole) {
        this.userName = userName;
        this.userRole = userRole;
        this.loaderElement = null;
        this.particleCount = 30;
    }

    // Create the loader HTML
    createLoader() {
        const loaderHTML = `
            <div class="dashboard-loader" id="dashboardLoader">
                <!-- Hexagon pattern background -->
                <div class="loader-hexagon-pattern"></div>
                
                <!-- Floating glow orbs -->
                <div class="loader-glow-orb"></div>
                <div class="loader-glow-orb"></div>
                <div class="loader-glow-orb"></div>
                
                <!-- Animated particles -->
                <div class="loader-particles" id="loaderParticles"></div>
                
                <!-- Logo with rotating rings -->
                <div class="loader-content">
                    <div class="loader-ring"></div>
                    <div class="loader-ring"></div>
                    <div class="loader-ring"></div>
                    
                    <img src="assets/logo.png" alt="Logo" class="loader-logo" id="loaderLogo">
                    
                    <h2 class="loader-text">Welcome, ${this.userName}!</h2>
                    <p class="loader-subtext">Loading ${this.getRoleName()} Dashboard...</p>
                </div>
                
                <!-- Loading bar -->
                <div class="loader-bar-container">
                    <div class="loader-bar-bg">
                        <div class="loader-bar-fill"></div>
                    </div>
                    <p class="loader-progress-text">Preparing your workspace...</p>
                </div>
            </div>
        `;
        
        // Insert at the beginning of body
        document.body.insertAdjacentHTML('afterbegin', loaderHTML);
        this.loaderElement = document.getElementById('dashboardLoader');
        
        // Create particles
        this.createParticles();
        
        // Handle logo error
        document.getElementById('loaderLogo').addEventListener('error', () => {
            const logo = document.getElementById('loaderLogo');
            logo.style.display = 'none';
            const textLogo = document.createElement('div');
            textLogo.style.cssText = `
                width: 100px;
                height: 100px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2.5rem;
                font-weight: bold;
                color: white;
                background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.1));
                border-radius: 50%;
                border: 3px solid rgba(255,255,255,0.3);
            `;
            textLogo.textContent = 'BC';
            logo.parentNode.insertBefore(textLogo, logo);
        });
    }

    // Create floating particles
    createParticles() {
        const particlesContainer = document.getElementById('loaderParticles');
        
        for (let i = 0; i < this.particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'loader-particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 8 + 's';
            particle.style.animationDuration = (Math.random() * 5 + 5) + 's';
            particlesContainer.appendChild(particle);
        }
    }

    // Get role display name
    getRoleName() {
        const roleNames = {
            'user': 'User',
            'admin': 'Admin',
            'head': 'Head Admin'
        };
        return roleNames[this.userRole] || 'Dashboard';
    }

    // Hide the loader
    hide() {
        if (this.loaderElement) {
            this.loaderElement.classList.add('hidden');
            
            // Remove from DOM after animation
            setTimeout(() => {
                if (this.loaderElement && this.loaderElement.parentNode) {
                    this.loaderElement.parentNode.removeChild(this.loaderElement);
                }
            }, 800);
        }
    }

    // Show the loader with auto-hide
    show(duration = 2000) {
        this.createLoader();
        
        // Auto-hide after duration
        setTimeout(() => {
            this.hide();
        }, duration);
    }
}

// Initialize dashboard loader on page load
function initDashboardLoader() {
    const userName = localStorage.getItem('user_name') || 'User';
    const userRole = localStorage.getItem('user_role') || 'user';
    
    const loader = new DashboardLoader(userName, userRole);
    loader.show(2000); // Show for 2 seconds
}

// Export for use in dashboards
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DashboardLoader, initDashboardLoader };
}
