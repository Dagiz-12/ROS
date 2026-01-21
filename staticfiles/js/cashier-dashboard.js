// static/js/cashier-dashboard.js
class CashierDashboard {
    constructor() {
        this.apiBase = '/api/tables';
        this.pollingInterval = 20000; // 20 seconds for updates
        this.selectedBill = null;
        this.selectedPaymentMethod = null;
        this.pendingBills = [];
        this.recentTransactions = [];
        
        this.init();
    }

    async init() {
        console.log('💰 Cashier Dashboard Initializing...');
        
        // Setup UI first
        this.setupUI();
        
        // Check authentication
        if (!await this.checkAuth()) {
            return;
        }
        
        // Load initial data
        await this.loadPendingBills();
        await this.loadRecentTransactions();
        await this.updateStats();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Start polling for updates
        this.startPolling();
        
        console.log('💰 Cashier Dashboard Ready');
    }

    setupUI() {
        // Update user info if available from template
        const userDataElement = document.getElementById('user-data');
        if (userDataElement) {
            try {
                const userData = JSON.parse(userDataElement.dataset.user || '{}');
                if (userData.username) {
                    const nameElement = document.getElementById('cashierName');
                    if (nameElement) {
                        nameElement.textContent = userData.username;
                    }
                }
            } catch (e) {
                console.log('Could not parse user data');
            }
        }
    }

