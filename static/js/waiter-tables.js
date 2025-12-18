// static/js/waiter-tables.js
class WaiterTables {
    constructor() {
        this.apiBase = '/api/tables';
        this.allTables = [];
        this.currentTable = null;
        this.pollingInterval = 30000; // 30 seconds
        this.pollTimer = null;
        this.init();
    }

    init() {
        this.checkAuth();
        this.loadTables();
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

    async loadTables() {
        try {
            this.showLoading();
            const response = await fetch(`${this.apiBase}/tables/?is_active=true`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                this.allTables = data.results || data;
                this.renderTables(this.allTables);
                this.updateStats(this.allTables);
            }
        } catch (error) {
            console.error('Error loading tables:', error);
            this.showError('Failed to load tables');
        } finally {
            this.hideLoading();
        }
    }

    renderTables(tables) {
        const container = document.getElementById('tables-container');
        if (!container) return;

        if (!tables || tables.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12 text-gray-500">
                    <i class="fas fa-table text-4xl mb-4"></i>
                    <p>No tables available</p>
                    <p class="text-sm mt-2">Contact manager to add tables</p>
                </div>
            `;
            return;
        }

        container.innerHTML = tables.map(table => `
            <div class="table-card bg-white rounded-lg shadow border-2 p-4 cursor-pointer transition hover:shadow-md ${this.getTableClasses(table.status)}"
                 onclick="waiterTables.showTableDetails(${table.id})">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <div class="text-3xl font-bold">${table.table_number}</div>
                        <div class="text-sm text-gray-600">${table.table_name || 'Table'}</div>
                    </div>
                    <span class="status-badge px-2 py-1 rounded-full text-xs font-medium capitalize ${this.getStatusBadgeClass(table.status)}">
                        ${table.status || 'available'}
                    </span>
                </div>
                
                <div class="space-y-2">
                    <div class="flex items-center text-sm">
                        <i class="fas fa-chair mr-2 text-gray-500"></i>
                        <span>Capacity: ${table.capacity || 4} seats</span>
                    </div>
                    
                    ${table.location_description ? `
                    <div class="flex items-center text-sm">
                        <i class="fas fa-map-marker-alt mr-2 text-gray-500"></i>
                        <span class="truncate">${table.location_description}</span>
                    </div>
                    ` : ''}
                </div>
                
                <div class="mt-4 pt-3 border-t">
                    <div class="flex space-x-2">
                        ${table.status === 'available' ? `
                        <button onclick="event.stopPropagation(); waiterTables.createOrder(${table.id})" 
                                class="flex-1 bg-green-600 text-white py-2 rounded text-sm hover:bg-green-700 transition">
                            <i class="fas fa-plus mr-1"></i>Order
                        </button>
                        ` : ''}
                        
                        ${table.status === 'occupied' ? `
                        <button onclick="event.stopPropagation(); waiterTables.viewOrders(${table.id})" 
                                class="flex-1 bg-blue-600 text-white py-2 rounded text-sm hover:bg-blue-700 transition">
                            <i class="fas fa-eye mr-1"></i>View
                        </button>
                        ` : ''}
                        
                        <button onclick="event.stopPropagation(); waiterTables.updateStatus(${table.id})" 
                                class="flex-1 border border-gray-300 py-2 rounded text-sm hover:bg-gray-50 transition">
                            <i class="fas fa-edit mr-1"></i>Status
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    getTableClasses(status) {
        switch(status) {
            case 'available': return 'border-green-300 bg-green-50';
            case 'occupied': return 'border-red-300 bg-red-50';
            case 'reserved': return 'border-yellow-300 bg-yellow-50';
            case 'cleaning': return 'border-blue-300 bg-blue-50';
            default: return 'border-gray-300 bg-gray-50';
        }
    }

    getStatusBadgeClass(status) {
        switch(status) {
            case 'available': return 'bg-green-100 text-green-800';
            case 'occupied': return 'bg-red-100 text-red-800';
            case 'reserved': return 'bg-yellow-100 text-yellow-800';
            case 'cleaning': return 'bg-blue-100 text-blue-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    }

    updateStats(tables) {
        const counts = {
            available: 0,
            occupied: 0,
            reserved: 0,
            cleaning: 0,
        };

        tables.forEach(table => {
            if (counts.hasOwnProperty(table.status)) {
                counts[table.status]++;
            }
        });

        document.getElementById('available-count').textContent = counts.available;
        document.getElementById('occupied-count').textContent = counts.occupied;
        document.getElementById('reserved-count').textContent = counts.reserved;
        document.getElementById('cleaning-count').textContent = counts.cleaning;
    }

    async showTableDetails(tableId) {
        const table = this.allTables.find(t => t.id === tableId);
        if (!table) return;

        const modal = document.getElementById('table-modal');
        const modalContent = modal.querySelector('.p-6');

        modalContent.innerHTML = `
            <div class="flex justify-between items-start mb-4">
                <h3 class="text-xl font-bold">Table ${table.table_number}</h3>
                <button onclick="waiterTables.closeModal()" class="text-gray-500 hover:text-gray-700">
                    <i class="fas fa-times text-xl"></i>
                </button>
            </div>
            
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Table Name</label>
                    <p class="text-lg">${table.table_name || 'No name'}</p>
                </div>
                
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
                        <span class="inline-block px-3 py-1 rounded-full text-sm font-medium ${this.getStatusBadgeClass(table.status)}">
                            ${table.status || 'available'}
                        </span>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Capacity</label>
                        <p class="text-lg">${table.capacity || 4} seats</p>
                    </div>
                </div>
                
                ${table.location_description ? `
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Location</label>
                    <p>${table.location_description}</p>
                </div>
                ` : ''}
                
                ${table.qr_code ? `
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">QR Code</label>
                    <div class="border rounded p-4 flex justify-center">
                        <img src="${table.qr_code}" alt="QR Code" class="w-32 h-32">
                    </div>
                </div>
                ` : ''}
                
                <div class="pt-4 border-t">
                    <h4 class="font-medium mb-2">Quick Actions</h4>
                    <div class="grid grid-cols-2 gap-2">
                        ${table.status === 'available' ? `
                        <button onclick="waiterTables.createOrder(${table.id})" 
                                class="bg-green-600 text-white py-2 rounded hover:bg-green-700 transition">
                            Create Order
                        </button>
                        ` : `
                        <button onclick="waiterTables.viewOrders(${table.id})" 
                                class="bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition">
                            View Orders
                        </button>
                        `}
                        
                        <button onclick="waiterTables.updateTableStatus(${table.id})" 
                                class="border border-gray-300 py-2 rounded hover:bg-gray-50 transition">
                            Change Status
                        </button>
                    </div>
                </div>
            </div>
        `;

        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }

    createOrder(tableId) {
        window.location.href = `/waiter/new-order/${tableId}/`;
    }

    viewOrders(tableId) {
        window.location.href = `/api/tables/orders/?table=${tableId}`;
    }

    async updateTableStatus(tableId) {
        const newStatus = prompt('Enter new status (available, occupied, reserved, cleaning):');
        if (!newStatus || !['available', 'occupied', 'reserved', 'cleaning'].includes(newStatus)) {
            window.authManager.showToast('Invalid status', 'error');
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/tables/${tableId}/update_status/`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({ status: newStatus })
            });

            if (response.ok) {
                window.authManager.showToast('Table status updated!', 'success');
                this.loadTables();
                this.closeModal();
            } else {
                window.authManager.showToast('Failed to update status', 'error');
            }
        } catch (error) {
            console.error('Error updating status:', error);
            window.authManager.showToast('Error updating status', 'error');
        }
    }

    closeModal() {
        document.getElementById('table-modal').classList.add('hidden');
        document.getElementById('table-modal').classList.remove('flex');
    }

    refreshTables() {
        this.loadTables();
    }

    printTableList() {
        window.print();
    }

    setupEventListeners() {
        // Filter tables
        document.getElementById('status-filter')?.addEventListener('change', () => this.filterTables());
        document.getElementById('capacity-filter')?.addEventListener('change', () => this.filterTables());
        
        // Auto-refresh on focus
        window.addEventListener('focus', () => {
            this.loadTables();
        });
    }

    filterTables() {
        const statusFilter = document.getElementById('status-filter').value;
        const capacityFilter = parseInt(document.getElementById('capacity-filter').value);

        let filtered = this.allTables;

        if (statusFilter !== 'all') {
            filtered = filtered.filter(table => table.status === statusFilter);
        }

        if (capacityFilter > 0) {
            filtered = filtered.filter(table => table.capacity >= capacityFilter);
        }

        this.renderTables(filtered);
    }

    showLoading() {
        const container = document.getElementById('tables-container');
        if (container) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <div class="w-12 h-12 border-4 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p class="text-gray-500">Loading tables...</p>
                </div>
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
            this.loadTables();
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
    window.waiterTables = new WaiterTables();
});

// Clean up polling when page is hidden
document.addEventListener('visibilitychange', () => {
    if (window.waiterTables) {
        if (document.hidden) {
            window.waiterTables.stopPolling();
        } else {
            window.waiterTables.startPolling();
        }
    }
});