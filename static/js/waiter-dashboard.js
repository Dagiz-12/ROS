// static/js/waiter-dashboard.js
class WaiterDashboard {
    constructor() {
        this.apiBase = '/api/tables';
        this.pollingInterval = 20000; // 20 seconds
        this.pollTimer = null;
        this.init();
    }

    init() {
        this.checkAuth();
        this.loadData();
        this.setupEventListeners();
        this.startPolling();
    }

    checkAuth() {
        const token = localStorage.getItem('access_token');
        const role = localStorage.getItem('user_role');
        
        if (!token) {
            window.location.href = '/login/';
            return;
        }
        
        if (!['waiter', 'manager', 'admin'].includes(role)) {
            window.location.href = '/login/';
        }
    }

    getAuthHeaders() {
        return window.authManager.getAuthHeaders();
    }

    async loadData() {
        try {
            await Promise.all([
                this.loadTables(),
                this.loadPendingOrders(),
                this.loadActiveOrders(),
                this.loadReadyOrders()
            ]);
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showToast('Failed to load data. Please refresh.', 'error');
        }
    }

    async loadTables() {
        try {
            const response = await fetch(`${this.apiBase}/tables/?is_active=true`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                this.renderTables(data.results || data);
                document.getElementById('active-tables-count').textContent = 
                    (data.results || data).length || 0;
            } else if (response.status === 403) {
                // No permission for tables
                document.getElementById('active-tables-count').textContent = '0';
                document.getElementById('tables-grid').innerHTML = `
                    <div class="col-span-full text-center py-8 text-gray-500">
                        <i class="fas fa-lock text-3xl mb-3"></i>
                        <p>No permission to view tables</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading tables:', error);
        }
    }

    async loadPendingOrders() {
        try {
            const response = await fetch(`${this.apiBase}/orders/pending_confirmation/`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                this.renderPendingOrders(data.results || data);
                const count = (data.results || data).length || 0;
                document.getElementById('pending-qr-count').textContent = count;
                document.getElementById('qr-orders-badge').textContent = count;
            }
        } catch (error) {
            console.error('Error loading pending orders:', error);
        }
    }

    async loadActiveOrders() {
        try {
            const response = await fetch(`${this.apiBase}/orders/?status=confirmed,preparing`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                document.getElementById('active-orders-count').textContent = 
                    (data.results || data).length || 0;
            }
        } catch (error) {
            console.error('Error loading active orders:', error);
        }
    }

    async loadReadyOrders() {
        try {
            const response = await fetch(`${this.apiBase}/orders/?status=ready`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                document.getElementById('ready-orders-count').textContent = 
                    (data.results || data).length || 0;
            }
        } catch (error) {
            console.error('Error loading ready orders:', error);
        }
    }

    renderTables(tables) {
        const container = document.getElementById('tables-grid');
        if (!tables || tables.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-8 text-gray-500">
                    <i class="fas fa-table text-3xl mb-3"></i>
                    <p>No tables available</p>
                </div>
            `;
            return;
        }

        container.innerHTML = tables.map(table => `
            <a href="/waiter/new-order/${table.id}/" 
               class="block p-3 rounded-lg border-2 text-center transition hover:shadow-md ${this.getTableClasses(table.status)}">
                <div class="text-2xl font-bold mb-1">${table.table_number}</div>
                <div class="text-sm capitalize ${this.getTableTextColor(table.status)}">
                    ${table.status || 'available'}
                </div>
                <div class="text-xs text-gray-500 mt-1">${table.capacity || 4} seats</div>
            </a>
        `).join('');
    }

    getTableClasses(status) {
        switch(status) {
            case 'occupied': return 'border-red-300 bg-red-50 hover:bg-red-100';
            case 'reserved': return 'border-yellow-300 bg-yellow-50 hover:bg-yellow-100';
            case 'cleaning': return 'border-blue-300 bg-blue-50 hover:bg-blue-100';
            case 'available': return 'border-green-300 bg-green-50 hover:bg-green-100';
            default: return 'border-gray-300 bg-gray-50 hover:bg-gray-100';
        }
    }

    getTableTextColor(status) {
        switch(status) {
            case 'occupied': return 'text-red-600';
            case 'reserved': return 'text-yellow-600';
            case 'cleaning': return 'text-blue-600';
            case 'available': return 'text-green-600';
            default: return 'text-gray-600';
        }
    }

    renderPendingOrders(orders) {
        const container = document.getElementById('pending-orders-list');
        if (!orders || orders.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-check-circle text-3xl mb-3"></i>
                    <p>No pending QR orders</p>
                </div>
            `;
            return;
        }

        container.innerHTML = orders.slice(0, 5).map(order => `
            <div class="border rounded-lg p-3 hover:bg-gray-50 transition">
                <div class="flex justify-between items-start">
                    <div>
                        <div class="font-bold">Order #${order.order_number || order.id}</div>
                        <div class="text-sm text-gray-600">
                            Table ${order.table?.table_number || 'N/A'}
                        </div>
                    </div>
                    <span class="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full">
                        Pending
                    </span>
                </div>
                <div class="mt-2 text-sm">
                    ${order.items_count || 0} items
                </div>
                <div class="mt-3 flex space-x-2">
                    <button onclick="waiterDashboard.confirmOrder(${order.id})" 
                            class="flex-1 bg-green-600 text-white py-1 px-3 rounded text-sm hover:bg-green-700 transition">
                        Confirm
                    </button>
                    <button onclick="waiterDashboard.viewOrder(${order.id})" 
                            class="flex-1 border border-gray-300 py-1 px-3 rounded text-sm hover:bg-gray-50 transition">
                        View
                    </button>
                </div>
            </div>
        `).join('');
    }

    async confirmOrder(orderId) {
        if (!confirm('Confirm this order and send to kitchen?')) return;

        try {
            const response = await fetch(`${this.apiBase}/orders/${orderId}/update_status/`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({ status: 'confirmed' })
            });

            if (response.ok) {
                this.showToast('Order confirmed and sent to kitchen!', 'success');
                this.loadData();
            } else {
                this.showToast('Failed to confirm order', 'error');
            }
        } catch (error) {
            console.error('Error confirming order:', error);
            this.showToast('Error confirming order', 'error');
        }
    }

    viewOrder(orderId) {
        // Implement view order details
        alert(`View order ${orderId} - To be implemented`);
    }

    setupEventListeners() {
        // Auto-refresh when window gains focus
        window.addEventListener('focus', () => {
            this.loadData();
        });
    }

    startPolling() {
        this.pollTimer = setInterval(() => {
            this.loadData();
        }, this.pollingInterval);
    }

    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }

    showToast(message, type = 'info') {
        window.authManager.showToast(message, type);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.waiterDashboard = new WaiterDashboard();
});

// Clean up polling when page is hidden
document.addEventListener('visibilitychange', () => {
    if (window.waiterDashboard) {
        if (document.hidden) {
            window.waiterDashboard.stopPolling();
        } else {
            window.waiterDashboard.startPolling();
        }
    }
});