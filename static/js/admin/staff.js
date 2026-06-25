// static/js/admin/staff.js
class StaffManager {
    constructor() {
        this.apiBase = '/api/restaurants/';
        this.init();
    }

    init() {
        this.checkAuth();
        this.setupEventListeners();
    }

    checkAuth() {
        if (typeof authManager !== 'undefined' && !authManager.isAuthenticated()) {
            window.location.href = '/login/';
        }
    }

    setupEventListeners() {
        // Any additional event listeners
    }

    async loadStaff() {
        try {
            const response = await fetch(`${this.apiBase}staff/`, {
                headers: this.getAuthHeaders()
            });
            const data = await response.json();
            if (data.success) {
                this.renderStaff(data.staff);
            }
        } catch (error) {
            console.error('Error loading staff:', error);
        }
    }

    async saveStaff(staffData) {
        try {
            const response = await fetch(`${this.apiBase}staff/`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify(staffData)
            });
            const data = await response.json();
            if (data.success) {
                showToast('Staff saved successfully!', 'success');
                return data;
            }
        } catch (error) {
            console.error('Error saving staff:', error);
            showToast('Failed to save staff', 'error');
        }
    }

    async toggleStatus(staffId) {
        try {
            const response = await fetch(`${this.apiBase}staff/${staffId}/toggle/`, {
                method: 'POST',
                headers: this.getAuthHeaders()
            });
            const data = await response.json();
            if (data.success) {
                showToast('Status toggled!', 'success');
                return data;
            }
        } catch (error) {
            console.error('Error toggling status:', error);
            showToast('Failed to toggle status', 'error');
        }
    }

    async deleteStaff(staffId) {
        try {
            const response = await fetch(`${this.apiBase}staff/${staffId}/`, {
                method: 'DELETE',
                headers: this.getAuthHeaders()
            });
            if (response.ok) {
                showToast('Staff deleted!', 'success');
                return true;
            }
        } catch (error) {
            console.error('Error deleting staff:', error);
            showToast('Failed to delete staff', 'error');
        }
    }

    getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }
        const csrfToken = this.getCsrfToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        return headers;
    }

    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return null;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.staffManager = new StaffManager();
});

console.log('Staff Management JavaScript loaded');