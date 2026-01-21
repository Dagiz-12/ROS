// static/js/auth-manager.js
class AuthManager {
    
    constructor() {
        this.baseUrl = '/api/auth';
        this.init();
    }

    init() {
        // Check authentication on page load
        this.checkAuth();
    }

    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    getAuthHeaders() {
        const token = localStorage.getItem('access_token');
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCSRFToken()
        };

        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }

        return headers;
    }

    // NEW METHOD ADDED: Check if user is authenticated
    isAuthenticated() {
        // Method 1: Check JWT token
        const token = localStorage.getItem('access_token');
        if (token) {
            // Basic validation - check if token has 3 parts (JWT structure)
            const parts = token.split('.');
            if (parts.length === 3) {
                return true;
            }
        }
        
        // Method 2: Check session cookie
        if (document.cookie.includes('sessionid')) {
            return true;
        }
        
        // Method 3: Check CSRF token (for Django session auth)
        if (this.getCSRFToken()) {
            return true;
        }
        
        return false;
    }

    async checkAuth() {
        const token = localStorage.getItem('access_token');

        // If we have a client-side token, assume authenticated for now
        if (token) return true;

        // No token: try server-side verification (session cookie)
        const serverValid = await this.verifyToken();
        if (serverValid) return true;

        // If still not authenticated, check protected pages and redirect
        const protectedPages = ['/waiter/', '/chef/', '/cashier/', '/restaurant-admin/', '/waste/', '/profit-dashboard/'];
        const currentPath = window.location.pathname;
        if (protectedPages.some(page => currentPath.startsWith(page))) {
            window.location.href = '/login/';
            return false;
        }

        return true;
    }

    async login(username, password) {
    console.log('Auth Manager: Login attempt for', username);
    
    try {
        const response = await fetch(`${this.baseUrl}/login/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({ username, password }),
            credentials: 'include'
        });

        console.log('Login response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Login successful, data received:', data);
            
            // Store the token - CORRECT FIELD NAME IS "token" not "access"
            if (data.token) {
                localStorage.setItem('access_token', data.token);
                console.log('Token stored successfully as access_token');
            } else {
                console.error('No token found in response! Available keys:', Object.keys(data));
            }
            
            // Store user info
            if (data.user) {
                localStorage.setItem('user_role', data.user.role);
                localStorage.setItem('user_id', data.user.id);
                localStorage.setItem('username', data.user.username);
                // Also store the full user object for dashboards that expect `user_data`
                try {
                    localStorage.setItem('user_data', JSON.stringify(data.user));
                } catch (e) {
                    console.warn('Failed to store user_data in localStorage', e);
                }
                console.log('User role stored:', data.user.role);
            } else {
                console.error('No user data in response!');
            }
            
            // DEBUG: Show what's in localStorage
            console.log('LocalStorage after login:', {
                token: localStorage.getItem('access_token'),
                role: localStorage.getItem('user_role'),
                username: localStorage.getItem('username')
            });
            
            return { success: true, data };
        } else {
            const error = await response.json();
            console.error('Login failed:', error);
            return { success: false, error: error.message || 'Login failed' };
        }
    } catch (error) {
        console.error('Login network error:', error);
        return { success: false, error: 'Network error. Please try again.' };
    }
}

    async logout() {
        try {
            // Call logout API
            await fetch(`${this.baseUrl}/logout/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'include'
            });
        } catch (error) {
            console.log('Logout API error:', error);
        } finally {
            // Clear all storage
            localStorage.clear();
            sessionStorage.clear();
            
            // Clear any cookies by forcing a new session
            document.cookie.split(";").forEach(function(c) {
                document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
            });
            
            // Redirect to login
            window.location.href = '/login/';
        }
    }

    async verifyToken() {
        try {
            const response = await fetch(`${this.baseUrl}/verify-token/`, {
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });

            if (!response.ok) return false;

            // Populate localStorage from server response when available
            try {
                const data = await response.json();
                if (data && data.user) {
                    try { localStorage.setItem('user_data', JSON.stringify(data.user)); } catch (e) {}
                    if (data.user.role) localStorage.setItem('user_role', data.user.role);
                }
            } catch (e) {
                // ignore JSON parse errors
            }

            return true;
        } catch (error) {
            return false;
        }
    }

    redirectBasedOnRole() {
        const role = localStorage.getItem('user_role');
        const routes = {
            'admin': '/admin/',
            'manager': '/restaurant-admin/dashboard/',
            'chef': '/chef/dashboard/',
            'waiter': '/waiter/dashboard/',
            'cashier': '/cashier/dashboard/'
        };
        
        if (role && routes[role]) {
            window.location.href = routes[role];
        } else {
            window.location.href = '/';
        }
    }

    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 px-4 py-2 rounded-lg shadow-lg z-50 transform transition-transform duration-300 ${
            type === 'success' ? 'bg-green-500 text-white' : 
            type === 'error' ? 'bg-red-500 text-white' : 
            'bg-blue-500 text-white'
        }`;
        toast.textContent = message;
        document.body.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateY(0)';
        }, 10);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.transform = 'translateY(-100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Create global instance
window.authManager = new AuthManager();

// Global logout function (used by all templates)
window.logout = function() {
    if (confirm('Are you sure you want to logout?')) {
        window.authManager.logout();
    }
};


// for debugging

// static/js/debug-auth.js
class AuthDebugger {
    static logAuthState() {
        const token = localStorage.getItem('access_token');
        const userData = localStorage.getItem('user_data');
        const userRole = localStorage.getItem('user_role');
        
        console.log('=== AUTH DEBUG ===');
        console.log('Current path:', window.location.pathname);
        console.log('Token exists:', !!token);
        console.log('Token length:', token ? token.length : 0);
        console.log('User data exists:', !!userData);
        console.log('User role:', userRole);
        console.log('User data:', userData ? JSON.parse(userData) : 'None');
        console.log('==================');
    }
    
    static checkProtectedPages() {
        const protectedPages = ['/waiter/', '/chef/', '/cashier/', '/restaurant-admin/'];
        const currentPath = window.location.pathname;
        const isProtected = protectedPages.some(page => currentPath.startsWith(page));
        
        console.log('Current path is protected:', isProtected);
        return isProtected;
    }


    async init() {
    console.log('👨‍🍳 Chef Dashboard Initializing...');
    
    // DEBUG
    AuthDebugger.logAuthState();
    AuthDebugger.checkProtectedPages();
    
    // Rest of init...
}

}

// Add to chef-dashboard.js init: