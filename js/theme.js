/* ========================================
   THEME MANAGER
   Dark/Light Theme Toggle with Persistence
   ======================================== */

const ThemeManager = {
    // Storage key for localStorage
    STORAGE_KEY: 'studentbot-theme',
    
    // Initialize theme on page load
    init() {
        // Get saved theme or detect system preference
        const savedTheme = localStorage.getItem(this.STORAGE_KEY);
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
        
        // Apply theme
        this.setTheme(theme);
        
        // Listen for system preference changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(this.STORAGE_KEY)) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });
        
        // Bind toggle button
        const toggleBtn = document.getElementById('themeToggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggle());
        }
        
        console.log('🎨 Theme Manager initialized:', theme);
    },
    
    // Get current theme
    getTheme() {
        return document.documentElement.getAttribute('data-theme') || 'dark';
    },
    
    // Set theme
    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(this.STORAGE_KEY, theme);
        
        // Update meta theme-color for mobile browsers
        const metaTheme = document.querySelector('meta[name="theme-color"]');
        if (metaTheme) {
            metaTheme.setAttribute('content', theme === 'dark' ? '#0f172a' : '#f8fafc');
        }
    },
    
    // Toggle between themes
    toggle() {
        const currentTheme = this.getTheme();
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
        
        // Optional: Show toast notification
        if (typeof Toast !== 'undefined') {
            Toast.show(`Switched to ${newTheme} mode`, 'info');
        }
        
        console.log('🎨 Theme toggled to:', newTheme);
        return newTheme;
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
});
