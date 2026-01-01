// static/js/waiter-orders.js
class WaiterOrders {
    constructor() {
        this.apiBase = '/api/tables';
        this.allOrders = [];
        this.filteredOrders = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.pollingInterval = 20000; // 20 seconds
        this.pollTimer = null;
        this.init();
    }

    init() {
        this.checkAuth();
        this.loadOrders();
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

    async loadOrders() {
        try {
            this.showLoading();
            const response = await fetch(`${this.apiBase}/orders/`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                this.allOrders = data.results || data;
                this.filteredOrders = [...this.allOrders];
                this.updateStats(this.allOrders);
                this.renderOrdersTable();
            }
        } catch (error) {
            console.error('Error loading orders:', error);
            this.showError('Failed to load orders');
        } finally {
            this.hideLoading();
        }
    }

    updateStats(orders) {
        const today = new Date().toISOString().split('T')[0];
        const todayOrders = orders.filter(order => 
            order.placed_at && order.placed_at.startsWith(today)
        );

        const counts = {
            pending: 0,
            preparing: 0,
            ready: 0,
        };

        let todayRevenue = 0;

        todayOrders.forEach(order => {
            if (counts.hasOwnProperty(order.status)) {
                counts[order.status]++;
            }
            if (order.total_amount) {
                todayRevenue += parseFloat(order.total_amount);
            }
        });

        document.getElementById('pending-count').textContent = counts.pending;
        document.getElementById('preparing-count').textContent = counts.preparing;
        document.getElementById('ready-count').textContent = counts.ready;
        document.getElementById('revenue-count').textContent = `$${todayRevenue.toFixed(2)}`;
    }

    renderOrdersTable() {
        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
        const pageOrders = this.filteredOrders.slice(start, end);

        const tbody = document.getElementById('orders-body');
        if (!tbody) return;

        if (!pageOrders || pageOrders.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-12 text-center text-gray-500">
                        <i class="fas fa-clipboard-list text-4xl mb-4"></i>
                        <p>No orders found</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = pageOrders.map(order => `
            <tr class="hover:bg-gray-50 cursor-pointer transition" onclick="waiterOrders.showOrderDetails(${order.id})">
                <td class="px-4 py-3">
                    <div class="font-bold">${order.order_number || `#${order.id}`}</div>
                    <div class="text-xs text-gray-500">${order.order_type || 'waiter'}</div>
                </td>
                <td class="px-4 py-3">
                    <div class="font-medium">${order.table_number || 'N/A'}</div>
                    <div class="text-xs text-gray-500">${order.customer_name || 'Guest'}</div>
                </td>
                <td class="px-4 py-3">
                    <div class="text-sm">${order.items?.length || 0} items</div>
                    <div class="text-xs text-gray-500 truncate max-w-xs">
                        ${order.items?.slice(0, 2).map(item => `${item.quantity}x ${item.name || 'Item'}`).join(', ') || ''}
                    ${order.items?.length > 2 ? '...' : ''}
                    </div>
                </td>
                <td class="px-4 py-3 font-bold">
                    $${order.total_amount ? parseFloat(order.total_amount).toFixed(2) : '0.00'}
                </td>
                <td class="px-4 py-3">
                    <span class="inline-block px-2 py-1 rounded-full text-xs font-medium ${this.getStatusClass(order.status)}">
                        ${order.status || 'pending'}
                    </span>
                </td>
                <td class="px-4 py-3">
                    <div class="text-sm">${this.formatTime(order.placed_at)}</div>
                    <div class="text-xs text-gray-500">${this.formatDate(order.placed_at)}</div>
                </td>
                <td class="px-4 py-3">
                    <div class="flex space-x-2">
                        ${order.status === 'pending' ? `
                        <button onclick="event.stopPropagation(); waiterOrders.confirmOrder(${order.id})" 
                                class="text-green-600 hover:text-green-900 transition">
                            <i class="fas fa-check"></i>
                        </button>
                        ` : ''}
                        
                        ${order.status === 'ready' ? `
                        <button onclick="event.stopPropagation(); waiterOrders.serveOrder(${order.id})" 
                                class="text-blue-600 hover:text-blue-900 transition">
                            <i class="fas fa-concierge-bell"></i>
                        </button>
                        ` : ''}
                        
                        <button onclick="event.stopPropagation(); waiterOrders.printOrder(${order.id})" 
                                class="text-gray-600 hover:text-gray-900 transition">
                            <i class="fas fa-print"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // Update pagination info
        document.getElementById('start-index').textContent = start + 1;
        document.getElementById('end-index').textContent = Math.min(end, this.filteredOrders.length);
        document.getElementById('total-orders').textContent = this.filteredOrders.length;

        // Update pagination buttons
        document.getElementById('prev-btn').disabled = this.currentPage === 1;
        document.getElementById('next-btn').disabled = end >= this.filteredOrders.length;
    }

    getStatusClass(status) {
        const classes = {
            pending: 'bg-yellow-100 text-yellow-800',
            confirmed: 'bg-blue-100 text-blue-800',
            preparing: 'bg-purple-100 text-purple-800',
            ready: 'bg-green-100 text-green-800',
            served: 'bg-indigo-100 text-indigo-800',
            completed: 'bg-gray-100 text-gray-800',
            cancelled: 'bg-red-100 text-red-800',
        };
        return classes[status] || 'bg-gray-100 text-gray-800';
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString();
    }

    formatTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    async showOrderDetails(orderId) {
        try {
            const response = await fetch(`${this.apiBase}/orders/${orderId}/`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) return;
            
            const order = await response.json();
            const modal = document.getElementById('order-modal');
            const modalContent = modal.querySelector('.p-6');
            
            modalContent.innerHTML = `
                <div class="flex justify-between items-start mb-6">
                    <div>
                        <h3 class="text-2xl font-bold">Order ${order.order_number}</h3>
                        <p class="text-gray-600">Table ${order.table_number || 'N/A'} • ${order.customer_name || 'Guest'}</p>
                    </div>
                    <button onclick="waiterOrders.closeOrderModal()" class="text-gray-500 hover:text-gray-700">
                        <i class="fas fa-times text-2xl"></i>
                    </button>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                    <div class="md:col-span-2">
                        <div class="bg-gray-50 rounded-lg p-4">
                            <h4 class="font-bold mb-3">Order Items</h4>
                            <div class="space-y-3">
                                ${order.items?.map(item => `
                                <div class="flex justify-between items-center p-2 bg-white rounded">
                                    <div>
                                        <div class="font-medium">${item.quantity}x ${item.name || 'Unknown Item'}</div>
                                        ${item.special_instructions ? `
                                        <div class="text-sm text-gray-600 italic">${item.special_instructions}</div>
                                        ` : ''}
                                    </div>
                                    <div class="font-bold">$${(item.quantity * (item.unit_price || 0)).toFixed(2)}</div>
                                </div>
                                `).join('') || '<p class="text-gray-500">No items</p>'}
                            </div>
                        </div>
                    </div>
                    
                    <div>
                        <div class="bg-gray-50 rounded-lg p-4">
                            <h4 class="font-bold mb-3">Order Summary</h4>
                            <div class="space-y-2">
                                <div class="flex justify-between">
                                    <span>Subtotal</span>
                                    <span>$${order.subtotal || '0.00'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>Tax</span>
                                    <span>$${order.tax_amount || '0.00'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>Service</span>
                                    <span>$${order.service_charge || '0.00'}</span>
                                </div>
                                <div class="border-t pt-2 mt-2">
                                    <div class="flex justify-between font-bold text-lg">
                                        <span>Total</span>
                                        <span>$${order.total_amount || '0.00'}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="mt-4 pt-4 border-t">
                                <div class="space-y-2">
                                    <div>
                                        <label class="block text-sm text-gray-600">Status</label>
                                        <span class="inline-block mt-1 ${this.getStatusClass(order.status)} px-3 py-1 rounded-full">
                                            ${order.status}
                                        </span>
                                    </div>
                                    <div>
                                        <label class="block text-sm text-gray-600">Order Type</label>
                                        <span class="font-medium">${order.order_type}</span>
                                    </div>
                                    <div>
                                        <label class="block text-sm text-gray-600">Placed At</label>
                                        <span>${this.formatDate(order.placed_at)} ${this.formatTime(order.placed_at)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="flex space-x-3">
                    ${order.status === 'pending' ? `
                    <button onclick="waiterOrders.confirmOrder(${order.id})" 
                            class="flex-1 bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 transition">
                        <i class="fas fa-check mr-2"></i>Confirm Order
                    </button>
                    ` : ''}
                    
                    ${order.status === 'ready' ? `
                    <button onclick="waiterOrders.serveOrder(${order.id})" 
                            class="flex-1 bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition">
                        <i class="fas fa-concierge-bell mr-2"></i>Mark as Served
                    </button>
                    ` : ''}
                    
                    <button onclick="waiterOrders.printOrder(${order.id})" 
                            class="flex-1 border border-gray-300 py-3 rounded-lg hover:bg-gray-50 transition">
                        <i class="fas fa-print mr-2"></i>Print Receipt
                    </button>
                </div>
            `;
            
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        } catch (error) {
            console.error('Error loading order details:', error);
        }
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
                window.authManager.showToast('Order confirmed!', 'success');
                this.loadOrders();
                this.closeOrderModal();
            } else {
                window.authManager.showToast('Failed to confirm order', 'error');
            }
        } catch (error) {
            console.error('Error confirming order:', error);
            window.authManager.showToast('Error confirming order', 'error');
        }
    }

    async serveOrder(orderId) {
        if (!confirm('Mark this order as served?')) return;

        try {
            const response = await fetch(`${this.apiBase}/orders/${orderId}/update_status/`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({ status: 'served' })
            });

            if (response.ok) {
                window.authManager.showToast('Order marked as served!', 'success');
                this.loadOrders();
                this.closeOrderModal();
            } else {
                window.authManager.showToast('Failed to update order', 'error');
            }
        } catch (error) {
            console.error('Error serving order:', error);
            window.authManager.showToast('Error updating order', 'error');
        }
    }

    
    printOrder(orderId) {
        window.open(`${this.apiBase}/orders/${orderId}/print/`, '_blank');
    }

