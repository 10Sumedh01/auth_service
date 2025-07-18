// dark-mode.js
class DarkMode {
    constructor() {
        this.darkModeKey = 'dark-mode-enabled';
        this.isDarkMode = localStorage.getItem(this.darkModeKey) === 'true';
        this.init();
    }

    init() {
        this.createToggleButton();
        this.applyDarkMode();
        this.addEventListeners();
    }

    createToggleButton() {
        // Create floating toggle button
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'dark-mode-toggle';
        toggleBtn.innerHTML = this.isDarkMode ? '☀️' : '🌙';
        toggleBtn.title = this.isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode';
        
        // Style the button
        Object.assign(toggleBtn.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            width: '50px',
            height: '50px',
            borderRadius: '50%',
            border: 'none',
            background: this.isDarkMode ? '#333' : '#fff',
            color: this.isDarkMode ? '#fff' : '#333',
            fontSize: '20px',
            cursor: 'pointer',
            zIndex: '9999',
            boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
            transition: 'all 0.3s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
        });

        // Add hover effect
        toggleBtn.addEventListener('mouseenter', () => {
            toggleBtn.style.transform = 'scale(1.1)';
        });

        toggleBtn.addEventListener('mouseleave', () => {
            toggleBtn.style.transform = 'scale(1)';
        });

        document.body.appendChild(toggleBtn);
    }

    applyDarkMode() {
        const body = document.body;
        const html = document.documentElement;
        
        if (this.isDarkMode) {
            // Apply dark mode styles
            body.classList.add('dark-mode');
            html.classList.add('dark-mode');
            
            // Add dark mode CSS if not already added
            if (!document.getElementById('dark-mode-styles')) {
                this.injectDarkModeCSS();
            }
        } else {
            // Remove dark mode
            body.classList.remove('dark-mode');
            html.classList.remove('dark-mode');
        }
    }

    injectDarkModeCSS() {
        const darkModeCSS = `
            <style id="dark-mode-styles">
                .dark-mode {
                    filter: invert(1) hue-rotate(180deg) brightness(1.1) contrast(0.9);
                    background-color: #121212 !important;
                }
                
                .dark-mode img,
                .dark-mode video,
                .dark-mode iframe,
                .dark-mode svg,
                .dark-mode [style*="background-image"] {
                    filter: invert(1) hue-rotate(180deg) brightness(1.1) contrast(0.9);
                }
                
                .dark-mode input,
                .dark-mode textarea,
                .dark-mode select {
                    background-color: #333 !important;
                    color: #fff !important;
                    border-color: #555 !important;
                }
                
                .dark-mode .btn-primary {
                    background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
                }
                
                .dark-mode .credential-value {
                    background-color: #222 !important;
                    color: #ccc !important;
                }
                
                .dark-mode .modal-content {
                    background-color: #1a1a1a !important;
                }
                
                .dark-mode .table-container {
                    background-color: #1a1a1a !important;
                }
                
                .dark-mode .search-container {
                    background-color: #1a1a1a !important;
                }
                
                .dark-mode .credentials-section {
                    background-color: #1a1a1a !important;
                }
                
                .dark-mode .app-card {
                    background-color: #1a1a1a !important;
                }
                
                .dark-mode .form-container {
                    background-color: #1a1a1a !important;
                }
                
                .dark-mode .login-container,
                .dark-mode .signup-container,
                .dark-mode .create-app-container {
                    background-color: #1a1a1a !important;
                }
                
                .dark-mode .danger-zone {
                    background-color: #1a1a1a !important;
                    border-color: #dc3545 !important;
                }
                
                .dark-mode #dark-mode-toggle {
                    background: #333 !important;
                    color: #fff !important;
                }
                
                .dark-mode:not(#dark-mode-toggle) {
                    color: #e0e0e0 !important;
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', darkModeCSS);
    }

    toggle() {
        this.isDarkMode = !this.isDarkMode;
        localStorage.setItem(this.darkModeKey, this.isDarkMode.toString());
        this.applyDarkMode();
        this.updateToggleButton();
    }

    updateToggleButton() {
        const toggleBtn = document.getElementById('dark-mode-toggle');
        if (toggleBtn) {
            toggleBtn.innerHTML = this.isDarkMode ? '☀️' : '🌙';
            toggleBtn.title = this.isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode';
            toggleBtn.style.background = this.isDarkMode ? '#333' : '#fff';
            toggleBtn.style.color = this.isDarkMode ? '#fff' : '#333';
        }
    }

    addEventListeners() {
        // Toggle button click
        document.addEventListener('click', (e) => {
            if (e.target.id === 'dark-mode-toggle') {
                this.toggle();
            }
        });

        // Keyboard shortcut (Ctrl/Cmd + Shift + D)
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
                e.preventDefault();
                this.toggle();
            }
        });
    }
}

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new DarkMode();
    });
} else {
    new DarkMode();
}
