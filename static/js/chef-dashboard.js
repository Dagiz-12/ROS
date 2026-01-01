// static/js/chef-dashboard.js
class ChefDashboard {
    constructor() {
        this.apiBase = '/api/tables';
        this.pollingInterval = 15000; // 15 seconds for kitchen updates
        this.soundEnabled = true;
        this.lastUpdateTime = null;
        this.currentOrders = {
            confirmed: [],
            preparing: [],
            ready: []
        };
        
        // Audio elements
        this.newOrderSound = document.getElementById('new-order-sound');
        this.orderReadySound = document.getElementById('order-ready-sound');
        // Attach error handlers: if audio fails to load (CORS/403), disable sound to avoid repeated failures
        try {
            if (this.newOrderSound) {
                this.newOrderSound.addEventListener('error', () => {
                    console.warn('newOrderSound failed to load; disabling sound');
                    this.soundEnabled = false;
                });
                this.newOrderSound.addEventListener('canplaythrough', () => {
                    console.log('newOrderSound loaded successfully');
                });
            }
            if (this.orderReadySound) {
                this.orderReadySound.addEventListener('error', () => {
                    console.warn('orderReadySound failed to load; disabling sound');
                    this.soundEnabled = false;
                });
                this.orderReadySound.addEventListener('canplaythrough', () => {
                    console.log('orderReadySound loaded successfully');
                });
            }
        } catch (e) {
            console.warn('Audio setup error:', e);
            this.soundEnabled = false;
        }
        
        this.init();
    }

  async init() {
    console.log('👨‍🍳 Chef Dashboard Initializing...');
    
    // First, check if authManager exists
    if (!window.authManager) {
        console.error('authManager not found, loading it...');
        // Try to reload the page to get authManager
        window.location.reload();
        return;
    }
    
    // Setup UI first (always do this)
    this.setupUI();
    
    // Check authentication
    try {
        if (!await this.checkAuth()) {
            console.log('Auth check failed, stopping initialization');
            return;
        }
    } catch (error) {
        console.error('Auth check error:', error);
        this.showError('Authentication error. Please login again.');
        return;
    }
    
    // Load initial data
    await this.loadKitchenOrders();
    
    // Setup event listeners
    this.setupEventListeners();
    
    // Start polling for updates
    this.startPolling();
    
    // Update timers
    this.updateTime();
    setInterval(() => this.updateTime(), 1000);
    
    console.log('👨‍🍳 Chef Dashboard Ready');
}

