// static/js/cashier-dashboard-enhanced.js - UPDATED WITH CORRECT ENDPOINTS
class IndustrialCashierDashboard {
    constructor() {
        console.log('🏦 Initializing Industrial Cashier Dashboard...');
        
        this.apiBase = '/api/payments'; // Correct base
        this.tablesApiBase = '/api/tables';
        this.pollingInterval = 15000; // 15 seconds
        this.selectedBill = null;
        this.pendingPayments = [];
        
        this.idempotencyKeys = new Map(); // Prevent duplicate payments
        
        this.init();
    }

    async init() {
        // 1. Check authentication
        if (!await this.checkAuth()) return;
        
        // 2. Setup event listeners
        this.setupEventListeners();
        
        // 3. Load initial data
        await this.loadDashboardData();
        
        // 4. Start polling
        this.startPolling();
        
        console.log('✅ Industrial Cashier Dashboard Ready');
    }

    async checkAuth() {
        const token = localStorage.getItem('access_token');
        const userData = localStorage.getItem('user_data');
        
        if (!token || !userData) {
            window.location.href = '/login/';
            return false;
        }
        
        try {
            this.user = JSON.parse(userData);
            this.token = token;
            
            // Verify cashier role
            const allowedRoles = ['cashier', 'manager', 'admin'];
            if (!allowedRoles.includes(this.user.role)) {
                this.showError('Access denied. Cashier role required.');
                window.location.href = '/login/';
                return false;
            }
            
            return true;
        } catch (error) {
            console.error('Auth error:', error);
            window.location.href = '/login/';
            return false;
        }
    }

    // FIXED: Use correct endpoint from your urls.py
    async loadDashboardData() {
        try {
            console.log('📊 Loading dashboard data...');
            
            // CORRECT ENDPOINT: /api/payments/cashier/dashboard/
            const response = await fetch(`${this.apiBase}/cashier/dashboard/`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.status === 401 || response.status === 403) {
                localStorage.clear();
                window.location.href = '/login/';
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Dashboard load failed`);
            }
            
            const data = await response.json();
            
            // Update dashboard with data
            this.updateDashboardUI(data);
            
        } catch (error) {
            console.error('❌ Dashboard load error:', error);
            this.showError('Failed to load dashboard. Please refresh.');
        }
    }

    updateDashboardUI(data) {
        // Update pending bills
        if (data.pending_orders && data.pending_orders.orders) {
            this.pendingPayments = data.pending_orders.orders;
            this.renderPendingBills();
        }
        
        // Update today's summary
        if (data.today_summary) {
            this.updateElement('today-revenue', `$${data.today_summary.total_amount.toFixed(2)}`);
            this.updateElement('pending-payments', data.pending_orders?.count || 0);
        }
        
        // Update recent transactions
        if (data.recent_transactions) {
            this.renderRecentTransactions(data.recent_transactions);
        }
    }

    // FIXED: Process payment with correct endpoint
    async processPayment(paymentData) {
        try {
            // INDUSTRY STANDARD: Generate idempotency key
            const idempotencyKey = crypto.randomUUID ? crypto.randomUUID() : Date.now().toString();
            
            console.log('💰 Processing payment with idempotency key:', idempotencyKey);
            
            // CORRECT ENDPOINT: /api/payments/ (POST)
            const response = await fetch(`${this.apiBase}/`, {
                method: 'POST',
                headers: {
                    ...this.getAuthHeaders(),
                    'Idempotency-Key': idempotencyKey
                },
                body: JSON.stringify({
                    order: paymentData.orderId,
                    payment_method: paymentData.method,
                    amount: paymentData.amount,
                    customer_name: paymentData.customerName || '',
                    customer_phone: paymentData.customerPhone || '',
                    notes: `Processed by ${this.user.username}`
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Payment failed: HTTP ${response.status}`);
            }
            
            const result = await response.json();
            console.log('✅ Payment processed:', result);
            
            // Handle success
            this.handlePaymentSuccess(result);
            
        } catch (error) {
            console.error('❌ Payment error:', error);
            this.handlePaymentError(error);
        }
    }

    handlePaymentSuccess(result) {
        // 1. Show success message
        this.showToast(`Payment ${result.payment_id} completed successfully!`, 'success');
        
        // 2. Play success sound
        this.playSound('success');
        
        // 3. Generate receipt
        this.generateReceipt(result);
        
        // 4. Refresh dashboard
        setTimeout(() => {
            this.loadDashboardData();
            this.deselectBill();
        }, 2000);
    }

    async generateReceipt(paymentResult) {
        try {
            // CORRECT ENDPOINT: /api/payments/payments/{id}/detailed-receipt/
            const response = await fetch(
                `${this.apiBase}/payments/${paymentResult.payment_id}/detailed-receipt/`,
                {
                    method: 'POST',
                    headers: this.getAuthHeaders()
                }
            );
            
            if (response.ok) {
                const receiptData = await response.json();
                this.showReceiptModal(receiptData);
            }
        } catch (error) {
            console.error('Receipt error:', error);
            // Still show basic receipt
            this.showBasicReceipt(paymentResult);
        }
    }

    // INDUSTRY STANDARD: Play sound feedback
    playSound(type) {
        const sounds = {
            success: 'https://assets.mixkit.co/sfx/preview/mixkit-cash-register-purchase-876.mp3',
            error: 'https://assets.mixkit.co/sfx/preview/mixkit-wrong-answer-fail-notification-946.mp3'
        };
        
        if (sounds[type]) {
            const audio = new Audio(sounds[type]);
            audio.volume = 0.3;
            audio.play().catch(e => console.log('Audio play failed:', e));
        }
    }

    getAuthHeaders() {
        const headers = {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
        
        // Add CSRF token
        const csrfToken = this.getCsrfToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        return headers;
    }

    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // Utility methods...
    showToast(message, type = 'info') {
        // Your existing toast implementation
    }

    showError(message) {
        this.showToast(message, 'error');
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.industrialCashier = new IndustrialCashierDashboard();
});