    closeOrderModal() {
        document.getElementById('order-modal').classList.add('hidden');
        document.getElementById('order-modal').classList.remove('flex');
    }

    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderOrdersTable();
        }
    }

    nextPage() {
        if (this.currentPage * this.pageSize < this.filteredOrders.length) {
            this.currentPage++;
            this.renderOrdersTable();
        }
    }

    printOrders() {
        window.print();
    }

    exportOrders() {
        // Simple CSV export
        const headers = ['Order #', 'Table', 'Customer', 'Items', 'Total', 'Status', 'Date'];
        const csvData = this.filteredOrders.map(order => [
            order.order_number || `#${order.id}`,
            order.table_number || 'N/A',
            order.customer_name || 'Guest',
            order.items_count || 0,
            `$${order.total_amount || '0.00'}`,
            order.status,
            this.formatDate(order.placed_at)
        ]);
        
        const csv = [headers, ...csvData].map(row => row.join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `orders_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    setupEventListeners() {
        // Filter and search
        document.getElementById('search-orders')?.addEventListener('input', () => this.filterOrders());
        document.getElementById('status-filter')?.addEventListener('change', () => this.filterOrders());
        document.getElementById('time-filter')?.addEventListener('change', () => this.filterOrders());
        
        // Auto-refresh on focus
        window.addEventListener('focus', () => {
            this.loadOrders();
        });
    }

    filterOrders() {
        const searchTerm = (document.getElementById('search-orders')?.value || '').toLowerCase().trim();
        const statusFilter = document.getElementById('status-filter')?.value || 'all';
        const timeFilter = document.getElementById('time-filter')?.value || 'today';

        let filtered = [...this.allOrders];

        // Status filter (fastest, do first)
        if (statusFilter !== 'all') {
            filtered = filtered.filter(order => order.status === statusFilter);
        }

        // Time filter
        if (timeFilter !== 'all') {
            const now = new Date();
            let cutoffDate = new Date();

            switch (timeFilter) {
                case 'today':
                    cutoffDate.setHours(0, 0, 0, 0);
                    break;
                case 'yesterday':
                    cutoffDate.setDate(now.getDate() - 1);
                    cutoffDate.setHours(0, 0, 0, 0);
                    break;
                case 'week':
                    cutoffDate.setDate(now.getDate() - 7);
                    break;
                case 'month':
                    cutoffDate.setMonth(now.getMonth() - 1);
                    break;
            }

            filtered = filtered.filter(order => {
                if (!order.placed_at) return false;
                const orderDate = new Date(order.placed_at);
                return orderDate >= cutoffDate;
            });
        }

        // Search filter (most complex, do last)
        if (searchTerm) {
            filtered = filtered.filter(order => {
                // Search in order number
                if (order.order_number && order.order_number.toLowerCase().includes(searchTerm)) {
                    return true;
                }

                // Search in customer name
                if (order.customer_name && order.customer_name.toLowerCase().includes(searchTerm)) {
                    return true;
                }

                // Search in table number
                if (order.table_number && order.table_number.toString().includes(searchTerm)) {
                    return true;
                }

                // Search in table name
                if (order.table_name && order.table_name.toLowerCase().includes(searchTerm)) {
                    return true;
                }

                // Search in item names
                if (order.items && order.items.some(item => 
                    item.name && item.name.toLowerCase().includes(searchTerm)
                )) {
                    return true;
                }

                // Search in special instructions
                if (order.items && order.items.some(item => 
                    item.special_instructions && item.special_instructions.toLowerCase().includes(searchTerm)
                )) {
                    return true;
                }

                return false;
            });
        }

        this.filteredOrders = filtered;
        this.currentPage = 1;
        this.renderOrdersTable();
        
        // Update search result count
        let resultCountEl = document.getElementById('search-result-count');
        if (!resultCountEl) {
            resultCountEl = document.createElement('div');
            resultCountEl.id = 'search-result-count';
            resultCountEl.className = 'text-sm text-gray-600 mt-2';
            const searchContainer = document.getElementById('search-orders')?.parentElement;
            if (searchContainer) {
                searchContainer.appendChild(resultCountEl);
            }
        }
        
        if (searchTerm) {
            resultCountEl.textContent = `Found ${filtered.length} orders matching "${searchTerm}"`;
            resultCountEl.classList.remove('hidden');
        } else {
            resultCountEl.classList.add('hidden');
        }
    }

    showLoading() {
        const tbody = document.getElementById('orders-body');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-12 text-center text-gray-500">
                        <div class="w-12 h-12 border-4 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                        <p>Loading orders...</p>
                    </td>
                </tr>
            `;
        }
    }

    hideLoading() {
        // Could hide loading indicator if needed
    }

    showError(message) {
        window.authManager.showToast(message, 'error');
    }

    startPolling() {
        this.pollTimer = setInterval(() => {
            this.loadOrders();
        }, this.pollingInterval);
    }

    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.waiterOrders = new WaiterOrders();
});

// Clean up polling when page is hidden
document.addEventListener('visibilitychange', () => {
    if (window.waiterOrders) {
        if (document.hidden) {
            window.waiterOrders.stopPolling();
        } else {
            window.waiterOrders.startPolling();
        }
    }
});