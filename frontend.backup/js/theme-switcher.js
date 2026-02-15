/**
 * Theme Switcher - Dark Mode / Light Mode Toggle
 * Handles theme switching with localStorage persistence
 */

class ThemeSwitcher {
    constructor() {
        this.themeKey = 'servonix-theme';
        this.init();
    }

    init() {
        // Load saved theme or default to light mode
        const savedTheme = localStorage.getItem(this.themeKey) || 'light';
        this.setTheme(savedTheme, false);
        
        // Listen for theme toggle events
        this.attachEventListeners();
    }

    attachEventListeners() {
        // Find all theme toggle buttons
        const toggleButtons = document.querySelectorAll('.theme-toggle-btn');
        toggleButtons.forEach(button => {
            button.addEventListener('click', () => this.toggleTheme());
        });
    }

    toggleTheme() {
        const currentTheme = this.getCurrentTheme();
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme, true);
    }

    setTheme(theme, save = true) {
        const body = document.body;
        
        if (theme === 'dark') {
            body.classList.add('dark-mode');
            body.classList.remove('light-mode');
            this.updateToggleButtons('light');
        } else {
            body.classList.remove('dark-mode');
            body.classList.add('light-mode');
            this.updateToggleButtons('dark');
        }

        // Save preference
        if (save) {
            localStorage.setItem(this.themeKey, theme);
        }

        // Dispatch custom event for other components
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
    }

    getCurrentTheme() {
        return document.body.classList.contains('dark-mode') ? 'dark' : 'light';
    }

    updateToggleButtons(targetTheme) {
        const toggleButtons = document.querySelectorAll('.theme-toggle-btn');
        toggleButtons.forEach(button => {
            const icon = button.querySelector('i');
            const text = button.querySelector('.theme-text');
            
            if (targetTheme === 'dark') {
                if (icon) {
                    icon.className = 'fas fa-moon';
                }
                if (text) {
                    text.textContent = 'Dark Mode';
                }
            } else {
                if (icon) {
                    icon.className = 'fas fa-sun';
                }
                if (text) {
                    text.textContent = 'Light Mode';
                }
            }
        });
    }
}

// Initialize theme switcher when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.themeSwitcher = new ThemeSwitcher();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeSwitcher;
}
