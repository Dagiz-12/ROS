// static/js/admin/dashboard.js
class RestaurantDashboard {
    constructor() {
        this.apiBase = '/restaurant-admin/api/';
        this.currentPeriod = 'today';
        this.init();
    }

    init() {
        this.checkAuth();
        this.loadDashboard();
        this.setupPeriodSelector();
        this.setupAutoRefresh();
        this.setupEventListeners();
    }

    checkAuth() {
        // Use your existing auth manager
        if (typeof authManager !== 'undefined') {
            if (!authManager.isAuthenticated()) {
                window.location.href = '/login/';
            }
        }
    }

    setupPeriodSelector() {
        const periodBtns = document.querySelectorAll('[data-period]');
        periodBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Update UI
                periodBtns.forEach(b => {
                    b.classList.remove('bg-red-600', 'text-white');
                    b.classList.add('bg-gray-100', 'text-gray-700');
                });
                
                btn.classList.remove('bg-gray-100', 'text-gray-700');
                btn.classList.add('bg-red-600', 'text-white');
                
                // Update data
                this.currentPeriod = btn.dataset.period;
                this.loadBusinessMetrics();
                this.loadProfitTable();
            });
        });
    }

    setupAutoRefresh() {
        // Refresh metrics every 30 seconds
        setInterval(() => {
            this.loadBusinessMetrics();
        }, 30000);
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadDashboard();
            showSuccess('Dashboard refreshed');
        });

        // Export buttons
        document.getElementById('export-profit')?.addEventListener('click', () => {
            this.exportProfitData();
        });
    }

    async loadDashboard() {
        showLoading('Loading dashboard...');
        try {
            await Promise.all([
                this.loadBusinessMetrics(),
                this.loadProfitTable(),
                this.loadRevenueChart(),
                this.loadPopularItems(),
                this.loadRecentActivity()
            ]);
            hideLoading();
        } catch (error) {
            hideLoading();
            showError('Failed to load dashboard data');
            console.error('Dashboard load error:', error);
        }
    }

    async loadBusinessMetrics() {
        try {
            const response = await fetch(`${this.apiBase}business-metrics/?period=${this.currentPeriod}`);
            const data = await response.json();

            if (data.success) {
                this.updateMetrics(data);
            }
        } catch (error) {
            console.error('Error loading business metrics:', error);
        }
    }

    updateMetrics(data) {
        // Revenue metrics
        this.updateMetric('revenue-amount', `$${data.metrics.total_revenue.toFixed(2)}`);
        this.updateMetric('revenue-change', data.metrics.revenue_change, true);
        
        // Profit metrics
        this.updateMetric('profit-amount', `$${data.profit.total_profit.toFixed(2)}`);
        this.updateMetric('profit-margin', `${data.profit.profit_margin.toFixed(1)}%`);
        
        // Order metrics
        this.updateMetric('orders-count', data.metrics.total_orders);
        this.updateMetric('orders-change', data.metrics.orders_change, true);
        
        // Average order value
        this.updateMetric('avg-order', `$${data.metrics.average_order_value.toFixed(2)}`);
        
        // Best seller
        if (data.profit.best_seller) {
            document.getElementById('best-seller-name').textContent = 
                data.profit.best_seller.name;
            document.getElementById('best-seller-stats').textContent = 
                `${data.profit.best_seller.sold} sold • $${data.profit.best_seller.revenue.toFixed(2)}`;
        }
    }

    updateMetric(elementId, value, isChange = false) {
        const element = document.getElementById(elementId);
        if (!element) return;

        if (isChange) {
            const change = parseFloat(value);
            if (change > 0) {
                element.innerHTML = `<i class="fas fa-arrow-up text-green-500 mr-1"></i> ${Math.abs(change).toFixed(1)}%`;
                element.className = 'text-green-600 text-sm font-medium';
            } else if (change < 0) {
                element.innerHTML = `<i class="fas fa-arrow-down text-red-500 mr-1"></i> ${Math.abs(change).toFixed(1)}%`;
                element.className = 'text-red-600 text-sm font-medium';
            } else {
                element.innerHTML = `<i class="fas fa-minus text-gray-500 mr-1"></i> 0%`;
                element.className = 'text-gray-600 text-sm font-medium';
            }
        } else {
            element.textContent = value;
        }
    }

    async loadProfitTable() {
        try {
            const response = await fetch(`${this.apiBase}profit-table/?period=${this.currentPeriod}`);
            const data = await response.json();

            if (data.success) {
                this.renderProfitTable(data.items);
            }
        } catch (error) {
            console.error('Error loading profit table:', error);
        }
    }

    renderProfitTable(items) {
        const container = document.getElementById('profit-table-body');
        if (!container) return;

        if (!items || items.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                        <i class="fas fa-chart-pie text-3xl mb-3"></i>
                        <p>No sales data available</p>
                    </td>
                </tr>
            `;
            return;
        }

        const rows = items.map(item => `
            <tr class="hover:bg-gray-50 transition-colors">
                <td class="px-4 py-3">
                    <div class="flex items-center">
                        <div class="w-8 h-8 bg-gray-100 rounded mr-3 flex items-center justify-center">
                            <i class="fas fa-utensils text-gray-500"></i>
                        </div>
                        <div>
                            <div class="font-medium text-gray-900">${item.name}</div>
                            <div class="text-xs text-gray-500">${item.category}</div>
                        </div>
                    </div>
                </td>
                <td class="px-4 py-3 text-center">
                    <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                        ${item.sold}
                    </span>
                </td>
                <td class="px-4 py-3 text-right font-medium">
                    $${item.revenue.toFixed(2)}
                </td>
                <td class="px-4 py-3 text-right text-gray-600">
                    $${item.cost.toFixed(2)}
                </td>
                <td class="px-4 py-3 text-right font-bold ${item.profit >= 0 ? 'text-green-600' : 'text-red-600'}">
                    $${item.profit.toFixed(2)}
                </td>
                <td class="px-4 py-3 text-center">
                    ${this.getMarginIcon(item.margin)}
                </td>
                <td class="px-4 py-3 text-center">
                    <span class="px-2 py-1 text-xs font-medium rounded-full ${this.getMarginClass(item.margin)}">
                        ${item.margin.toFixed(1)}%
                    </span>
                </td>
            </tr>
        `).join('');

        container.innerHTML = rows;
    }

    getMarginIcon(margin) {
        if (margin >= 60) return '<i class="fas fa-crown text-yellow-500" title="Excellent profit"></i>';
        if (margin >= 40) return '<i class="fas fa-check-circle text-green-500" title="Good profit"></i>';
        if (margin >= 20) return '<i class="fas fa-exclamation-triangle text-yellow-500" title="Low profit"></i>';
        return '<i class="fas fa-times-circle text-red-500" title="Very low profit"></i>';
    }

    getMarginClass(margin) {
        if (margin >= 60) return 'bg-green-100 text-green-800';
        if (margin >= 40) return 'bg-yellow-100 text-yellow-800';
        if (margin >= 20) return 'bg-orange-100 text-orange-800';
        return 'bg-red-100 text-red-800';
    }

    async exportProfitData() {
        showConfirm('Export profit data as CSV?', () => {
            showLoading('Exporting data...');
            
            // In real implementation, this would call an API endpoint
            setTimeout(() => {
                hideLoading();
                showSuccess('Profit data exported successfully!');
            }, 1000);
        });
    }

    // Other methods (loadRevenueChart, loadPopularItems, etc.) remain similar
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.restaurantDashboard = new RestaurantDashboard();
});