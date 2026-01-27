// static/js/cashier/cashier-dashboard-industrial.js - COMPLETE WORKING VERSION
class IndustrialCashierDashboard {
    constructor() {
        console.log('💰 Industrial Cashier Dashboard Initializing...');
        
        this.apiBase = '/api/payments/cashier/dashboard-data/';
        this.paymentsApiBase = '/api/payments/';
        this.pollingInterval = 15000; // 15 seconds
        this.selectedOrder = null;
        this.pendingOrders = [];
        this.todaySummary = {};
        this.recentPayments = [];
        this.user = null;
        this.token = null;
        
        // Prevent double initialization
        if (window.cashierDashboard) {
            console.warn('⚠️ Cashier dashboard already initialized');
            return;
        }
        
        window.cashierDashboard = this;
        this.init();
    }

    async init() {
        console.log('🔧 Setting up...');
        
        // 1. Check authentication
        if (!await this.checkAuth()) {
            return;
        }
        
        // 2. Setup event listeners
        this.setupEventListeners();
        
        // 3. Load data
        await this.loadDashboardData();
        
        // 4. Start polling
        this.startPolling();
        
        console.log('✅ Cashier Dashboard Ready');
    }

    async checkAuth() {
        try {
            this.token = localStorage.getItem('access_token');
            const userData = localStorage.getItem('user_data');
            
            if (!this.token || !userData) {
                console.warn('❌ No auth token, redirecting to login');
                window.location.href = '/login/';
                return false;
            }
            
            this.user = JSON.parse(userData);
            
            // Verify cashier role
            const allowedRoles = ['cashier', 'manager', 'admin'];
            if (!allowedRoles.includes(this.user.role)) {
                this.showToast('Access denied. Cashier role required.', 'error');
                window.location.href = '/login/';
                return false;
            }
            
            console.log(`✅ Authenticated as ${this.user.username} (${this.user.role})`);
            return true;
            
        } catch (error) {
            console.error('Auth error:', error);
            window.location.href = '/login/';
            return false;
        }
    }

