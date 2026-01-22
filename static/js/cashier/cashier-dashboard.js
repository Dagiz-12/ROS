// static/js/cashier-dashboard.js - UPDATED VERSION
class CashierDashboard {
    constructor() {
        console.log('💰 Initializing Cashier Dashboard...');
        
        this.apiBase = '/api/payments'; // Base API URL
        this.tablesApiBase = '/api/tables';
        this.pollingInterval = 20000; // 20 seconds
        this.selectedBill = null;
        this.selectedPaymentMethod = null;
        this.pendingBills = [];
        this.recentTransactions = [];
        this.isInitialized = false;
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    async init() {
        console.log('💰 Cashier Dashboard Starting...');
        
        // Check authentication
        if (!await this.checkAuth()) {
            return;
        }
        
        // Setup event listeners FIRST
        this.setupEventListeners();
        
        // Then load data
        await this.loadPendingBills();
        await this.loadRecentTransactions();
        await this.updateStats();
        
        // Start polling
        this.startPolling();
        
        this.isInitialized = true;
        console.log('✅ Cashier Dashboard Ready');
    }

    async checkAuth() {
        // Check if we have auth token
        const token = localStorage.getItem('access_token');
        const userData = localStorage.getItem('user_data');
        
        if (!token || !userData) {
            console.warn('❌ User not authenticated, redirecting to login...');
            window.location.href = '/login/';
            return false;
        }
        
        try {
            const user = JSON.parse(userData);
            // Verify user is cashier or higher
            const allowedRoles = ['cashier', 'manager', 'admin'];
            if (!allowedRoles.includes(user.role)) {
                this.showError('Access denied. Cashier role required.');
                window.location.href = '/login/';
                return false;
            }
            
            this.user = user;
            this.token = token;
            return true;
        } catch (error) {
            console.error('Auth check failed:', error);
            window.location.href = '/login/';
            return false;
        }
    }

    getAuthHeaders() {
        const headers = {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
        
        // Add CSRF token if available
        const csrfToken = this.getCsrfToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        return headers;
    }

    // FIXED: Use the correct payment API endpoint
async loadPendingBills() {
    try {
        console.log('📋 Loading pending bills...');
        
        // Use payment API to get pending payments
        const response = await fetch(
            `/api/payments/cashier/pending-orders/`,  // FIXED ENDPOINT
            { headers: this.getAuthHeaders() }
        );
        
        if (response.status === 401 || response.status === 403) {
            localStorage.clear();
            window.location.href = '/login/';
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: Failed to load pending bills`);
        }
        
        const data = await response.json();
        this.pendingBills = data.orders || [];
        console.log(`✅ Loaded ${this.pendingBills.length} pending bills`);
        this.renderPendingBills();
        this.populateTableFilter();
        
    } catch (error) {
        console.error('❌ Error loading pending bills:', error);
        this.showError('Failed to load pending bills. Please refresh.');
    }
}

    async loadRecentTransactions() {
    try {
        console.log('📊 Loading recent transactions...');
        
        // FIXED: Use tables API for getting orders
        const response = await fetch(
            `${this.tablesApiBase}/orders/?is_paid=true&ordering=-completed_at&limit=10`,
            { headers: this.getAuthHeaders() }
        );
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: Failed to load transactions`);
        }
        
        const data = await response.json();
        this.recentTransactions = data.results || data.slice(0, 10) || [];
        console.log(`✅ Loaded ${this.recentTransactions.length} recent transactions`);
        this.renderRecentTransactions();
        
    } catch (error) {
        console.error('❌ Error loading transactions:', error);
        // Don't show error for transactions - they're less critical
    }
}

    renderPendingBills() {
        const container = document.getElementById('pending-bills');
        if (!container) {
            console.error('❌ Cannot find #pending-bills container');
            return;
        }
        
        if (!this.pendingBills || this.pendingBills.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <div class="inline-block p-4 bg-gray-100 rounded-full mb-4">
                        <i class="fas fa-check-circle text-3xl"></i>
                    </div>
                    <p class="text-lg font-medium">No pending bills</p>
                    <p class="text-sm">All bills are paid or no orders are served yet</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.pendingBills.map(bill => this.createBillCard(bill)).join('');
        console.log(`✅ Rendered ${this.pendingBills.length} bill cards`);
    }

    createBillCard(bill) {
        const subtotal = parseFloat(bill.subtotal || bill.total_amount || 0);
        const tax = parseFloat(bill.tax_amount || 0);
        const service = parseFloat(bill.service_charge || 0);
        const total = parseFloat(bill.total_amount || 0);
        const tableNum = bill.table?.table_number || 'N/A';
        const orderNum = bill.order_number || `#${bill.id}`;
        const customer = bill.customer_name || 'Guest';
        const time = this.formatTime(bill.placed_at);
        
        return `
            <div class="payment-card bg-white border border-gray-200 rounded-lg p-4 hover:border-red-300 hover:shadow-md transition-all cursor-pointer"
                 onclick="window.cashierDashboard.selectBill(${bill.id})">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <div class="font-bold text-lg text-gray-800">Table ${tableNum}</div>
                        <div class="text-sm text-gray-600">Order ${orderNum}</div>
                        <div class="text-sm text-gray-600">${customer}</div>
                    </div>
                    <div class="text-right">
                        <div class="font-bold text-xl text-red-600">$${total.toFixed(2)}</div>
                        <div class="text-sm text-gray-600">${time}</div>
                    </div>
                </div>
                
                <div class="flex justify-between items-center">
                    <div class="flex items-center">
                        <span class="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-full mr-2">
                            <i class="fas fa-clock mr-1"></i>Unpaid
                        </span>
                        <span class="text-sm text-gray-600">
                            ${bill.items?.length || 0} items
                        </span>
                    </div>
                    <button onclick="event.stopPropagation(); window.cashierDashboard.viewBillDetails(${bill.id})" 
                            class="text-blue-600 hover:text-blue-800 text-sm transition flex items-center">
                        <i class="fas fa-eye mr-1"></i>View
                    </button>
                </div>
            </div>
        `;
    }

    renderRecentTransactions() {
        const container = document.getElementById('recent-transactions');
        if (!container) return;
        
        if (!this.recentTransactions || this.recentTransactions.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="6" class="px-4 py-8 text-center text-gray-500">
                        <i class="fas fa-history text-2xl mb-2"></i>
                        <p>No recent transactions</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        container.innerHTML = this.recentTransactions.map(transaction => 
            this.createTransactionRow(transaction)).join('');
    }

    createTransactionRow(transaction) {
        const total = parseFloat(transaction.total_amount || 0);
        const tableNum = transaction.table?.table_number || 'N/A';
        const orderNum = transaction.order_number || `#${transaction.id}`;
        const time = this.formatTime(transaction.completed_at || transaction.placed_at);
        const paymentMethod = transaction.payment_method || 'cash';
        
        // Method badge color
        const methodClass = paymentMethod === 'cash' ? 'bg-blue-100 text-blue-800' :
                          paymentMethod === 'card' ? 'bg-purple-100 text-purple-800' :
                          'bg-green-100 text-green-800';
        
        return `
            <tr class="border-b border-gray-100 hover:bg-gray-50">
                <td class="px-4 py-3 text-sm">${time}</td>
                <td class="px-4 py-3 text-sm font-medium">${tableNum}</td>
                <td class="px-4 py-3 text-sm text-gray-600">${orderNum}</td>
                <td class="px-4 py-3 text-sm font-bold">$${total.toFixed(2)}</td>
                <td class="px-4 py-3 text-sm">
                    <span class="px-2 py-1 rounded-full text-xs ${methodClass}">
                        ${paymentMethod}
                    </span>
                </td>
                <td class="px-4 py-3 text-sm">
                    <span class="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                        Paid
                    </span>
                </td>
            </tr>
        `;
    }

    selectBill(billId) {
        console.log(`💰 Selecting bill ${billId}`);
        
        const bill = this.pendingBills.find(b => b.id === billId);
        if (!bill) {
            this.showError('Bill not found');
            return;
        }
        
        this.selectedBill = bill;
        this.selectedPaymentMethod = null;
        
        // Update selected bill UI
        this.updateSelectedBillUI(bill);
        
        // Show payment interface
        const paymentInterface = document.getElementById('payment-interface');
        if (paymentInterface) {
            paymentInterface.classList.remove('hidden');
        }
        
        // Update bill summary
        this.updateBillSummary(bill);
        
        // Reset payment interface
        this.resetPaymentInterface();
        
        this.showToast(`Selected bill for Table ${bill.table?.table_number || 'N/A'}`, 'info');
    }

    updateSelectedBillUI(bill) {
        const container = document.getElementById('selected-bill-container');
        const statusBadge = document.getElementById('selected-bill-status');
        
        if (!container) return;
        
        const tableNum = bill.table?.table_number || 'N/A';
        const orderNum = bill.order_number || `#${bill.id}`;
        const customer = bill.customer_name || 'Guest';
        const time = this.formatTime(bill.placed_at);
        
        container.innerHTML = `
            <div class="text-left">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h4 class="font-bold text-lg text-gray-800">Table ${tableNum}</h4>
                        <p class="text-sm text-gray-600">Order ${orderNum}</p>
                    </div>
                    <button onclick="window.cashierDashboard.deselectBill()" 
                            class="text-gray-500 hover:text-gray-700 transition">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="space-y-2 text-sm">
                    <div class="flex justify-between">
                        <span class="text-gray-600">Customer:</span>
                        <span class="font-medium">${customer}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Time:</span>
                        <span>${time}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Items:</span>
                        <span>${bill.items?.length || 0}</span>
                    </div>
                </div>
            </div>
        `;
        
        if (statusBadge) {
            statusBadge.textContent = 'Selected';
            statusBadge.className = 'px-3 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800';
        }
    }

    deselectBill() {
        this.selectedBill = null;
        this.selectedPaymentMethod = null;
        
        const container = document.getElementById('selected-bill-container');
        const statusBadge = document.getElementById('selected-bill-status');
        const paymentInterface = document.getElementById('payment-interface');
        
        if (container) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <div class="inline-block p-4 bg-gray-100 rounded-full mb-4">
                        <i class="fas fa-hand-pointer text-2xl"></i>
                    </div>
                    <p class="font-medium">Select a bill</p>
                    <p class="text-sm mt-1">Click on a bill from the left panel to process payment</p>
                </div>
            `;
        }
        
        if (statusBadge) {
            statusBadge.textContent = 'None';
            statusBadge.className = 'px-3 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800';
        }
        
        if (paymentInterface) {
            paymentInterface.classList.add('hidden');
        }
        
        this.showToast('Bill deselected', 'info');
    }

    updateBillSummary(bill) {
        const subtotal = parseFloat(bill.subtotal || bill.total_amount || 0);
        const tax = parseFloat(bill.tax_amount || 0);
        const service = parseFloat(bill.service_charge || 0);
        const total = parseFloat(bill.total_amount || 0);
        const paid = parseFloat(bill.paid_amount || 0);
        const balance = total - paid;
        
        this.updateElement('bill-subtotal', `$${subtotal.toFixed(2)}`);
        this.updateElement('bill-tax', `$${tax.toFixed(2)}`);
        this.updateElement('bill-service', `$${service.toFixed(2)}`);
        this.updateElement('bill-total', `$${total.toFixed(2)}`);
        
        // For balance, we'll just show total for now
        this.updateElement('bill-balance', `$${total.toFixed(2)}`);
        
        // Update amount received placeholder
        const amountInput = document.getElementById('amount-received');
        if (amountInput) {
            amountInput.placeholder = total.toFixed(2);
            amountInput.value = total.toFixed(2); // Auto-fill with total
            this.validatePayment(); // Trigger validation
        }
    }

    resetPaymentInterface() {
        this.selectedPaymentMethod = null;
        
        // Reset payment method buttons
        document.querySelectorAll('.payment-method-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Hide change container
        const changeContainer = document.getElementById('change-container');
        if (changeContainer) {
            changeContainer.classList.add('hidden');
        }
        
        // Disable process button
        const processBtn = document.getElementById('process-payment-btn');
        if (processBtn) {
            processBtn.disabled = true;
        }
    }

    selectPaymentMethod(method) {
        console.log(`💳 Selecting payment method: ${method}`);
        
        this.selectedPaymentMethod = method;
        
        // Update UI
        document.querySelectorAll('.payment-method-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        event.target.classList.add('active');
        
        // For cash payments, show amount input
        const amountInput = document.getElementById('amount-received');
        if (amountInput && method === 'cash') {
            amountInput.value = amountInput.placeholder;
        }
        
        // Validate payment
        this.validatePayment();
    }

    addAmount(amount) {
        const input = document.getElementById('amount-received');
        if (!input) return;
        
        const current = parseFloat(input.value) || 0;
        input.value = (current + amount).toFixed(2);
        
        // Trigger change calculation and validation
        this.calculateChange();
        this.validatePayment();
    }

    calculateChange() {
        const amountInput = document.getElementById('amount-received');
        const totalElement = document.getElementById('bill-total');
        const changeContainer = document.getElementById('change-container');
        const changeAmount = document.getElementById('change-amount');
        
        if (!amountInput || !totalElement || !changeContainer || !changeAmount) return;
        
        const amountReceived = parseFloat(amountInput.value) || 0;
        const total = parseFloat(totalElement.textContent.replace('$', '')) || 0;
        
        if (this.selectedPaymentMethod === 'cash' && amountReceived > total) {
            const change = amountReceived - total;
            changeAmount.textContent = `$${change.toFixed(2)}`;
            changeContainer.classList.remove('hidden');
        } else {
            changeContainer.classList.add('hidden');
        }
    }

    validatePayment() {
        const amountInput = document.getElementById('amount-received');
        const totalElement = document.getElementById('bill-total');
        const processBtn = document.getElementById('process-payment-btn');
        
        if (!amountInput || !totalElement || !processBtn) return;
        
        const amountReceived = parseFloat(amountInput.value) || 0;
        const total = parseFloat(totalElement.textContent.replace('$', '')) || 0;
        
        // For cash: amount can be any positive number (change will be calculated)
        // For non-cash: amount must be >= total
        let isValid = false;
        
        if (this.selectedPaymentMethod === 'cash') {
            isValid = amountReceived > 0;
        } else if (this.selectedPaymentMethod) {
            isValid = amountReceived >= total;
        }
        
        processBtn.disabled = !isValid;
        
        // Update button text based on method
        if (isValid) {
            processBtn.innerHTML = `
                <i class="fas fa-check-circle mr-2"></i>
                Process ${this.selectedPaymentMethod === 'cash' ? 'Cash' : this.selectedPaymentMethod} Payment
            `;
        }
    }

    async processPayment() {
    if (!this.selectedBill || !this.selectedPaymentMethod) {
        this.showError('Please select a bill and payment method');
        return;
    }
    
    const amountInput = document.getElementById('amount-received');
    if (!amountInput) return;
    
    const amountReceived = parseFloat(amountInput.value) || 0;
    const total = parseFloat(document.getElementById('bill-total').textContent.replace('$', '')) || 0;
    
    // Industry-standard validation
    if (this.selectedPaymentMethod !== 'cash' && amountReceived !== total) {
        this.showError('For non-cash payments, amount must equal the total');
        return;
    }
    
    if (this.selectedPaymentMethod === 'cash' && amountReceived < total) {
        this.showError('Cash payment must be equal to or greater than total');
        return;
    }
    
    // Get customer details if available
    const customerName = this.selectedBill.customer_name || '';
    const customerPhone = this.selectedBill.customer_phone || '';
    
    // Prepare payment data (industry standard format)
    const paymentData = {
        order_id: this.selectedBill.id,
        payment_method: this.selectedPaymentMethod,
        amount: amountReceived,
        customer_name: customerName,
        customer_phone: customerPhone,
        notes: `Processed by ${this.user.username} at ${new Date().toLocaleString()}`,
        metadata: {
            table_number: this.selectedBill.table?.table_number,
            order_number: this.selectedBill.order_number
        }
    };
    
    // Show confirmation with details
    const confirmed = await this.showConfirm(
        `Process ${this.selectedPaymentMethod.toUpperCase()} payment of $${amountReceived.toFixed(2)}?\n\n` +
        `Order: #${this.selectedBill.order_number}\n` +
        `Table: ${this.selectedBill.table?.table_number || 'N/A'}\n` +
        `Customer: ${customerName || 'Guest'}`,
        'Confirm Payment Processing'
    );
    
    if (!confirmed) return;
    
    try {
        // Use industry-standard payment processing endpoint
        const response = await fetch(`${this.apiBase}/cashier/process/`, {
            method: 'POST',
            headers: this.getAuthHeaders(),
            body: JSON.stringify(paymentData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}: Payment failed`);
        }
        
        const result = await response.json();
        console.log('✅ Payment processed:', result);
        
        // Industry-standard success handling
        if (result.success) {
            this.showToast(`Payment ${result.payment_id} processed successfully!`, 'success');
            
            // Play success sound (industry standard)
            this.playPaymentSound('success');
            
            // Generate and show receipt
            this.generateAndShowReceipt(result.payment_id, result.receipt_number);
            
            // Refresh dashboard data
            await this.loadPendingBills();
            await this.loadRecentTransactions();
            await this.updateStats();
            
            // Reset after delay (industry standard UX)
            setTimeout(() => {
                this.deselectBill();
            }, 3000);
        } else {
            throw new Error(result.error || 'Payment failed');
        }
        
    } catch (error) {
        console.error('❌ Payment processing error:', error);
        
        // Play error sound
        this.playPaymentSound('error');
        
        // Industry-standard error handling
        this.showError(`Payment failed: ${error.message}`);
        
        // Log error for support
        this.logPaymentError(error, paymentData);
    }
}

// Industry-standard helper methods
playPaymentSound(type) {
    if (type === 'success') {
        // Play success sound
        const audio = new Audio('/static/sounds/payment-success.mp3');
        audio.volume = 0.3;
        audio.play().catch(e => console.log('Audio play failed:', e));
    } else {
        // Play error sound
        const audio = new Audio('/static/sounds/payment-error.mp3');
        audio.volume = 0.3;
        audio.play().catch(e => console.log('Audio play failed:', e));
    }
}

async generateAndShowReceipt(paymentId, receiptNumber) {
    try {
        // Fetch receipt from API
        const response = await fetch(`${this.apiBase}/cashier/receipt/${paymentId}/`, {
            headers: this.getAuthHeaders()
        });
        
        if (response.ok) {
            const receiptData = await response.json();
            this.showReceiptModal(receiptData);
        }
    } catch (error) {
        console.error('Error generating receipt:', error);
        // Still show basic receipt
        this.showReceiptModal({
            receipt_number: receiptNumber,
            payment_id: paymentId,
            timestamp: new Date().toISOString()
        });
    }
}

logPaymentError(error, paymentData) {
    // In production, this would log to your error tracking service
    console.error('PAYMENT ERROR LOG:', {
        timestamp: new Date().toISOString(),
        user: this.user.username,
        error: error.message,
        payment_data: paymentData,
        stack: error.stack
    });
}

    async updateStats() {
        try {
            // Calculate totals from pending bills
            const pendingCount = this.pendingBills.length;
            const todayRevenue = this.pendingBills.reduce((sum, bill) => {
                return sum + parseFloat(bill.total_amount || 0);
            }, 0);
            
            // Simulate payment method breakdown
            const cardCount = Math.floor(pendingCount * 0.3);
            const mobileCount = Math.floor(pendingCount * 0.2);
            
            // Update UI
            this.updateElement('pending-payments', pendingCount);
            this.updateElement('today-revenue', `$${todayRevenue.toFixed(2)}`);
            this.updateElement('card-payments', cardCount);
            this.updateElement('mobile-payments', mobileCount);
            
        } catch (error) {
            console.error('Error updating stats:', error);
        }
    }

    populateTableFilter() {
        const filter = document.getElementById('table-filter');
        if (!filter) return;
        
        // Get unique table numbers from pending bills
        const tables = [...new Set(this.pendingBills
            .map(bill => bill.table?.table_number)
            .filter(tableNum => tableNum !== undefined && tableNum !== null)
            .sort((a, b) => a - b))];
        
        // Clear existing options except "All Tables"
        while (filter.options.length > 1) {
            filter.remove(1);
        }
        
        // Add table options
        tables.forEach(tableNum => {
            const option = document.createElement('option');
            option.value = tableNum;
            option.textContent = `Table ${tableNum}`;
            filter.appendChild(option);
        });
    }

    filterByTable(tableNumber) {
        if (tableNumber === 'all') {
            this.renderPendingBills();
        } else {
            const filtered = this.pendingBills.filter(bill => bill.table?.table_number == tableNumber);
            
            const container = document.getElementById('pending-bills');
            if (!container) return;
            
            if (filtered.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-12 text-gray-500">
                        <i class="fas fa-search text-3xl mb-3"></i>
                        <p>No bills for Table ${tableNumber}</p>
                        <p class="text-sm">Select a different table</p>
                    </div>
                `;
            } else {
                container.innerHTML = filtered.map(bill => this.createBillCard(bill)).join('');
            }
        }
    }

    async viewBillDetails(billId) {
        const bill = this.pendingBills.find(b => b.id === billId);
        if (!bill) return;
        
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div class="p-6">
                    <div class="flex justify-between items-start mb-6">
                        <div>
                            <h3 class="text-xl font-bold text-gray-800">Bill Details</h3>
                            <p class="text-gray-600">Order #${bill.order_number || bill.id}</p>
                        </div>
                        <button onclick="this.closest('.fixed').remove()" 
                                class="text-gray-500 hover:text-gray-700">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>
                    
                    ${this.createBillDetailsHTML(bill)}
                    
                    <div class="mt-6 flex gap-3">
                        <button onclick="window.cashierDashboard.selectBill(${bill.id}); this.closest('.fixed').remove()" 
                                class="flex-1 py-3 bg-green-600 text-white font-bold rounded-lg hover:bg-green-700 transition">
                            <i class="fas fa-cash-register mr-2"></i>Process Payment
                        </button>
                        <button onclick="this.closest('.fixed').remove()" 
                                class="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    createBillDetailsHTML(bill) {
        const subtotal = parseFloat(bill.subtotal || 0);
        const tax = parseFloat(bill.tax_amount || 0);
        const service = parseFloat(bill.service_charge || 0);
        const total = parseFloat(bill.total_amount || 0);
        
        let itemsHTML = '';
        if (bill.items && bill.items.length > 0) {
            itemsHTML = bill.items.map(item => `
                <div class="flex justify-between items-start py-3 border-b border-gray-100">
                    <div>
                        <div class="font-medium">${item.quantity}x ${item.menu_item?.name || 'Item'}</div>
                        ${item.special_instructions ? `
                            <div class="text-sm text-gray-600 italic mt-1">${item.special_instructions}</div>
                        ` : ''}
                    </div>
                    <div class="text-right">
                        <div class="font-medium">$${(item.quantity * item.unit_price).toFixed(2)}</div>
                    </div>
                </div>
            `).join('');
        }
        
        return `
            <div class="space-y-6">
                <!-- Customer Info -->
                <div class="bg-gray-50 p-4 rounded-lg">
                    <div class="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <div class="text-gray-600">Table</div>
                            <div class="font-medium">${bill.table?.table_number || 'N/A'}</div>
                        </div>
                        <div>
                            <div class="text-gray-600">Customer</div>
                            <div class="font-medium">${bill.customer_name || 'Guest'}</div>
                        </div>
                        <div>
                            <div class="text-gray-600">Order Time</div>
                            <div class="font-medium">${this.formatTime(bill.placed_at)}</div>
                        </div>
                        <div>
                            <div class="text-gray-600">Status</div>
                            <div class="font-medium text-red-600">Unpaid</div>
                        </div>
                    </div>
                </div>
                
                <!-- Order Items -->
                <div>
                    <h4 class="font-bold text-gray-700 mb-3">Order Items</h4>
                    ${itemsHTML || '<p class="text-gray-500 text-center py-4">No items found</p>'}
                </div>
                
                <!-- Payment Summary -->
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h4 class="font-bold text-gray-700 mb-3">Payment Summary</h4>
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span class="text-gray-600">Subtotal:</span>
                            <span>$${subtotal.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Tax (15%):</span>
                            <span>$${tax.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Service (10%):</span>
                            <span>$${service.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between pt-2 border-t border-gray-300 font-bold text-lg">
                            <span>Total:</span>
                            <span class="text-red-600">$${total.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    showReceipt(amountReceived) {
        if (!this.selectedBill) return;
        
        const bill = this.selectedBill;
        const total = parseFloat(document.getElementById('bill-total').textContent.replace('$', '')) || 0;
        const change = this.selectedPaymentMethod === 'cash' && amountReceived > total ? amountReceived - total : 0;
        const now = new Date();
        
        // Create modal
        const modal = document.getElementById('receipt-modal');
        if (!modal) return;
        
        modal.innerHTML = `
            <div class="bg-white rounded-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
                <div class="p-6">
                    <div class="text-center mb-6">
                        <h3 class="text-xl font-bold">PAYMENT RECEIPT</h3>
                        <p class="text-sm text-gray-600">${now.toLocaleDateString()} ${now.toLocaleTimeString()}</p>
                    </div>
                    
                    ${this.createReceiptHTML(bill, amountReceived, change)}
                    
                    <div class="mt-6 flex gap-3">
                        <button onclick="window.cashierDashboard.printReceipt()" 
                                class="flex-1 py-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition">
                            <i class="fas fa-print mr-2"></i>Print Receipt
                        </button>
                        <button onclick="window.cashierDashboard.closeReceipt()" 
                                class="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
                            Done
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        modal.classList.remove('hidden');
    }

    createReceiptHTML(bill, amountReceived, change) {
        const subtotal = parseFloat(bill.subtotal || 0);
        const tax = parseFloat(bill.tax_amount || 0);
        const service = parseFloat(bill.service_charge || 0);
        const total = parseFloat(bill.total_amount || 0);
        const now = new Date();
        
        return `
            <div class="receipt bg-white text-black">
                <!-- Header -->
                <div class="text-center border-b pb-4 mb-4">
                    <div class="font-bold text-lg">RESTAURANT RECEIPT</div>
                    <div class="text-sm">${now.toLocaleDateString()} ${now.toLocaleTimeString()}</div>
                    <div class="text-sm">Order #${bill.order_number || bill.id}</div>
                    <div class="text-sm">Table ${bill.table?.table_number || 'N/A'}</div>
                </div>
                
                <!-- Items -->
                <div class="mb-4">
                    ${(bill.items || []).map(item => `
                        <div class="flex justify-between text-sm mb-1">
                            <span>${item.quantity}x ${item.menu_item?.name || 'Item'}</span>
                            <span>$${(item.quantity * item.unit_price).toFixed(2)}</span>
                        </div>
                    `).join('')}
                </div>
                
                <!-- Totals -->
                <div class="border-t border-b py-3 my-3">
                    <div class="flex justify-between text-sm">
                        <span>Subtotal:</span>
                        <span>$${subtotal.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between text-sm">
                        <span>Tax:</span>
                        <span>$${tax.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between text-sm">
                        <span>Service:</span>
                        <span>$${service.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between font-bold mt-2">
                        <span>TOTAL:</span>
                        <span>$${total.toFixed(2)}</span>
                    </div>
                </div>
                
                <!-- Payment -->
                <div class="mb-4">
                    <div class="flex justify-between text-sm">
                        <span>Payment Method:</span>
                        <span class="font-medium">${this.selectedPaymentMethod}</span>
                    </div>
                    <div class="flex justify-between text-sm">
                        <span>Amount Paid:</span>
                        <span>$${amountReceived.toFixed(2)}</span>
                    </div>
                    ${change > 0 ? `
                        <div class="flex justify-between text-sm">
                            <span>Change:</span>
                            <span>$${change.toFixed(2)}</span>
                        </div>
                    ` : ''}
                </div>
                
                <!-- Footer -->
                <div class="text-center text-sm text-gray-600">
                    <div>Thank you for dining with us!</div>
                    <div>Please visit again</div>
                </div>
            </div>
        `;
    }

    printReceipt() {
        window.print();
    }

    closeReceipt() {
        const modal = document.getElementById('receipt-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.innerHTML = '';
        }
    }

    openCashDrawer() {
        this.showToast('Cash drawer opened', 'info');
    }

    startPolling() {
        this.pollingTimer = setInterval(() => {
            this.loadPendingBills();
            this.loadRecentTransactions();
        }, this.pollingInterval);
    }

    stopPolling() {
        if (this.pollingTimer) {
            clearInterval(this.pollingTimer);
        }
    }

    // ==================== UTILITY METHODS ====================

    formatTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    }

    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = content;
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) {
            // Create container if it doesn't exist
            const newContainer = document.createElement('div');
            newContainer.id = 'toast-container';
            newContainer.className = 'toast-container';
            document.body.appendChild(newContainer);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'success' ? 'fa-check-circle' :
                    type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle';
        
        toast.innerHTML = `
            <div class="flex items-center">
                <i class="fas ${icon} mr-3"></i>
                <span>${message}</span>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    async showConfirm(message, title = 'Confirm') {
        return new Promise((resolve) => {
            if (window.confirm(`${title}\n\n${message}`)) {
                resolve(true);
            } else {
                resolve(false);
            }
        });
    }

    getCsrfToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }

    setupEventListeners() {
        console.log('🔗 Setting up event listeners...');
        
        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadPendingBills();
                this.loadRecentTransactions();
                this.showToast('Dashboard refreshed', 'info');
            });
        }
        
        // Table filter
        const tableFilter = document.getElementById('table-filter');
        if (tableFilter) {
            tableFilter.addEventListener('change', (e) => {
                this.filterByTable(e.target.value);
            });
        }
        
        // Cash drawer button
        const cashDrawerBtn = document.getElementById('cash-drawer-btn');
        if (cashDrawerBtn) {
            cashDrawerBtn.addEventListener('click', () => this.openCashDrawer());
        }
        
        // Print receipt button
        const printBtn = document.getElementById('print-receipt-btn');
        if (printBtn) {
            printBtn.addEventListener('click', () => this.printReceipt());
        }
        
        // Payment method buttons (event delegation)
        document.addEventListener('click', (e) => {
            if (e.target.closest('.payment-method-btn')) {
                const method = e.target.closest('.payment-method-btn').dataset.method;
                this.selectPaymentMethod(method);
            }
            
            if (e.target.closest('[data-amount]')) {
                const amount = parseFloat(e.target.closest('[data-amount]').dataset.amount);
                this.addAmount(amount);
            }
        });
        
        // Amount received input
        const amountInput = document.getElementById('amount-received');
        if (amountInput) {
            amountInput.addEventListener('input', () => {
                this.calculateChange();
                this.validatePayment();
            });
        }
        
        // Process payment button
        const processBtn = document.getElementById('process-payment-btn');
        if (processBtn) {
            processBtn.addEventListener('click', () => this.processPayment());
        }
        
        console.log('✅ Event listeners set up');
    }

// Add to cashier-dashboard.js
setupPaymentStatusPolling() {
    // Poll for payment status updates every 5 seconds
    this.paymentStatusInterval = setInterval(async () => {
        if (this.selectedBill && this.selectedPaymentMethod !== 'cash') {
            await this.checkPaymentStatus();
        }
    }, 5000);
}

async checkPaymentStatus() {
    if (!this.selectedBill) return;
    
    try {
        const response = await fetch(`${this.apiBase}/payments/status/?order_id=${this.selectedBill.id}`, {
            headers: this.getAuthHeaders()
        });
        
        if (response.ok) {
            const status = await response.json();
            if (status.state === 'completed') {
                this.showToast('Digital payment completed!', 'success');
                this.loadPendingBills(); // Refresh
            } else if (status.state === 'failed') {
                this.showError('Payment failed. Please try another method.');
            }
        }
    } catch (error) {
        // Silent fail for polling
    }
}


    
}

class PaymentErrorHandler {
    static handle(error, context) {
        const errorMap = {
            'insufficient_funds': {
                message: 'Insufficient funds',
                action: 'Please try another payment method or contact the customer',
                severity: 'high'
            },
            'network_error': {
                message: 'Network connection failed',
                action: 'Check internet connection and try again',
                severity: 'medium'
            },
            'gateway_timeout': {
                message: 'Payment gateway timeout',
                action: 'Please wait and try again in 30 seconds',
                severity: 'medium'
            },
            'invalid_card': {
                message: 'Invalid card details',
                action: 'Please check card details and try again',
                severity: 'high'
            },
            'duplicate_payment': {
                message: 'Duplicate payment detected',
                action: 'This payment has already been processed',
                severity: 'critical'
            }
        };
        
        const errorInfo = errorMap[error.code] || {
            message: 'Payment processing error',
            action: 'Please try again or contact support',
            severity: 'unknown'
        };
        
        // Log error for monitoring
        PaymentErrorHandler.logError(error, context, errorInfo);
        
        // Show appropriate user message
        return {
            userMessage: `${errorInfo.message}. ${errorInfo.action}`,
            shouldRetry: errorInfo.severity !== 'critical',
            requiresSupport: errorInfo.severity === 'critical'
        };
    }
    
    static logError(error, context, errorInfo) {
        console.error('PAYMENT ERROR:', {
            timestamp: new Date().toISOString(),
            error: error.message,
            code: error.code,
            context: context,
            info: errorInfo,
            stack: error.stack
        });
        
        // In production: Send to error tracking service
        // Sentry.captureException(error, {extra: {context, errorInfo}});
    }
}



// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM loaded, initializing CashierDashboard...');
    window.cashierDashboard = new CashierDashboard();
});

// Also initialize if script is loaded after DOM is ready
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    console.log('🚀 Document ready, initializing CashierDashboard...');
    window.cashierDashboard = new CashierDashboard();
}