    async checkAuth() {
        // Check if we have auth token
        const token = localStorage.getItem('access_token');
        const userData = localStorage.getItem('user_data');
        
        if (!token || !userData) {
            console.warn('User not authenticated, redirecting to login...');
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

    async loadPendingBills() {
        try {
            this.showLoading(true, 'pending-bills');
            
            const headers = {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            };
            
            // Get served or completed orders that are not paid
            const response = await fetch(`${this.apiBase}/orders/?status=served,completed&is_paid=false`, {
                headers: headers
            });
            
            if (response.status === 401 || response.status === 403) {
                localStorage.clear();
                window.location.href = '/login/';
                return;
            }
            
            if (!response.ok) {
                throw new Error(`Failed to load pending bills: ${response.status}`);
            }
            
            const data = await response.json();
            this.pendingBills = data.results || data;
            this.renderPendingBills();
            
            this.populateTableFilter();
            
            this.showLoading(false, 'pending-bills');
            
        } catch (error) {
            console.error('Error loading pending bills:', error);
            this.showError('Failed to load pending bills');
            this.showLoading(false, 'pending-bills');
        }
    }

    async loadRecentTransactions() {
        try {
            const headers = {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            };
            
            // Get recent paid orders
            const response = await fetch(`${this.apiBase}/orders/?is_paid=true&ordering=-completed_at&limit=10`, {
                headers: headers
            });
            
            if (!response.ok) {
                throw new Error(`Failed to load transactions: ${response.status}`);
            }
            
            const data = await response.json();
            this.recentTransactions = data.results || data.slice(0, 10);
            this.renderRecentTransactions();
            
        } catch (error) {
            console.error('Error loading transactions:', error);
        }
    }

    renderPendingBills() {
        const container = document.getElementById('pending-bills');
        if (!container) return;
        
        if (!this.pendingBills || this.pendingBills.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <i class="fas fa-check-circle text-3xl mb-3"></i>
                    <p>No pending bills</p>
                    <p class="text-sm">All bills are paid</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.pendingBills.map(bill => this.createBillCard(bill)).join('');
    }

    createBillCard(bill) {
        const subtotal = parseFloat(bill.subtotal || bill.total_amount || 0);
        const tax = parseFloat(bill.tax_amount || 0);
        const service = parseFloat(bill.service_charge || 0);
        const total = parseFloat(bill.total_amount || 0);
        
        return `
            <div class="payment-card border rounded-lg p-4 status-unpaid cursor-pointer hover:bg-gray-50 transition"
                 onclick="cashierDashboard.selectBill(${bill.id})">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <div class="font-bold text-lg">Table ${bill.table?.table_number || 'N/A'}</div>
                        <div class="text-sm text-gray-600">Order #${bill.order_number}</div>
                        <div class="text-sm text-gray-600">${bill.customer_name || 'Guest'}</div>
                    </div>
                    <div class="text-right">
                        <div class="font-bold text-lg">$${total.toFixed(2)}</div>
                        <div class="text-sm text-gray-600">${this.formatTime(bill.placed_at)}</div>
                    </div>
                </div>
                
                <div class="flex justify-between items-center">
                    <div class="text-sm">
                        <span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs">
                            Unpaid
                        </span>
                        <span class="ml-2 text-gray-600">${bill.items?.length || 0} items</span>
                    </div>
                    <button onclick="event.stopPropagation(); cashierDashboard.viewBillDetails(${bill.id})" 
                            class="text-green-600 hover:text-green-800 text-sm transition">
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
                    <td colspan="5" class="px-4 py-8 text-center text-gray-500">
                        <i class="fas fa-history text-2xl mb-3"></i>
                        <p>No recent transactions</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        container.innerHTML = this.recentTransactions.map(transaction => this.createTransactionRow(transaction)).join('');
    }

    createTransactionRow(transaction) {
        const total = parseFloat(transaction.total_amount || 0);
        const paymentMethod = transaction.payment_method || 'cash';
        const methodClass = paymentMethod === 'cash' ? 'bg-blue-100 text-blue-800' :
                          paymentMethod === 'card' ? 'bg-purple-100 text-purple-800' :
                          'bg-green-100 text-green-800';
        
        return `
            <tr>
                <td class="px-4 py-2 text-sm">${this.formatTime(transaction.completed_at)}</td>
                <td class="px-4 py-2 text-sm">${transaction.table?.table_number || 'N/A'}</td>
                <td class="px-4 py-2 text-sm font-bold">$${total.toFixed(2)}</td>
                <td class="px-4 py-2 text-sm">
                    <span class="px-2 py-1 rounded-full text-xs ${methodClass}">
                        ${paymentMethod}
                    </span>
                </td>
                <td class="px-4 py-2 text-sm">
                    <span class="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                        Paid
                    </span>
                </td>
            </tr>
        `;
    }

    async updateStats() {
        try {
            // Calculate totals from pending bills
            const pendingCount = this.pendingBills.length;
            const todayRevenue = this.pendingBills.reduce((sum, bill) => {
                return sum + parseFloat(bill.total_amount || 0);
            }, 0);
            
            // Simulate payment method breakdown (in real system, this would come from API)
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

    selectBill(billId) {
        const bill = this.pendingBills.find(b => b.id === billId);
        if (!bill) {
            this.showError('Bill not found');
            return;
        }
        
        this.selectedBill = bill;
        this.selectedPaymentMethod = null;
        
        // Update selected bill UI
        const container = document.getElementById('selected-bill-container');
        if (container) {
            container.innerHTML = this.createSelectedBillUI(bill);
        }
        
        // Show payment interface
        const paymentInterface = document.getElementById('payment-interface');
        if (paymentInterface) {
            paymentInterface.classList.remove('hidden');
        }
        
        // Update bill summary
        this.updateBillSummary(bill);
        
        // Reset payment interface
        this.resetPaymentInterface();
    }

    createSelectedBillUI(bill) {
        return `
            <div>
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h4 class="font-bold text-lg">Table ${bill.table?.table_number}</h4>
                        <p class="text-sm text-gray-600">Order #${bill.order_number}</p>
                    </div>
                    <button onclick="cashierDashboard.deselectBill()" class="text-gray-500 hover:text-gray-700 transition">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="space-y-1 text-sm">
                    <div class="flex justify-between">
                        <span>Customer:</span>
                        <span>${bill.customer_name || 'Guest'}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Time:</span>
                        <span>${this.formatTime(bill.placed_at)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Status:</span>
                        <span class="text-red-600 font-bold">Unpaid</span>
                    </div>
                </div>
            </div>
        `;
    }

    deselectBill() {
        this.selectedBill = null;
        const container = document.getElementById('selected-bill-container');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-receipt text-3xl mb-3"></i>
                    <p>No bill selected</p>
                    <p class="text-sm">Select a bill from the left</p>
                </div>
            `;
        }
        
        const paymentInterface = document.getElementById('payment-interface');
        if (paymentInterface) {
            paymentInterface.classList.add('hidden');
        }
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
        this.updateElement('bill-paid', `$${paid.toFixed(2)}`);
        this.updateElement('bill-balance', `$${balance.toFixed(2)}`);
        
        // Update amount received placeholder
        const amountInput = document.getElementById('amount-received');
        if (amountInput) {
            amountInput.placeholder = balance.toFixed(2);
            amountInput.value = '';
        }
    }

    resetPaymentInterface() {
        this.selectedPaymentMethod = null;
        
        // Reset payment method buttons
        document.querySelectorAll('.payment-method-btn').forEach(btn => {
            btn.classList.remove('border-green-500', 'border-2');
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
        
        // Clear amount input
        const amountInput = document.getElementById('amount-received');
        if (amountInput) {
            amountInput.value = '';
        }
    }

    selectPaymentMethod(method) {
        this.selectedPaymentMethod = method;
        
        // Update UI
        document.querySelectorAll('.payment-method-btn').forEach(btn => {
            btn.classList.remove('border-green-500', 'border-2');
        });
        
        event.target.classList.add('border-green-500', 'border-2');
        
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
        const balanceElement = document.getElementById('bill-balance');
        const changeContainer = document.getElementById('change-container');
        const changeAmount = document.getElementById('change-amount');
        
        if (!amountInput || !balanceElement || !changeContainer || !changeAmount) return;
        
        const amountReceived = parseFloat(amountInput.value) || 0;
        const balance = parseFloat(balanceElement.textContent.replace('$', '')) || 0;
        
        if (this.selectedPaymentMethod === 'cash' && amountReceived > balance) {
            const change = amountReceived - balance;
            changeAmount.textContent = `$${change.toFixed(2)}`;
            changeContainer.classList.remove('hidden');
        } else {
            changeContainer.classList.add('hidden');
        }
    }

    validatePayment() {
        const amountInput = document.getElementById('amount-received');
        const balanceElement = document.getElementById('bill-balance');
        const processBtn = document.getElementById('process-payment-btn');
        
        if (!amountInput || !balanceElement || !processBtn) return;
        
        const amountReceived = parseFloat(amountInput.value) || 0;
        const balance = parseFloat(balanceElement.textContent.replace('$', '')) || 0;
        
        const isValid = this.selectedPaymentMethod && 
                      (this.selectedPaymentMethod === 'cash' ? amountReceived >= 0 : amountReceived >= balance);
        
        processBtn.disabled = !isValid;
    }

    async processPayment() {
        if (!this.selectedBill || !this.selectedPaymentMethod) {
            this.showError('Please select a bill and payment method');
            return;
        }
        
        const amountInput = document.getElementById('amount-received');
        if (!amountInput) return;
        
        const amountReceived = parseFloat(amountInput.value) || 0;
        const balance = parseFloat(document.getElementById('bill-balance').textContent.replace('$', '')) || 0;
        
        // Validate amount
        if (this.selectedPaymentMethod !== 'cash' && amountReceived < balance) {
            this.showError('Amount received must be equal to or greater than balance for non-cash payments');
            return;
        }
        
        if (amountReceived <= 0) {
            this.showError('Please enter a valid amount');
            return;
        }
        
        // Confirm payment
        if (!confirm(`Process $${amountReceived.toFixed(2)} as ${this.selectedPaymentMethod} payment?`)) {
            return;
        }
        
        try {
            // Update order payment status
            const response = await fetch(`${this.apiBase}/orders/${this.selectedBill.id}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`,
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({
                    is_paid: true,
                    payment_method: this.selectedPaymentMethod,
                    paid_amount: amountReceived,
                    status: 'completed'
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to process payment');
            }
            
            this.showToast('Payment processed successfully!', 'success');
            
            // Refresh data
            await this.loadPendingBills();
            await this.loadRecentTransactions();
            await this.updateStats();
            
            // Reset interface
            this.deselectBill();
            
            // Show receipt
            this.showReceipt(amountReceived);
            
        } catch (error) {
            console.error('Error processing payment:', error);
            this.showError('Failed to process payment');
        }
    }

    showReceipt(amountReceived) {
        const modal = document.getElementById('receipt-modal');
        const modalContent = modal.querySelector('.p-6');
        
        if (!modal || !modalContent) return;
        
        const bill = this.selectedBill;
        const balance = parseFloat(document.getElementById('bill-balance').textContent.replace('$', '')) || 0;
        const change = this.selectedPaymentMethod === 'cash' && amountReceived > balance ? amountReceived - balance : 0;
        
        modalContent.innerHTML = this.createReceiptHTML(bill, amountReceived, change);
        
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }

    createReceiptHTML(bill, amountReceived, change) {
        const now = new Date();
        
        return `
            <div class="receipt p-4">
                <div class="text-center mb-4">
                    <h2 class="text-xl font-bold">RESTAURANT RECEIPT</h2>
                    <p class="text-sm">123 Main Street</p>
                    <p class="text-sm">Phone: (123) 456-7890</p>
                </div>
                
                <div class="border-t border-b py-2 my-2">
                    <div class="flex justify-between">
                        <span>Order #:</span>
                        <span>${bill.order_number}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Table:</span>
                        <span>${bill.table?.table_number || 'N/A'}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Date:</span>
                        <span>${now.toLocaleDateString()}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Time:</span>
                        <span>${now.toLocaleTimeString()}</span>
                    </div>
                </div>
                
                <div class="my-4">
                    <h3 class="font-bold mb-2">Items:</h3>
                    ${(bill.items || []).map(item => `
                        <div class="flex justify-between text-sm">
                            <span>${item.quantity}x ${item.menu_item?.name || 'Item'}</span>
                            <span>$${(item.quantity * item.unit_price).toFixed(2)}</span>
                        </div>
                    `).join('')}
                </div>
                
                <div class="border-t border-b py-2 my-2">
                    <div class="flex justify-between">
                        <span>Subtotal:</span>
                        <span>$${parseFloat(bill.subtotal || 0).toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Tax:</span>
                        <span>$${parseFloat(bill.tax_amount || 0).toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Service:</span>
                        <span>$${parseFloat(bill.service_charge || 0).toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between font-bold">
                        <span>Total:</span>
                        <span>$${parseFloat(bill.total_amount || 0).toFixed(2)}</span>
                    </div>
                </div>
                
                <div class="my-4">
                    <div class="flex justify-between">
                        <span>Payment Method:</span>
                        <span>${this.selectedPaymentMethod}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Amount Received:</span>
                        <span>$${amountReceived.toFixed(2)}</span>
                    </div>
                    ${change > 0 ? `
                        <div class="flex justify-between">
                            <span>Change:</span>
                            <span>$${change.toFixed(2)}</span>
                        </div>
                    ` : ''}
                </div>
                
                <div class="text-center mt-6">
                    <p class="text-sm">Thank you for dining with us!</p>
                    <p class="text-sm">Please come again</p>
                </div>
            </div>
            
            <div class="mt-4 text-center">
                <button onclick="cashierDashboard.printReceipt()" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition">
                    <i class="fas fa-print mr-2"></i>Print Receipt
                </button>
                <button onclick="cashierDashboard.closeReceipt()" class="ml-2 border border-gray-300 px-4 py-2 rounded hover:bg-gray-50 transition">
                    Close
                </button>
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
            modal.classList.remove('flex');
        }
    }

    async viewBillDetails(billId) {
        // Show bill details in a modal
        const bill = this.pendingBills.find(b => b.id === billId);
        if (!bill) return;
        
        let detailsHTML = `
            <div class="p-6">
                <h3 class="text-lg font-bold mb-4">Bill Details - Order #${bill.order_number}</h3>
                <div class="space-y-4">
                    <div>
                        <h4 class="font-medium mb-2">Customer Information:</h4>
                        <p>Table: ${bill.table?.table_number || 'N/A'}</p>
                        <p>Customer: ${bill.customer_name || 'Guest'}</p>
                        <p>Order Time: ${this.formatTime(bill.placed_at)}</p>
                    </div>
        `;
        
        if (bill.items && bill.items.length > 0) {
            detailsHTML += `
                <div>
                    <h4 class="font-medium mb-2">Order Items:</h4>
                    <div class="space-y-2">
                        ${bill.items.map(item => `
                            <div class="flex justify-between border-b pb-2">
                                <div>
                                    <p>${item.quantity}x ${item.menu_item?.name || 'Item'}</p>
                                    ${item.special_instructions ? `<p class="text-xs text-gray-600 italic">${item.special_instructions}</p>` : ''}
                                </div>
                                <div class="text-right">
                                    <p>$${(item.quantity * item.unit_price).toFixed(2)}</p>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        detailsHTML += `
                    <div class="bg-gray-50 p-4 rounded">
                        <h4 class="font-medium mb-2">Payment Summary:</h4>
                        <div class="space-y-1">
                            <div class="flex justify-between">
                                <span>Subtotal:</span>
                                <span>$${parseFloat(bill.subtotal || 0).toFixed(2)}</span>
                            </div>
                            <div class="flex justify-between">
                                <span>Tax:</span>
                                <span>$${parseFloat(bill.tax_amount || 0).toFixed(2)}</span>
                            </div>
                            <div class="flex justify-between">
                                <span>Service Charge:</span>
                                <span>$${parseFloat(bill.service_charge || 0).toFixed(2)}</span>
                            </div>
                            <div class="flex justify-between font-bold border-t pt-2 mt-2">
                                <span>Total:</span>
                                <span>$${parseFloat(bill.total_amount || 0).toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="mt-6 text-center">
                    <button onclick="cashierDashboard.selectBill(${bill.id})" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition">
                        <i class="fas fa-cash-register mr-2"></i>Process Payment
                    </button>
                    <button onclick="this.closest('.modal').remove()" class="ml-2 border border-gray-300 px-4 py-2 rounded hover:bg-gray-50 transition">
                        Close
                    </button>
                </div>
            </div>
        `;
        
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="bg-white rounded-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
                ${detailsHTML}
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close modal on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    populateTableFilter() {
        const filter = document.getElementById('table-filter');
        if (!filter) return;
        
        // Get unique table numbers
        const tables = [...new Set(this.pendingBills
            .map(bill => bill.table?.table_number)
            .filter(tableNum => tableNum !== undefined))];
        
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
            this.renderPendingBills(filtered);
        }
    }

    openCashDrawer() {
        // Simulate cash drawer opening
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

    // Utility methods
    formatTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = content;
        }
    }

    showLoading(show, elementId = null) {
        if (elementId) {
            const element = document.getElementById(elementId);
            if (element) {
                if (show) {
                    element.classList.add('loading');
                } else {
                    element.classList.remove('loading');
                }
            }
        } else {
            if (show) {
                document.body.classList.add('loading');
            } else {
                document.body.classList.remove('loading');
            }
        }
    }

    showError(message) {
        console.error('Error:', message);
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
            refreshBtn.addEventListener('click', () => {
                this.loadPendingBills();
                this.loadRecentTransactions();
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
        
        // Payment method buttons
        document.querySelectorAll('.payment-method-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const method = e.target.closest('.payment-method-btn').dataset.method;
                this.selectPaymentMethod(method);
            });
        });
        
        // Quick amount buttons
        document.querySelectorAll('[data-amount]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const amount = parseFloat(e.target.dataset.amount);
                this.addAmount(amount);
            });
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
        
        // Print receipt button
        const printBtn = document.getElementById('print-receipt-btn');
        if (printBtn) {
            printBtn.addEventListener('click', () => this.printReceipt());
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.cashierDashboard = new CashierDashboard();
});