    setupEventListeners() {
        console.log('🔗 Setting up event listeners...');
        
        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadDashboardData();
                this.showToast('Dashboard refreshed', 'success');
            });
        }
        
        // Payment method buttons
        document.querySelectorAll('.payment-method-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Remove active class from all buttons
                document.querySelectorAll('.payment-method-btn').forEach(b => {
                    b.classList.remove('active');
                });
                
                // Add active class to clicked button
                e.currentTarget.classList.add('active');
                
                // Show/hide amount input based on method
                const method = e.currentTarget.dataset.method;
                const amountInput = document.getElementById('amount-received');
                if (amountInput) {
                    if (method === 'cash') {
                        amountInput.disabled = false;
                        amountInput.placeholder = 'Enter amount received';
                    } else {
                        amountInput.disabled = true;
                        amountInput.placeholder = 'Amount set to order total';
                        amountInput.value = this.selectedOrder?.total_amount || '';
                    }
                }
            });
        });
        
        // Quick amount buttons
        document.querySelectorAll('[data-amount]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const amount = parseFloat(e.currentTarget.dataset.amount);
                const input = document.getElementById('amount-received');
                if (input) {
                    const currentValue = parseFloat(input.value) || 0;
                    input.value = (currentValue + amount).toFixed(2);
                    this.calculateChange();
                }
            });
        });
        
        // Amount input change listener
        const amountInput = document.getElementById('amount-received');
        if (amountInput) {
            amountInput.addEventListener('input', () => {
                this.calculateChange();
            });
        }
        
        // Process payment button
        const processBtn = document.getElementById('process-payment-btn');
        if (processBtn) {
            processBtn.addEventListener('click', () => {
                this.processSelectedPayment();
            });
        }
        
        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (confirm('Are you sure you want to logout?')) {
                    localStorage.clear();
                    window.location.href = '/login/';
                }
            });
        }
        
        // Cash drawer button
        const cashDrawerBtn = document.getElementById('cash-drawer-btn');
        if (cashDrawerBtn) {
            cashDrawerBtn.addEventListener('click', () => {
                this.showToast('Cash drawer opened (simulated)', 'info');
            });
        }
        
        // Print report button
        const printBtn = document.getElementById('print-receipt-btn');
        if (printBtn) {
            printBtn.addEventListener('click', () => {
                this.printDailyReport();
            });
        }
        
        console.log('✅ Event listeners set up');
    }

    async loadDashboardData() {
        try {
            console.log('📊 Loading dashboard data...');
            const csrfToken = this.getCsrfToken();
            console.log(`🔐 CSRF Token length: ${csrfToken?.length || 0}`);
            
            const response = await fetch(this.apiBase, {
                method: 'GET',
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });
            
            if (response.status === 401 || response.status === 403) {
                localStorage.clear();
                window.location.href = '/login/';
                return;
            }
            
            const data = await response.json();
            console.log('📊 Dashboard response:', data);
            
            if (data.success && data.data) {
                this.updateDashboard(data.data);
            } else if (data.success && !data.data) {
                // Handle different response structure
                this.updateDashboard(data);
            } else {
                console.error('❌ Dashboard API error:', data.error || 'Unknown error');
                // Fallback: load orders directly
                await this.loadOrdersDirectly();
            }
            
        } catch (error) {
            console.error('❌ Dashboard load error:', error);
            // Fallback: load orders directly
            await this.loadOrdersDirectly();
        }
    }

    async loadOrdersDirectly() {
        try {
            console.log('🔄 Loading orders directly...');
            
            const response = await fetch('/api/tables/orders/?status=served', {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('📦 Direct orders data:', data);
                
                // Check if data is an array or has results
                let orders = [];
                if (Array.isArray(data)) {
                    orders = data;
                } else if (data.results && Array.isArray(data.results)) {
                    orders = data.results;
                } else if (data.orders && Array.isArray(data.orders)) {
                    orders = data.orders;
                }
                
                // Filter unpaid orders
                this.pendingOrders = orders.filter(order => 
                    (order.status === 'served' || order.status === 'bill_presented') && 
                    !order.is_paid
                );
                
                console.log(`📦 Found ${this.pendingOrders.length} unpaid orders`);
                this.renderPendingOrders();
            }
        } catch (error) {
            console.error('Direct orders error:', error);
        }
    }

    updateDashboard(data) {
        console.log('📊 Updating dashboard with:', data);
        
        // Extract data based on structure
        if (data.pending_orders && data.pending_orders.orders) {
            this.pendingOrders = data.pending_orders.orders;
        } else if (data.orders && Array.isArray(data.orders)) {
            this.pendingOrders = data.orders;
        } else if (Array.isArray(data)) {
            this.pendingOrders = data;
        } else {
            this.pendingOrders = [];
        }
        
        // Extract today summary
        if (data.today_summary) {
            this.todaySummary = data.today_summary;
        } else if (data.summary) {
            this.todaySummary = data.summary;
        }
        
        // Extract recent payments
        if (data.recent_payments && Array.isArray(data.recent_payments)) {
            this.recentPayments = data.recent_payments;
        } else if (data.recent && Array.isArray(data.recent)) {
            this.recentPayments = data.recent;
        } else if (data.payments && Array.isArray(data.payments)) {
            this.recentPayments = data.payments;
        } else {
            this.recentPayments = [];
        }
        
        console.log(`📦 Parsed: ${this.pendingOrders.length} orders, ${this.recentPayments.length} recent payments`);
        
        // Render all components
        this.renderPendingOrders();
        this.renderTodaySummary();
        this.renderRecentPayments();
    }

    renderPendingOrders() {
        const container = document.getElementById('pending-bills');
        if (!container) {
            console.error('❌ pending-bills container not found');
            return;
        }
        
        if (!this.pendingOrders || this.pendingOrders.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <div class="inline-block p-4 bg-gray-100 rounded-full mb-4">
                        <i class="fas fa-check-circle text-3xl"></i>
                    </div>
                    <p class="text-lg font-medium">No pending bills</p>
                    <p class="text-sm">All orders are paid or no orders are served yet</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.pendingOrders.map(order => this.createOrderCard(order)).join('');
        
        // Add click listeners to order cards
        container.querySelectorAll('.payment-card').forEach(card => {
            const orderId = card.getAttribute('data-order-id');
            card.addEventListener('click', () => {
                this.selectOrder(orderId);
            });
        });
    }

    createOrderCard(order) {
        // Safely get table number
        let tableNum = 'N/A';
        if (order.table) {
            if (typeof order.table === 'object') {
                tableNum = order.table.table_number || 'N/A';
            } else if (order.table_details) {
                tableNum = order.table_details.table_number || 'N/A';
            } else if (order.table_number) {
                tableNum = order.table_number;
            }
        }
        
        const orderNum = order.order_number || `#${order.id}`;
        const customer = order.customer_name || 'Guest';
        const total = order.total_amount ? parseFloat(order.total_amount).toFixed(2) : '0.00';
        
        return `
            <div class="payment-card bg-white border border-gray-200 rounded-lg p-4 hover:border-red-300 hover:shadow-md transition-all cursor-pointer"
                 data-order-id="${order.id}">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <div class="font-bold text-lg text-gray-800">Table ${tableNum}</div>
                        <div class="text-sm text-gray-600">Order ${orderNum}</div>
                        <div class="text-sm text-gray-600">${customer}</div>
                    </div>
                    <div class="text-right">
                        <div class="font-bold text-xl text-red-600">$${total}</div>
                        <div class="text-xs text-gray-500">
                            ${order.status === 'served' ? 'Ready for payment' : 
                              order.status === 'bill_presented' ? 'Bill presented' : 
                              order.status || 'Pending'}
                        </div>
                    </div>
                </div>
                
                <div class="flex justify-between items-center">
                    <div class="flex items-center">
                        <span class="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-full mr-2">
                            <i class="fas fa-clock mr-1"></i>${order.status === 'bill_presented' ? 'Bill Presented' : 'Awaiting Payment'}
                        </span>
                    </div>
                    <button class="select-order-btn bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition flex items-center">
                        <i class="fas fa-money-bill-wave mr-1"></i>Process Payment
                    </button>
                </div>
            </div>
        `;
    }

    selectOrder(orderId) {
        console.log(`💰 Selecting order ${orderId}`);
        const order = this.pendingOrders.find(o => o.id == orderId); // Use loose equality
        if (!order) {
            console.error(`Order ${orderId} not found in pending orders`);
            this.showToast('Order not found', 'error');
            return;
        }
        
        this.selectedOrder = order;
        this.showOrderDetails(order);
    }

    showOrderDetails(order) {
        // Update selected bill interface
        const container = document.getElementById('selected-bill-container');
        const interfaceDiv = document.getElementById('payment-interface');
        
        if (!container || !interfaceDiv) {
            console.error('Required UI elements not found');
            return;
        }
        
        // Hide container, show interface
        container.classList.add('hidden');
        interfaceDiv.classList.remove('hidden');
        
        // Update bill details
        this.updateElement('bill-subtotal', `$${order.subtotal || '0.00'}`);
        this.updateElement('bill-tax', `$${order.tax_amount || '0.00'}`);
        this.updateElement('bill-service', `$${order.service_charge || '0.00'}`);
        this.updateElement('bill-total', `$${order.total_amount || '0.00'}`);
        
        // Set amount received to total
        const amountInput = document.getElementById('amount-received');
        if (amountInput) {
            amountInput.value = order.total_amount || '0.00';
            amountInput.disabled = false; // Enable for cash payments
        }
        
        // Reset payment method selection
        document.querySelectorAll('.payment-method-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        // Select cash by default
        const cashBtn = document.querySelector('.payment-method-btn[data-method="cash"]');
        if (cashBtn) cashBtn.classList.add('active');
        
        // Update selected bill status
        const statusElement = document.getElementById('selected-bill-status');
        if (statusElement) {
            statusElement.textContent = 'Selected';
            statusElement.className = 'px-3 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800';
        }
        
        // Enable process button
        const processBtn = document.getElementById('process-payment-btn');
        if (processBtn) {
            processBtn.disabled = false;
        }
        
        // Calculate change if cash payment
        this.calculateChange();
        
        this.showToast(`Selected Order #${order.order_number || order.id} from Table ${order.table?.table_number || 'N/A'}`, 'info');
    }

    renderTodaySummary() {
        // Update pending payments count
        this.updateElement('pending-payments', this.pendingOrders.length);
        
        // Update today's revenue
        const revenue = this.todaySummary.revenue || 0;
        this.updateElement('today-revenue', `$${parseFloat(revenue).toFixed(2)}`);
        
        // Count payment methods
        if (this.recentPayments && this.recentPayments.length > 0) {
            const cardPayments = this.recentPayments.filter(p => 
                p.payment_method === 'card' || p.payment_method?.toLowerCase().includes('card')
            ).length;
            
            const mobilePayments = this.recentPayments.filter(p => 
                p.payment_method === 'mobile' || p.payment_method?.toLowerCase().includes('mobile')
            ).length;
            
            this.updateElement('card-payments', cardPayments);
            this.updateElement('mobile-payments', mobilePayments);
        } else {
            this.updateElement('card-payments', 0);
            this.updateElement('mobile-payments', 0);
        }
    }

    renderRecentPayments() {
        const container = document.getElementById('recent-transactions');
        if (!container) return;
        
        if (!this.recentPayments || this.recentPayments.length === 0) {
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
        
        container.innerHTML = this.recentPayments.map(payment => {
            const time = payment.processed_at ? 
                new Date(payment.processed_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 
                'N/A';
            
            const tableNum = payment.table_number || 
                           payment.order?.table?.table_number || 
                           payment.order_details?.table_number || 
                           'N/A';
            
            const orderNum = payment.order_number || 
                           payment.order?.order_number || 
                           payment.order_details?.order_number || 
                           'N/A';
            
            const amount = payment.amount ? parseFloat(payment.amount).toFixed(2) : '0.00';
            const method = payment.payment_method || 'unknown';
            
            return `
                <tr class="border-b border-gray-200 hover:bg-gray-50">
                    <td class="px-4 py-3 text-sm">${time}</td>
                    <td class="px-4 py-3 text-sm font-medium">${tableNum}</td>
                    <td class="px-4 py-3 text-sm">${orderNum}</td>
                    <td class="px-4 py-3 font-medium">$${amount}</td>
                    <td class="px-4 py-3">
                        <span class="px-2 py-1 text-xs font-medium rounded-full ${this.getPaymentMethodClass(method)}">
                            ${method.toUpperCase()}
                        </span>
                    </td>
                    <td class="px-4 py-3">
                        <span class="px-2 py-1 text-xs font-medium rounded-full ${payment.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}">
                            ${payment.status || 'pending'}
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // ADD MISSING HELPER METHODS:

    getPaymentMethodClass(method) {
        const methodLower = method.toLowerCase();
        const classes = {
            'cash': 'bg-green-100 text-green-800',
            'cbe': 'bg-blue-100 text-blue-800',
            'telebirr': 'bg-purple-100 text-purple-800',
            'card': 'bg-orange-100 text-orange-800',
            'mobile': 'bg-indigo-100 text-indigo-800',
            'pending': 'bg-gray-100 text-gray-800'
        };
        
        for (const [key, value] of Object.entries(classes)) {
            if (methodLower.includes(key)) {
                return value;
            }
        }
        
        return 'bg-gray-100 text-gray-800';
    }

    calculateChange() {
        if (!this.selectedOrder) return;
        
        const amountInput = document.getElementById('amount-received');
        const changeContainer = document.getElementById('change-container');
        const changeAmount = document.getElementById('change-amount');
        
        if (!amountInput || !changeContainer || !changeAmount) return;
        
        const amountPaid = parseFloat(amountInput.value) || 0;
        const orderTotal = parseFloat(this.selectedOrder.total_amount) || 0;
        
        if (amountPaid >= orderTotal) {
            const change = amountPaid - orderTotal;
            changeAmount.textContent = `$${change.toFixed(2)}`;
            changeContainer.classList.remove('hidden');
        } else {
            changeContainer.classList.add('hidden');
        }
    }

    async processSelectedPayment() {
        if (!this.selectedOrder) {
            this.showToast('Please select an order first', 'error');
            return;
        }
        
        // Get selected payment method
        const activeMethod = document.querySelector('.payment-method-btn.active');
        if (!activeMethod) {
            this.showToast('Please select a payment method', 'error');
            return;
        }
        
        const paymentMethod = activeMethod.dataset.method;
        const amountInput = document.getElementById('amount-received');
        const amount = parseFloat(amountInput.value) || this.selectedOrder.total_amount;
        
        // Validate amount for cash payments
        if (paymentMethod === 'cash' && amount < this.selectedOrder.total_amount) {
            this.showToast(`Amount paid ($${amount.toFixed(2)}) is less than total ($${this.selectedOrder.total_amount})`, 'error');
            return;
        }
        
        if (!confirm(`Process ${paymentMethod.toUpperCase()} payment of $${amount.toFixed(2)} for Order #${this.selectedOrder.order_number || this.selectedOrder.id}?`)) {
            return;
        }
        
        try {
            this.showToast('Processing payment...', 'info');
            
            const response = await fetch('/api/payments/cashier/process-payment/', {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({
                    order_id: this.selectedOrder.id,
                    payment_method: paymentMethod,
                    amount: amount,
                    cash_received: paymentMethod === 'cash' ? amount : null,
                    customer_name: this.selectedOrder.customer_name || 'Guest',
                    notes: `Processed by cashier ${this.user?.username || 'system'}`
                })
            });
            
            await this.handlePaymentResponse(response);
            
        } catch (error) {
            console.error('Payment processing error:', error);
            this.showToast('❌ Failed to process payment. Please try again.', 'error');
        }
    }

    async handlePaymentResponse(response) {
        // Check content type
        const contentType = response.headers.get('content-type');
        
        if (!contentType || !contentType.includes('application/json')) {
            // Try to read as text to see what we got
            const text = await response.text();
            console.error('Non-JSON response:', text.substring(0, 200));
            
            this.showToast('❌ Server returned invalid response format', 'error');
            return;
        }
        
        try {
            const result = await response.json();
            console.log('Payment response:', result);
            
            if (response.ok) {
                this.showToast(`✅ Payment processed successfully!`, 'success');
                
                // Reset selection
                this.selectedOrder = null;
                const container = document.getElementById('selected-bill-container');
                const interfaceDiv = document.getElementById('payment-interface');
                if (container && interfaceDiv) {
                    container.classList.remove('hidden');
                    interfaceDiv.classList.add('hidden');
                }
                
                // Disable process button
                const processBtn = document.getElementById('process-payment-btn');
                if (processBtn) {
                    processBtn.disabled = true;
                }
                
                // Reload dashboard after delay
                setTimeout(() => this.loadDashboardData(), 1000);
            } else {
                this.showToast(`❌ Payment failed: ${result.error || result.detail || result.message || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('JSON parsing error:', error);
            this.showToast('❌ Failed to parse server response', 'error');
        }
    }

    printDailyReport() {
        const printWindow = window.open('', '_blank');
        const today = new Date().toLocaleDateString();
        
        let reportHTML = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Daily Report - ${today}</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1 { color: #333; }
                    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f4f4f4; }
                    .total { font-weight: bold; color: #d32f2f; }
                </style>
            </head>
            <body>
                <h1>Daily Sales Report - ${today}</h1>
                <p>Generated: ${new Date().toLocaleString()}</p>
                
                <h2>Summary</h2>
                <p>Total Revenue: $${this.todaySummary.revenue || 0}</p>
                <p>Total Transactions: ${this.todaySummary.transactions || 0}</p>
                <p>Average Transaction: $${(this.todaySummary.average_transaction || 0).toFixed(2)}</p>
                
                <h2>Recent Transactions (${this.recentPayments.length})</h2>
                <table>
                    <tr>
                        <th>Time</th>
                        <th>Table</th>
                        <th>Order #</th>
                        <th>Amount</th>
                        <th>Method</th>
                        <th>Status</th>
                    </tr>
        `;
        
        this.recentPayments.forEach(payment => {
            const time = payment.processed_at ? 
                new Date(payment.processed_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'N/A';
            
            reportHTML += `
                <tr>
                    <td>${time}</td>
                    <td>${payment.table_number || payment.order?.table?.table_number || 'N/A'}</td>
                    <td>${payment.order_number || payment.order?.order_number || 'N/A'}</td>
                    <td>$${payment.amount || 0}</td>
                    <td>${payment.payment_method || 'Unknown'}</td>
                    <td>${payment.status || 'Unknown'}</td>
                </tr>
            `;
        });
        
        reportHTML += `
                </table>
                <p class="total">End of Report</p>
            </body>
            </html>
        `;
        
        printWindow.document.write(reportHTML);
        printWindow.document.close();
        printWindow.print();
    }

    // UTILITY METHODS:

    getCsrfToken() {
        // Try multiple methods to get CSRF token
        let csrfToken = null;
        
        // Method 1: From meta tag
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            csrfToken = metaTag.getAttribute('content');
        }
        
        // Method 2: From cookie
        if (!csrfToken) {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const trimmed = cookie.trim();
                if (trimmed.startsWith('csrftoken=')) {
                    csrfToken = trimmed.substring('csrftoken='.length);
                    break;
                }
            }
        }
        
        // Method 3: From Django template variable (if available)
        if (!csrfToken && window.CSRF_TOKEN) {
            csrfToken = window.CSRF_TOKEN;
        }
        
        return csrfToken;
    }

    getAuthHeaders(contentType = 'application/json') {
        const headers = {
            'Content-Type': contentType
        };
        
        // Add JWT token
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        // Add CSRF token
        const csrfToken = this.getCsrfToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        return headers;
    }

    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = content;
        }
    }

    showToast(message, type = 'info') {
        // Create toast container if it doesn't exist
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} 
                   ${type === 'success' ? 'text-green-500' : type === 'error' ? 'text-red-500' : 'text-blue-500'} mr-3"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Add to container
        container.appendChild(toast);
        
        // Remove after 3 seconds
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    startPolling() {
        console.log('🔄 Starting polling...');
        this.pollingIntervalId = setInterval(() => {
            this.loadDashboardData();
        }, this.pollingInterval);
    }

    stopPolling() {
        if (this.pollingIntervalId) {
            clearInterval(this.pollingIntervalId);
            console.log('🛑 Polling stopped');
        }
    }
}

// Initialize only once when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (!window.cashierDashboard) {
        window.cashierDashboard = new IndustrialCashierDashboard();
    }
});

// Make functions globally accessible
window.selectOrder = (orderId) => {
    if (window.cashierDashboard) {
        window.cashierDashboard.selectOrder(orderId);
    }
};