    setupUI() {
        // Update user info if available from template
        const userDataElement = document.getElementById('user-data');
        if (userDataElement) {
            try {
                const userData = JSON.parse(userDataElement.dataset.user || '{}');
                if (userData.username) {
                    const nameElement = document.getElementById('chefName');
                    if (nameElement) {
                        nameElement.textContent = userData.username;
                    }
                }
            } catch (e) {
                console.log('Could not parse user data');
            }
        }
    }
// In your existing auth-manager.js, update the checkAuth method:
// static/js/chef-dashboard.js - UPDATE checkAuth method
async checkAuth() {
    console.log('🔐 Chef Dashboard Auth Check...');
    
    // Check localStorage for auth data
    const token = localStorage.getItem('access_token');
    const userData = localStorage.getItem('user_data');
    
    console.log('Token exists:', !!token, 'User data exists:', !!userData);
    
    // If no auth data, redirect to login immediately
    if (!token || !userData) {
        console.warn('No auth data found, redirecting to login...');
        window.authManager.showToast('Please login first', 'error');
        setTimeout(() => {
            window.location.href = '/login/';
        }, 1000);
        return false;
    }
    
    try {
        const user = JSON.parse(userData);
        console.log('User role:', user.role);
        
        // Verify user is chef or higher
        const allowedRoles = ['chef', 'manager', 'admin'];
        if (!allowedRoles.includes(user.role)) {
            console.warn('User role not allowed for chef dashboard:', user.role);
            window.authManager.showToast('Access denied. Chef role required.', 'error');
            window.location.href = '/';
            return false;
        }
        
        // Verify token is still valid
        const isValid = await window.authManager.verifyToken();
        if (!isValid) {
            console.warn('Token invalid, trying to refresh...');
            if (await window.authManager.refreshToken()) {
                // Token refreshed, continue
                this.token = localStorage.getItem('access_token');
                this.user = user;
                console.log('Token refreshed successfully');
                return true;
            } else {
                console.warn('Token refresh failed, redirecting to login');
                window.authManager.showToast('Session expired. Please login again.', 'error');
                localStorage.clear();
                setTimeout(() => {
                    window.location.href = '/login/';
                }, 1000);
                return false;
            }
        }
        
        this.user = user;
        this.token = token;
        console.log('✅ Auth check passed for user:', user.username);
        return true;
        
    } catch (error) {
        console.error('Auth check failed:', error);
        window.authManager.showToast('Authentication error', 'error');
        localStorage.clear();
        window.location.href = '/login/';
        return false;
    }
}

async verifyToken() {
    try {
        const response = await fetch('/api/auth/verify-token/', {
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            }
        });
        return response.ok;
    } catch (error) {
        console.error('Token verification failed:', error);
        return false;
    }
}

    async loadKitchenOrders() {
        try {
            this.showLoading(true);
            
            const headers = {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            };
            
            const response = await fetch(`${this.apiBase}/orders/kitchen_orders/`, {
                headers: headers
            });
            
            if (response.status === 401 || response.status === 403) {
                console.error('Access denied or token expired');
                if (await this.refreshToken()) {
                // Retry with new token
                return this.loadKitchenOrders();
            } else {
                // Clear storage and redirect
                localStorage.clear();
                window.location.href = '/login/';
                return;
            }
            }
            
            if (!response.ok) {
                throw new Error(`Failed to load orders: ${response.status}`);
            }
            
            const orders = await response.json();
            this.processOrders(orders);
            
            this.updateLastUpdateTime();
            this.updateStats();
            
            this.showLoading(false);
            
        } catch (error) {
            console.error('Error loading kitchen orders:', error);
            this.showError('Failed to load orders. Please try again.');
            this.showLoading(false);
        }


        

        
    }


    async refreshToken() {
    try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) return false;
        
        const response = await fetch('/api/auth/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access);
            if (data.refresh) {
                localStorage.setItem('refresh_token', data.refresh);
            }
            return true;
        }
        return false;
    } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
    }
}


    processOrders(orders) {
        // Track previous counts for notification
        const previousCounts = {
            confirmed: this.currentOrders.confirmed.length,
            preparing: this.currentOrders.preparing.length,
            ready: this.currentOrders.ready.length
        };
        
        // Reset current orders
        this.currentOrders = {
            confirmed: [],
            preparing: [],
            ready: []
        };
        
        // Categorize orders
        orders.forEach(order => {
            switch(order.status) {
                case 'confirmed':
                    this.currentOrders.confirmed.push(order);
                    break;
                case 'preparing':
                    this.currentOrders.preparing.push(order);
                    break;
                case 'ready':
                    this.currentOrders.ready.push(order);
                    break;
            }
        });
        
        // Sort orders (oldest first)
        this.currentOrders.confirmed.sort((a, b) => new Date(a.placed_at) - new Date(b.placed_at));
        this.currentOrders.preparing.sort((a, b) => new Date(a.preparation_started_at || a.placed_at) - new Date(b.preparation_started_at || b.placed_at));
        this.currentOrders.ready.sort((a, b) => new Date(a.ready_at || a.placed_at) - new Date(b.ready_at || b.placed_at));
        
        // Render orders
        this.renderOrders();
        
        // Play notification sounds for new orders
        if (this.soundEnabled) {
            if (this.currentOrders.confirmed.length > previousCounts.confirmed) {
                this.playNewOrderSound();
            }
            if (this.currentOrders.ready.length > previousCounts.ready) {
                this.playOrderReadySound();
            }
        }
    }

    renderOrders() {
        this.renderConfirmedOrders();
        this.renderPreparingOrders();
        this.renderReadyOrders();
        
        // Update column counts
        this.updateColumnCounts();
    }

    renderConfirmedOrders() {
        const container = document.getElementById('confirmed-orders');
        if (!container) return;
        
        if (this.currentOrders.confirmed.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <i class="fas fa-check-circle text-3xl mb-3"></i>
                    <p>No confirmed orders</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.currentOrders.confirmed.map(order => this.createOrderCard(order, 'confirmed')).join('');
    }

    renderPreparingOrders() {
        const container = document.getElementById('preparing-orders');
        if (!container) return;
        
        if (this.currentOrders.preparing.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <i class="fas fa-fire text-3xl mb-3"></i>
                    <p>No orders preparing</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.currentOrders.preparing.map(order => this.createOrderCard(order, 'preparing')).join('');
    }

    renderReadyOrders() {
        const container = document.getElementById('ready-orders');
        if (!container) return;
        
        if (this.currentOrders.ready.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <i class="fas fa-concierge-bell text-3xl mb-3"></i>
                    <p>No orders ready</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.currentOrders.ready.map(order => this.createOrderCard(order, 'ready')).join('');
    }

    createOrderCard(order, status) {
        const isPriority = order.is_priority || false;
        const elapsedTime = this.calculateElapsedTime(order.placed_at);
        const waitingTime = status === 'ready' ? this.calculateElapsedTime(order.ready_at || order.placed_at) : null;
        
        let actionButton = '';
        let progressBar = '';
        let timerDisplay = '';
        
        switch(status) {
            case 'confirmed':
                actionButton = `
                    <button onclick="startPreparing(${order.id})" 
                            class="bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-1 rounded text-sm transition">
                        <i class="fas fa-play mr-1"></i>Start
                    </button>
                `;
                timerDisplay = `Est. time: <span class="timer">${order.preparation_time || '15:00'}</span>`;
                break;
                
            case 'preparing':
                progressBar = `
                    <div class="mt-2">
                        <div class="text-xs text-gray-400 mb-1">Progress:</div>
                        <div class="w-full h-2 bg-gray-600 rounded-full overflow-hidden">
                            <div class="h-full bg-green-500" style="width: ${this.calculateProgress(elapsedTime)}%"></div>
                        </div>
                    </div>
                `;
                actionButton = `
                    <button onclick="markAsReady(${order.id})" 
                            class="bg-green-500 hover:bg-green-600 text-white px-3 py-1 rounded text-sm transition">
                        <i class="fas fa-check mr-1"></i>Ready
                    </button>
                `;
                timerDisplay = `<div class="text-xs text-yellow-400 timer">${elapsedTime}</div>`;
                break;
                
            case 'ready':
                actionButton = `
                    <button onclick="notifyWaiter(${order.id})" 
                            class="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 rounded text-sm transition">
                        <i class="fas fa-bell mr-2"></i>Notify Waiter
                    </button>
                `;
                timerDisplay = `<div class="text-xs text-red-400 timer">Waiting: ${waitingTime}</div>`;
                break;
        }
        
        return `
            <div class="order-card bg-gray-700 rounded-lg p-4 ${isPriority ? 'priority-high' : 'priority-normal'} ${status === 'confirmed' && isPriority ? 'new-order' : ''}">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <div class="font-bold text-lg">Order #${order.order_number}</div>
                        <div class="text-gray-400">Table ${order.table_number}</div>
                        ${order.customer_name ? `<div class="text-sm text-gray-400">${order.customer_name}</div>` : ''}
                    </div>
                    <div class="text-right">
                        <div class="text-sm text-gray-400">${this.formatTime(order.placed_at)}</div>
                        ${isPriority ? `
                            <span class="inline-block mt-1 bg-red-500 text-red-900 text-xs px-2 py-1 rounded">
                                <i class="fas fa-bolt mr-1"></i>Priority
                            </span>
                        ` : ''}
                        ${timerDisplay}
                    </div>
                </div>
                
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Items:</div>
                    <div class="space-y-1">
                        ${order.items.map(item => `
                            <div class="flex justify-between text-sm">
                                <span>${item.quantity}x ${item.name}</span>
                                <span class="text-gray-400">${item.preparation_time || 15}min</span>
                            </div>
                            ${item.instructions ? `
                                <div class="text-xs text-yellow-400 italic ml-3">${item.instructions}</div>
                            ` : ''}
                        `).join('')}
                    </div>
                </div>
                
                ${progressBar}
                
                <div class="flex justify-between items-center mt-3">
                    <div class="text-sm text-gray-400">
                        ${status === 'confirmed' ? timerDisplay : ''}
                    </div>
                    ${actionButton}
                </div>
            </div>
        `;
    }

    async startPreparing(orderId) {
        try {
            const response = await fetch(`${this.apiBase}/orders/${orderId}/update_status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`,
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ status: 'preparing' })
            });
            
            if (response.ok) {
                await this.loadKitchenOrders();
                this.showToast('Order marked as preparing', 'success');
            } else {
                throw new Error('Failed to update order');
            }
        } catch (error) {
            console.error('Error starting preparation:', error);
            this.showError('Failed to start preparation');
        }
    }

    async markAsReady(orderId) {
        try {
            const response = await fetch(`${this.apiBase}/orders/${orderId}/update_status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`,
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ status: 'ready' })
            });
            
            if (response.ok) {
                if (this.soundEnabled) {
                    this.playOrderReadySound();
                }
                await this.loadKitchenOrders();
                this.showToast('Order marked as ready', 'success');
            } else {
                throw new Error('Failed to update order');
            }
        } catch (error) {
            console.error('Error marking as ready:', error);
            this.showError('Failed to mark as ready');
        }
    }

    async notifyWaiter(orderId) {
        try {
            // In a real system, this would send a notification to waiters
            this.showToast('Waiter notified about ready order', 'info');
        } catch (error) {
            console.error('Error notifying waiter:', error);
        }
    }

    async startAllPreparing() {
        const confirmStart = confirm('Start preparing all confirmed orders?');
        if (!confirmStart) return;
        
        for (const order of this.currentOrders.confirmed) {
            await this.startPreparing(order.id);
            // Small delay to avoid overwhelming the server
            await new Promise(resolve => setTimeout(resolve, 200));
        }
    }

    async markAllReady() {
        const confirmReady = confirm('Mark all preparing orders as ready?');
        if (!confirmReady) return;
        
        for (const order of this.currentOrders.preparing) {
            await this.markAsReady(order.id);
            await new Promise(resolve => setTimeout(resolve, 200));
        }
    }

    updateColumnCounts() {
        const elements = {
            'confirmed-count': this.currentOrders.confirmed.length,
            'pending-count': this.currentOrders.confirmed.length,
            'preparing-column-count': this.currentOrders.preparing.length,
            'preparing-count': this.currentOrders.preparing.length,
            'ready-column-count': this.currentOrders.ready.length,
            'ready-count': this.currentOrders.ready.length
        };
        
        Object.entries(elements).forEach(([id, count]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = count;
            }
        });
        
        // Update priority count
        const priorityCount = [...this.currentOrders.confirmed, ...this.currentOrders.preparing, ...this.currentOrders.ready]
            .filter(order => order.is_priority).length;
        const priorityElement = document.getElementById('priority-count');
        if (priorityElement) {
            priorityElement.textContent = priorityCount;
        }
    }

    updateStats() {
        // Calculate average preparation time
        if (this.currentOrders.preparing.length > 0) {
            const totalMinutes = this.currentOrders.preparing.reduce((sum, order) => {
                return sum + this.elapsedToMinutes(this.calculateElapsedTime(order.placed_at));
            }, 0);
            
            const averageMinutes = Math.round(totalMinutes / this.currentOrders.preparing.length);
            const averageElement = document.getElementById('average-time');
            if (averageElement) {
                averageElement.textContent = `${String(averageMinutes).padStart(2, '0')}:00`;
            }
            
            // Find longest preparation time
            const longestOrder = this.currentOrders.preparing.reduce((longest, order) => {
                const currentTime = this.elapsedToMinutes(this.calculateElapsedTime(order.placed_at));
                const longestTime = this.elapsedToMinutes(this.calculateElapsedTime(longest.placed_at));
                return currentTime > longestTime ? order : longest;
            }, this.currentOrders.preparing[0]);
            
            const longestMinutes = this.elapsedToMinutes(this.calculateElapsedTime(longestOrder.placed_at));
            const longestElement = document.getElementById('longest-time');
            if (longestElement) {
                longestElement.textContent = `${String(longestMinutes).padStart(2, '0')}:00`;
            }
        }
    }

    updateTime() {
        const now = new Date();
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = now.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
    }

    updateLastUpdateTime() {
        const now = new Date();
        this.lastUpdateTime = now;
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = now.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
    }

    startPolling() {
        this.pollingTimer = setInterval(() => {
            this.loadKitchenOrders();
        }, this.pollingInterval);
        
        console.log(`Polling started every ${this.pollingInterval/1000} seconds`);
    }

    stopPolling() {
        if (this.pollingTimer) {
            clearInterval(this.pollingTimer);
            console.log('Polling stopped');
        }
    }

    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        const btn = document.getElementById('sound-btn');
        if (btn) {
            if (this.soundEnabled) {
                btn.innerHTML = '<i class="fas fa-volume-up mr-2"></i>Sound On';
                btn.classList.remove('bg-gray-600');
                btn.classList.add('bg-gray-700');
            } else {
                btn.innerHTML = '<i class="fas fa-volume-mute mr-2"></i>Sound Off';
                btn.classList.remove('bg-gray-700');
                btn.classList.add('bg-gray-600');
            }
        }
    }

    playNewOrderSound() {
        if (this.newOrderSound) {
            this.newOrderSound.currentTime = 0;
            this.newOrderSound.play().catch(e => console.log('Audio play failed:', e));
        }
    }

    playOrderReadySound() {
        if (this.orderReadySound) {
            this.orderReadySound.currentTime = 0;
            this.orderReadySound.play().catch(e => console.log('Audio play failed:', e));
        }
    }

    // Utility methods
    formatTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    calculateElapsedTime(startTime) {
        if (!startTime) return '00:00';
        const start = new Date(startTime);
        const now = new Date();
        const diffMs = now - start;
        const diffMins = Math.floor(diffMs / 60000);
        const diffSecs = Math.floor((diffMs % 60000) / 1000);
        return `${String(diffMins).padStart(2, '0')}:${String(diffSecs).padStart(2, '0')}`;
    }

    elapsedToMinutes(elapsedTime) {
        const [mins, secs] = elapsedTime.split(':').map(Number);
        return mins;
    }

    calculateProgress(elapsedTime) {
        const mins = this.elapsedToMinutes(elapsedTime);
        // Assuming average preparation time is 30 minutes
        return Math.min(100, (mins / 30) * 100);
    }

    showLoading(show) {
        // Implement loading indicator if needed
        if (show) {
            document.body.classList.add('loading');
        } else {
            document.body.classList.remove('loading');
        }
    }

    showError(message) {
        console.error('Error:', message);
        // Show toast notification
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} mr-3"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Add to toast container
        const container = document.getElementById('toast-container') || this.createToastContainer();
        container.appendChild(toast);
        
        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadKitchenOrders());
        }

        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                if (window.logout) {
                    window.logout();
                } else if (window.authManager && window.authManager.logout) {
                    window.authManager.logout();
                } else {
                    // Fallback: clear storage and redirect
                    localStorage.clear();
                    sessionStorage.clear();
                    window.location.href = '/login/';
                }
            });
        }
        
        // Sound toggle button
        const soundBtn = document.getElementById('sound-btn');
        if (soundBtn) {
            soundBtn.addEventListener('click', () => this.toggleSound());
        }
        
        // Print button
        const printBtn = document.getElementById('print-btn');
        if (printBtn) {
            printBtn.addEventListener('click', () => window.print());
        }
        
        // Start All button
        const startAllBtn = document.getElementById('start-all-btn');
        if (startAllBtn) {
            startAllBtn.addEventListener('click', () => this.startAllPreparing());
        }
        
        // Ready All button
        const readyAllBtn = document.getElementById('ready-all-btn');
        if (readyAllBtn) {
            readyAllBtn.addEventListener('click', () => this.markAllReady());
        }
        
        // Clear all ready button
        const clearReadyBtn = document.getElementById('clear-ready-btn');
        if (clearReadyBtn) {
            clearReadyBtn.addEventListener('click', () => {
                // This would archive or clear ready orders in a real system
                this.showToast('Ready orders cleared from display', 'info');
            });
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.chefDashboard = new ChefDashboard();
});


// Make functions globally accessible
window.startPreparing = (orderId) => window.chefDashboard.startPreparing(orderId);
window.markAsReady = (orderId) => window.chefDashboard.markAsReady(orderId);
window.notifyWaiter = (orderId) => window.chefDashboard.notifyWaiter(orderId);