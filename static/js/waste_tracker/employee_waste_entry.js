// static/js/waste_tracker/employee-waste-entry.js
class WasteEntryManager {
    constructor(config = {}) {
        this.csrfToken = config.csrfToken || '';
        this.userData = config.userData || {};
        this.stockItems = [];
        this.wasteReasons = [];
        this.selectedItem = null;
        this.currentQuantity = 1;
        this.userRole = config.userData.role;
        this.initNavigation();
        
        this.apiEndpoints = {
            stockItems: '/api/inventory/stock-items/',
            wasteReasons: '/waste/api/reasons/',
            quickEntry: '/waste/api/quick-entry/',
            myWasteRecords: '/waste/api/records/my_records/'
        };
        
        this.init();
    }

    init() {
        this.checkAuth();
        this.bindEvents();
        this.loadData();
    }

    checkAuth() {
        // Check if user is authenticated
        if (typeof authManager !== 'undefined' && !authManager.isAuthenticated()) {
            this.redirectToLogin();
            return false;
        }
        return true;
    }

    // new method to initialize navigation based on user role
    initNavigation() {
        // Back to dashboard button click handler
        const backButton = document.querySelector('[href*="/waiter/dashboard/"], [href*="/chef/dashboard/"], [href*="/cashier/dashboard/"]');
        if (backButton) {
            backButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.goToDashboard();
            });
        }
        
        // Or if you're handling it dynamically:
        const dynamicBackButton = document.querySelector('a[href="#back-to-dashboard"]');
        if (dynamicBackButton) {
            dynamicBackButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.goToDashboard();
            });
        }
    }
    
    goToDashboard() {
        let dashboardUrl = '/';
        
        switch(this.userRole) {
            case 'chef':
                dashboardUrl = '/chef/dashboard/';
                break;
            case 'waiter':
                dashboardUrl = '/waiter/dashboard/';
                break;
            case 'cashier':
                dashboardUrl = '/cashier/dashboard/';
                break;
            case 'manager':
                dashboardUrl = '/restaurant-admin/dashboard/';
                break;
            case 'admin':
                dashboardUrl = '/admin/';
                break;
            default:
                dashboardUrl = '/login/';
        }
        
        window.location.href = dashboardUrl;
    }

    bindEvents() {
        // Logout button
        document.getElementById('logout-btn')?.addEventListener('click', () => this.logout());
        
        // Selection buttons
        document.getElementById('clear-selection-btn')?.addEventListener('click', () => this.clearSelection());
        
        // Quantity buttons
        document.getElementById('increase-qty-btn')?.addEventListener('click', () => this.increaseQuantity());
        document.getElementById('decrease-qty-btn')?.addEventListener('click', () => this.decreaseQuantity());
        
        // Quantity input
        document.getElementById('quantity')?.addEventListener('input', (e) => {
            this.currentQuantity = parseFloat(e.target.value) || 1;
            this.updateCostCalculation();
        });
        
        // Submit button
        document.getElementById('submit-waste-btn')?.addEventListener('click', () => this.submitWaste());
        
        // Search input
        document.getElementById('search-items')?.addEventListener('input', (e) => {
            this.filterItems(e.target.value);
        });
        
        // Waste reason change
        document.getElementById('waste-reason')?.addEventListener('change', (e) => {
            this.validateForm();
        });
    }

    async loadData() {
        try {
            this.showLoading('Loading inventory...');
            
            // Load stock items and waste reasons in parallel
            await Promise.all([
                this.loadStockItems(),
                this.loadWasteReasons()
            ]);
            
            this.hideLoading();
            this.loadTodaySummary();
            
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Failed to load data. Please refresh the page.');
            this.hideLoading();
        }
    }

    async loadStockItems() {
    try {
        const url = `${this.apiEndpoints.stockItems}?is_active=true&branch_id=${this.userData.branch_id || ''}`;
        const response = await this.apiRequest('GET', url);
        
        console.log('Stock items response:', response);  // Debug log
        
        // Handle paginated response (DRF default)
        if (response && typeof response === 'object') {
            if (response.results !== undefined) {
                // Paginated response
                this.stockItems = response.results;
                this.renderItemsGrid();
            } else if (Array.isArray(response)) {
                // Direct array response
                this.stockItems = response;
                this.renderItemsGrid();
            } else {
                console.error('Unexpected response format:', response);
                throw new Error('Invalid response format');
            }
        } else {
            console.error('Response is not an object:', response);
            throw new Error('Invalid response format');
        }
    } catch (error) {
        console.error('Error loading stock items:', error);
        this.showError('Failed to load inventory items. Please contact your manager.');
    }
}
    async loadWasteReasons() {
    try {
        const response = await this.apiRequest('GET', this.apiEndpoints.wasteReasons);
        
        console.log('Waste reasons response:', response);  // Debug log
        
        // Handle paginated response
        if (response && typeof response === 'object') {
            if (response.results !== undefined) {
                this.wasteReasons = response.results;
                this.populateWasteReasons();
            } else if (Array.isArray(response)) {
                this.wasteReasons = response;
                this.populateWasteReasons();
            }
        }
    } catch (error) {
        console.error('Error loading waste reasons:', error);
        // Don't show error - waste reasons are optional for display
    }
}

    async loadTodaySummary() {
    try {
        // Load user's waste records for today
        const today = new Date().toISOString().split('T')[0];
        const url = `${this.apiEndpoints.myWasteRecords}?start_date=${today}`;
        const response = await this.apiRequest('GET', url);
        
        console.log('Today summary response:', response);  // Debug log
        
        // Handle paginated response
        if (response && typeof response === 'object') {
            if (response.results !== undefined) {
                this.updateSummary(response.results);
            } else if (Array.isArray(response)) {
                this.updateSummary(response);
            }
        }
    } catch (error) {
        console.error('Error loading summary:', error);
    }
}

    renderItemsGrid() {
        const container = document.getElementById('items-grid');
        if (!container) return;

        if (!this.stockItems || this.stockItems.length === 0) {
            container.innerHTML = `
                <div class="col-span-3 text-center py-8 text-gray-500">
                    <i class="fas fa-box-open text-3xl mb-3"></i>
                    <p>No items found in inventory</p>
                    <p class="text-sm mt-1">Contact your manager to add inventory items</p>
                </div>
            `;
            return;
        }

        const itemsHtml = this.stockItems.map(item => `
            <div class="waste-item-card bg-white border border-gray-200 rounded-lg p-3 cursor-pointer hover:border-red-300 transition-colors"
                 data-item-id="${item.id}"
                 onclick="window.wasteEntryManager.selectItem(${item.id})">
                <div class="flex items-center mb-2">
                    <div class="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center mr-3">
                        <i class="fas fa-${this.getItemIcon(item.category)} text-gray-500"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="font-medium text-gray-900 truncate" title="${item.name}">${item.name}</div>
                        <div class="text-xs text-gray-500">${this.formatCategory(item.category)}</div>
                    </div>
                </div>
                <div class="flex justify-between text-sm">
                    <span class="text-gray-600">Stock:</span>
                    <span class="font-medium ${item.current_quantity <= item.minimum_quantity ? 'text-red-600' : 'text-green-600'}">
                        ${this.formatQuantity(item.current_quantity)} ${item.unit}
                    </span>
                </div>
                <div class="flex justify-between text-sm mt-1">
                    <span class="text-gray-600">Cost:</span>
                    <span class="font-medium">${this.formatCurrency(item.cost_per_unit)}/${item.unit}</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = itemsHtml;
    }

    populateWasteReasons() {
        const select = document.getElementById('waste-reason');
        if (!select || !this.wasteReasons || this.wasteReasons.length === 0) {
            select.innerHTML = '<option value="">No reasons available</option>';
            return;
        }

        // Clear existing options
        select.innerHTML = '<option value="">Select a reason...</option>';
        
        // Group by category
        const reasonsByCategory = {};
        this.wasteReasons.forEach(reason => {
            const categoryName = reason.category?.name || 'General';
            if (!reasonsByCategory[categoryName]) {
                reasonsByCategory[categoryName] = [];
            }
            reasonsByCategory[categoryName].push(reason);
        });

        // Add grouped options
        Object.entries(reasonsByCategory).forEach(([category, reasons]) => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = category;
            
            reasons.forEach(reason => {
                const option = document.createElement('option');
                option.value = reason.id;
                option.textContent = reason.name;
                if (reason.description) {
                    option.title = reason.description;
                }
                optgroup.appendChild(option);
            });
            
            select.appendChild(optgroup);
        });
    }

    selectItem(itemId) {
        this.selectedItem = this.stockItems.find(item => item.id == itemId);
        if (!this.selectedItem) return;

        // Update UI
        document.getElementById('selected-name').textContent = this.selectedItem.name;
        document.getElementById('item-unit').textContent = this.selectedItem.unit;
        document.getElementById('available-stock').textContent = this.formatQuantity(this.selectedItem.current_quantity);
        document.getElementById('available-unit').textContent = this.selectedItem.unit;
        document.getElementById('unit-cost').textContent = this.formatCurrency(this.selectedItem.cost_per_unit);

        // Reset quantity to 1
        this.currentQuantity = 1;
        document.getElementById('quantity').value = this.currentQuantity;
        this.updateCostCalculation();

        // Show selected section, hide empty state
        document.getElementById('selected-section').classList.remove('hidden');
        document.getElementById('empty-state').classList.add('hidden');

        // Highlight selected item
        this.highlightSelectedItem(itemId);
        
        // Validate form
        this.validateForm();
    }

    clearSelection() {
        this.selectedItem = null;
        document.getElementById('selected-section').classList.add('hidden');
        document.getElementById('empty-state').classList.remove('hidden');
        this.clearItemSelection();
        this.validateForm();
    }

    increaseQuantity() {
        this.currentQuantity += 1;
        document.getElementById('quantity').value = this.currentQuantity;
        this.updateCostCalculation();
        this.validateForm();
    }

    decreaseQuantity() {
        if (this.currentQuantity > 0.001) {
            this.currentQuantity = Math.max(0.001, this.currentQuantity - 1);
            document.getElementById('quantity').value = this.currentQuantity;
            this.updateCostCalculation();
            this.validateForm();
        }
    }

    updateCostCalculation() {
        if (!this.selectedItem) return;
        
        const unitCost = parseFloat(this.selectedItem.cost_per_unit);
        const totalCost = this.currentQuantity * unitCost;
        
        document.getElementById('total-cost').textContent = 
            this.formatCurrency(totalCost);
    }

    // In employee_waste_entry.js - Update the submitWaste method

async submitWaste() {
    if (!this.validateForm(true)) return;

    const wasteData = {
        stock_item_id: this.selectedItem.id,
        quantity: this.currentQuantity,
        waste_reason_id: document.getElementById('waste-reason').value,
        notes: document.getElementById('notes').value.trim(),
        station: 'kitchen',
        shift: this.getCurrentShift(),
        waste_source: 'Kitchen waste'
    };

    // Remove empty fields
    Object.keys(wasteData).forEach(key => {
        if (wasteData[key] === '' || wasteData[key] === null || wasteData[key] === undefined) {
            delete wasteData[key];
        }
    });

    try {
        this.showLoading('Recording waste...');
        
        const response = await this.apiRequest('POST', this.apiEndpoints.quickEntry, wasteData);
        
        if (response && response.success) {
            this.showSuccess('Waste recorded successfully!');
            this.clearSelection();
            
            // Clear form
            document.getElementById('waste-reason').value = '';
            document.getElementById('notes').value = '';
            
            // Reload data to update stock levels
            await this.loadStockItems();
            await this.loadTodaySummary();
            
        } else {
            throw new Error(response?.error || 'Failed to record waste');
        }
    } catch (error) {
        console.error('Error submitting waste:', error);
        this.showError(error.message || 'Failed to record waste. Please try again.');
    } finally {
        this.hideLoading();
    }
}

    filterItems(searchTerm) {
        const items = document.querySelectorAll('.waste-item-card');
        const term = searchTerm.toLowerCase().trim();
        
        items.forEach(item => {
            const itemName = item.querySelector('.font-medium').textContent.toLowerCase();
            const itemCategory = item.querySelector('.text-xs').textContent.toLowerCase();
            
            if (!term || itemName.includes(term) || itemCategory.includes(term)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }

    validateForm(showErrors = false) {
        const submitBtn = document.getElementById('submit-waste-btn');
        if (!submitBtn) return false;

        let isValid = true;
        let errorMessage = '';

        if (!this.selectedItem) {
            isValid = false;
            errorMessage = 'Please select an item';
        } else if (!document.getElementById('waste-reason').value) {
            isValid = false;
            errorMessage = 'Please select a waste reason';
        } else if (this.currentQuantity <= 0) {
            isValid = false;
            errorMessage = 'Quantity must be greater than 0';
        } else if (this.selectedItem && this.currentQuantity > this.selectedItem.current_quantity) {
            isValid = false;
            errorMessage = `Cannot waste more than available stock (${this.formatQuantity(this.selectedItem.current_quantity)} ${this.selectedItem.unit})`;
        }

        submitBtn.disabled = !isValid;
        
        if (showErrors && !isValid && errorMessage) {
            this.showError(errorMessage);
        }

        return isValid;
    }

    // Utility Methods
    highlightSelectedItem(itemId) {
        document.querySelectorAll('.waste-item-card').forEach(card => {
            card.classList.remove('selected-item');
            if (card.dataset.itemId == itemId) {
                card.classList.add('selected-item');
            }
        });
    }

    clearItemSelection() {
        document.querySelectorAll('.waste-item-card').forEach(card => {
            card.classList.remove('selected-item');
        });
    }

    updateSummary(wasteRecords) {
        let totalCost = 0;
        
        if (wasteRecords && Array.isArray(wasteRecords)) {
            wasteRecords.forEach(record => {
                if (record.total_cost) {
                    totalCost += parseFloat(record.total_cost);
                }
            });
        }
        
        document.getElementById('today-waste').textContent = this.formatCurrency(totalCost);
        document.getElementById('my-records').textContent = wasteRecords?.length || 0;
    }

    getItemIcon(category) {
        const icons = {
            'meat': 'drumstick-bite',
            'seafood': 'fish',
            'vegetable': 'carrot',
            'fruit': 'apple-alt',
            'dairy': 'cheese',
            'beverage': 'wine-bottle',
            'cleaning': 'spray-can',
            'spices': 'mortar-pestle',
            'dry_goods': 'wheat-awn'
        };
        return icons[category?.toLowerCase()] || 'box';
    }

    formatCategory(category) {
        const categories = {
            'meat': 'Meat & Poultry',
            'seafood': 'Seafood',
            'vegetable': 'Vegetables',
            'fruit': 'Fruits',
            'dairy': 'Dairy',
            'beverage': 'Beverages',
            'cleaning': 'Cleaning',
            'spices': 'Spices & Herbs',
            'dry_goods': 'Dry Goods',
            'other': 'Other'
        };
        return categories[category?.toLowerCase()] || category || 'General';
    }

    formatQuantity(quantity) {
        if (!quantity && quantity !== 0) return '0';
        
        const num = parseFloat(quantity);
        if (num % 1 === 0) {
            return num.toString();
        } else {
            return num.toFixed(3).replace(/\.?0+$/, '');
        }
    }

    formatCurrency(amount) {
        if (!amount && amount !== 0) return '$0.00';
        
        const num = parseFloat(amount);
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(num);
    }

    getCurrentShift() {
        const hour = new Date().getHours();
        if (hour < 12) return 'morning';
        if (hour < 17) return 'afternoon';
        return 'evening';
    }

    // API Helper
    async apiRequest(method, url, data = null) {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Add CSRF token for non-GET requests
        if (method !== 'GET' && this.csrfToken) {
            headers['X-CSRFToken'] = this.csrfToken;
        }
        
        // Add JWT token if available
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const options = {
            method: method,
            headers: headers,
            credentials: 'include'
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            
            // Handle 401 Unauthorized
            if (response.status === 401) {
                this.redirectToLogin();
                return null;
            }
            
            // Handle 403 Forbidden
            if (response.status === 403) {
                throw new Error('You do not have permission to perform this action');
            }
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || `HTTP ${response.status}`);
            }
            
            return result;
        } catch (error) {
            console.error(`API Error (${method} ${url}):`, error);
            throw error;
        }
    }

    // UI Helper Methods
    showLoading(message = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        const messageEl = document.getElementById('loading-message');
        
        if (overlay) {
            if (messageEl) messageEl.textContent = message;
            overlay.classList.remove('hidden');
            overlay.style.display = 'flex';
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
            overlay.style.display = 'none';
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `px-4 py-3 rounded-lg shadow-lg text-white toast-enter ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 'bg-blue-500'
        }`;
        toast.textContent = message;

        // Add close button for errors
        if (type === 'error') {
            const closeBtn = document.createElement('button');
            closeBtn.className = 'ml-3 text-white hover:text-gray-200';
            closeBtn.innerHTML = '<i class="fas fa-times"></i>';
            closeBtn.onclick = () => toast.remove();
            toast.appendChild(closeBtn);
        }

        container.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.classList.add('toast-exit');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    redirectToLogin() {
        window.location.href = '/login/';
    }

    logout() {
        if (typeof authManager !== 'undefined') {
            authManager.logout();
        } else {
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_data');
            this.redirectToLogin();
        }
    }
}

// Make it globally accessible
window.WasteEntryManager = WasteEntryManager;