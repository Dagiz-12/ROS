// static/js/admin/dashboard.js - UPDATED VERSION

class RestaurantDashboard {
    constructor() {
        this.apiBase = '/profit-intelligence/api/';
        this.currentPeriod = 'today';
        this.trendChart = null;
        this.pollingInterval = null;
        this.init();
    }

    init() {
        this.checkAuth();
        this.loadDashboard();
        this.setupEventListeners();
        this.setupAutoRefresh();
        this.updateLastUpdated();
    }

    checkAuth() {
        if (typeof authManager !== 'undefined') {
            if (!authManager.isAuthenticated()) {
                window.location.href = '/login/';
            }
        }
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadDashboard();
            showToast('Dashboard refreshed', 'success');
        });

        // Period buttons for chart
        document.querySelectorAll('.trend-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.trend-btn').forEach(b => {
                    b.classList.remove('bg-red-600', 'text-white');
                    b.classList.add('bg-gray-100', 'text-gray-700');
                });
                e.target.classList.remove('bg-gray-100', 'text-gray-700');
                e.target.classList.add('bg-red-600', 'text-white');
                const days = parseInt(e.target.dataset.days) || 7;
                this.loadTrend(days);
            });
        });
    }

    setupAutoRefresh() {
        // Refresh every 30 seconds
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        this.pollingInterval = setInterval(() => {
            this.loadKPIs();
            this.loadAlerts();
            this.loadTopItems();
        }, 30000);
    }

    updateLastUpdated() {
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const element = document.getElementById('last-updated');
        if (element) {
            element.innerHTML = `<i class="fas fa-clock mr-1"></i> Updated: ${timeString}`;
        }
    }

    async loadDashboard() {
        this.showLoading(true);
        try {
            await Promise.all([
                this.loadKPIs(),
                this.loadAlerts(),
                this.loadTrend(7),
                this.loadTopItems(),
                this.loadDailyInsight()
            ]);
            this.showLoading(false);
            this.updateLastUpdated();
        } catch (error) {
            this.showLoading(false);
            console.error('Dashboard load error:', error);
            showToast('Failed to load dashboard data', 'error');
        }
    }

    // ==================== KPIs ====================
    async loadKPIs() {
        try {
            const response = await fetch(`${this.apiBase}business-metrics/?period=today`);
            if (!response.ok) throw new Error('Failed to load KPIs');
            
            const data = await response.json();
            if (data.success) {
                this.updateKPIs(data);
            }
        } catch (error) {
            console.error('KPI load error:', error);
            // Show fallback data
            this.showFallbackKPIs();
        }
    }

    updateKPIs(data) {
        const metrics = data.metrics || {};
        const profit = data.profit || {};
        
        // === REVENUE ===
        const revenueEl = document.getElementById('kpi-revenue');
        if (revenueEl) revenueEl.textContent = `$${this.formatCurrency(metrics.total_revenue || 0)}`;
        
        const revenueChangeEl = document.getElementById('kpi-revenue-change');
        if (revenueChangeEl) revenueChangeEl.innerHTML = this.formatChange(metrics.revenue_change);
        
        // === ORDERS ===
        const ordersEl = document.getElementById('kpi-total-orders');
        if (ordersEl) ordersEl.textContent = metrics.total_orders || 0;
        
        const ordersChangeEl = document.getElementById('kpi-orders-change');
        if (ordersChangeEl) ordersChangeEl.innerHTML = this.formatChange(metrics.orders_change);
        
        const pendingEl = document.getElementById('kpi-pending-orders');
        if (pendingEl) pendingEl.textContent = metrics.pending_orders || 0;
        
        const completedEl = document.getElementById('kpi-completed-orders');
        if (completedEl) completedEl.textContent = metrics.completed_orders || 0;
        
        // Order count in revenue card
        const orderCountEl = document.getElementById('kpi-orders');
        if (orderCountEl) orderCountEl.textContent = metrics.total_orders || 0;
        
        const avgOrderEl = document.getElementById('kpi-avg-order');
        if (avgOrderEl) avgOrderEl.textContent = `$${this.formatCurrency(metrics.average_order_value || 0)}`;
        
        // === PROFIT ===
        const profitEl = document.getElementById('kpi-profit');
        if (profitEl) profitEl.textContent = `$${this.formatCurrency(profit.total_profit || 0)}`;
        
        const profitMarginEl = document.getElementById('kpi-profit-margin');
        if (profitMarginEl) profitMarginEl.textContent = `${this.formatPercent(profit.profit_margin || 0)}% margin`;
        
        const profitChangeEl = document.getElementById('kpi-profit-change');
        if (profitChangeEl) {
            const change = profit.profit_change || 0;
            if (change > 0) {
                profitChangeEl.innerHTML = `<span class="text-green-600"><i class="fas fa-arrow-up mr-1"></i>${Math.abs(change).toFixed(1)}% vs yesterday</span>`;
            } else if (change < 0) {
                profitChangeEl.innerHTML = `<span class="text-red-600"><i class="fas fa-arrow-down mr-1"></i>${Math.abs(change).toFixed(1)}% vs yesterday</span>`;
            } else {
                profitChangeEl.textContent = 'vs yesterday';
            }
        }
        
        // Profit bar
        const margin = profit.profit_margin || 0;
        const bar = document.getElementById('profit-bar');
        const health = document.getElementById('profit-health');
        if (bar) {
            const width = Math.min(margin * 2, 100);
            bar.style.width = `${width}%`;
            bar.className = `h-1.5 rounded-full transition-all duration-500 ${
                margin >= 40 ? 'bg-gradient-to-r from-green-400 to-green-600' :
                margin >= 30 ? 'bg-gradient-to-r from-green-300 to-green-500' :
                margin >= 20 ? 'bg-gradient-to-r from-yellow-400 to-yellow-600' :
                'bg-gradient-to-r from-red-400 to-red-600'
            }`;
        }
        if (health) {
            health.textContent = margin >= 40 ? 'Excellent' :
                                 margin >= 30 ? 'Good' :
                                 margin >= 20 ? 'Fair' :
                                 'Needs Attention';
        }
        
        // === WASTE ===
        const wasteEl = document.getElementById('kpi-waste');
        if (wasteEl) wasteEl.textContent = `$${this.formatCurrency(profit.waste_cost || 0)}`;
        
        const wastePercentEl = document.getElementById('kpi-waste-percent');
        if (wastePercentEl) wastePercentEl.textContent = `${this.formatPercent(profit.waste_percentage || 0)}%`;
        
        const wasteChangeEl = document.getElementById('kpi-waste-change');
        if (wasteChangeEl) wasteChangeEl.innerHTML = this.formatChange(profit.waste_change);
    }

    showFallbackKPIs() {
        // Set default values when API fails
        const defaults = {
            'kpi-revenue': '$0.00',
            'kpi-revenue-change': this.formatChange(0),
            'kpi-total-orders': '0',
            'kpi-orders-change': this.formatChange(0),
            'kpi-orders': '0',
            'kpi-avg-order': '$0.00',
            'kpi-profit': '$0.00',
            'kpi-profit-margin': '0% margin',
            'kpi-waste': '$0.00',
            'kpi-waste-percent': '0%',
            'kpi-waste-change': this.formatChange(0),
            'kpi-pending-orders': '0',
            'kpi-completed-orders': '0'
        };
        
        Object.keys(defaults).forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                // Use innerHTML for change indicators, textContent for others
                if (id.includes('change') || id.includes('margin')) {
                    el.innerHTML = defaults[id];
                } else {
                    el.textContent = defaults[id];
                }
            }
        });
    }

    // ==================== ALERTS ====================
    // Add to loadAlerts() method - include staff alerts

async loadAlerts() {
    try {
        // Get staff performance alerts
        const staffResponse = await fetch('/api/auth/staff/performance/?period=week', {
            headers: this.getAuthHeaders()
        });
        const staffData = await staffResponse.json();
        
        // Get other alerts
        const alertResponse = await fetch(`${this.apiBase}alerts/?limit=3&unresolved=true`, {
            headers: this.getAuthHeaders()
        });
        const alertData = await alertResponse.json();
        
        // Combine alerts
        let allAlerts = [];
        
        // Staff performance alerts
        if (staffData.success && staffData.staff) {
            const lowPerformers = staffData.staff
                .filter(s => s.performance_score < 40 && s.performance_score > 0)
                .slice(0, 3);
            
            lowPerformers.forEach(staff => {
                allAlerts.push({
                    title: `⚠️ Low Performance: ${staff.full_name || staff.username}`,
                    message: `Performance score is ${staff.performance_score.toFixed(1)}% - needs attention`,
                    severity: 'high',
                    alert_type: 'staff_issue',
                    time: 'Just now',
                    action_url: `/restaurant-admin/staff-analytics/?staff=${staff.id}`
                });
            });
        }
        
        // Add system alerts
        if (alertData.success && alertData.alerts) {
            allAlerts = [...allAlerts, ...alertData.alerts];
        }
        
        // Sort by severity
        const severityOrder = { 'critical': 0, 'high': 1, 'medium': 2, 'low': 3 };
        allAlerts.sort((a, b) => (severityOrder[a.severity] || 4) - (severityOrder[b.severity] || 4));
        
        this.renderAlerts(allAlerts.slice(0, 5));
        
    } catch (error) {
        console.error('Alert load error:', error);
        this.renderAlerts([]);
    }
}

    renderAlerts(alerts) {
        const container = document.getElementById('alerts-container');
        const badge = document.getElementById('alert-count-badge');
        
        if (!container) return;

        if (badge) {
            badge.textContent = alerts.length;
            badge.className = `px-3 py-1 text-sm font-bold rounded-full ${
                alerts.length > 0 ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-600'
            }`;
        }

        if (alerts.length === 0) {
            container.innerHTML = `
                <div class="flex items-center justify-center py-6">
                    <div class="flex items-center space-x-3 text-green-600">
                        <i class="fas fa-check-circle text-xl"></i>
                        <span class="font-medium">All systems clear! No issues require attention.</span>
                    </div>
                </div>
            `;
            return;
        }

        const alertHtml = alerts.map((alert, index) => {
            const icons = {
                'low_margin': 'fa-chart-line',
                'loss_maker': 'fa-times-circle',
                'waste_spike': 'fa-trash-alt',
                'low_stock': 'fa-boxes',
                'staff_issue': 'fa-user-slash',
                'default': 'fa-bell'
            };
            const colors = {
                'critical': 'border-l-4 border-red-500 bg-red-50',
                'high': 'border-l-4 border-orange-500 bg-orange-50',
                'medium': 'border-l-4 border-yellow-500 bg-yellow-50',
                'low': 'border-l-4 border-blue-500 bg-blue-50',
                'default': 'border-l-4 border-gray-300 bg-gray-50'
            };
            
            const icon = icons[alert.alert_type] || icons.default;
            const color = colors[alert.severity] || colors.default;
            
            return `
                <div class="flex items-center justify-between py-3 ${color} px-4 rounded-lg transition hover:shadow-sm">
                    <div class="flex items-center flex-1 min-w-0">
                        <div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 flex-shrink-0 ${
                            alert.severity === 'critical' ? 'bg-red-100 text-red-600' :
                            alert.severity === 'high' ? 'bg-orange-100 text-orange-600' :
                            alert.severity === 'medium' ? 'bg-yellow-100 text-yellow-600' :
                            'bg-blue-100 text-blue-600'
                        }">
                            <i class="fas ${icon}"></i>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="font-medium text-gray-900 truncate">${alert.title || 'Alert'}</div>
                            <div class="text-sm text-gray-600 truncate">${alert.message || ''}</div>
                            <div class="text-xs text-gray-400 mt-0.5">${alert.time || 'Just now'}</div>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2 ml-4 flex-shrink-0">
                        <span class="text-xs font-medium px-2 py-1 rounded-full ${
                            alert.severity === 'critical' ? 'bg-red-100 text-red-800' :
                            alert.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                            alert.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-blue-100 text-blue-800'
                        }">
                            ${alert.severity || 'info'}
                        </span>
                        ${alert.action_url ? `
                            <a href="${alert.action_url}" class="text-sm text-red-600 hover:text-red-700 font-medium">
                                <i class="fas fa-arrow-right"></i>
                            </a>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = alertHtml;
    }

    // ==================== TREND CHART ====================
    async loadTrend(days = 7) {
        try {
            const response = await fetch(`${this.apiBase}daily/?days=${days}`);
            if (!response.ok) throw new Error('Failed to load trend data');
            
            const data = await response.json();
            if (data.success) {
                this.createTrendChart(data.daily_data || [], days);
            }
        } catch (error) {
            console.error('Trend load error:', error);
        }
    }

    createTrendChart(chartData, days) {
        const ctx = document.getElementById('trendChart')?.getContext('2d');
        if (!ctx || !chartData.length) return;

        if (this.trendChart) {
            this.trendChart.destroy();
        }

        const labels = chartData.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        });

        this.trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Revenue',
                        data: chartData.map(d => d.revenue || 0),
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 3,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Profit',
                        data: chartData.map(d => d.profit || 0),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 3,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                label += '$' + context.parsed.y.toFixed(2);
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { maxTicksLimit: 8 }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => '$' + value
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                }
            }
        });
    }

    // ==================== TOP ITEMS ====================
    async loadTopItems() {
        try {
            const response = await fetch(`${this.apiBase}popular-items/?limit=5`);
            if (!response.ok) throw new Error('Failed to load top items');
            
            const data = await response.json();
            if (data.success) {
                this.renderTopItems(data.items || []);
            }
        } catch (error) {
            console.error('Top items load error:', error);
        }
    }

    renderTopItems(items) {
        const container = document.getElementById('top-items-container');
        if (!container) return;

        if (items.length === 0) {
            container.innerHTML = `
                <div class="text-center py-6 text-gray-500">
                    <i class="fas fa-utensils text-2xl mb-2"></i>
                    <p>No sales data available</p>
                </div>
            `;
            return;
        }

        const colors = ['#dc2626', '#ea580c', '#d97706', '#059669', '#2563eb'];
        
        const itemsHtml = items.map((item, index) => `
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div class="flex items-center flex-1 min-w-0">
                    <span class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white mr-3 flex-shrink-0" style="background: ${colors[index % colors.length]}">
                        ${index + 1}
                    </span>
                    ${item.image ? 
                        `<img src="${item.image}" alt="${item.name}" class="w-8 h-8 rounded-lg object-cover mr-3 flex-shrink-0">` :
                        `<div class="w-8 h-8 bg-gray-200 rounded-lg flex items-center justify-center mr-3 flex-shrink-0">
                            <i class="fas fa-utensils text-gray-400"></i>
                        </div>`
                    }
                    <div class="flex-1 min-w-0">
                        <div class="font-medium text-gray-900 truncate">${item.name}</div>
                        <div class="text-sm text-gray-500">${item.category || ''}</div>
                    </div>
                </div>
                <div class="text-right ml-4 flex-shrink-0">
                    <div class="font-bold text-gray-900">$${this.formatCurrency(item.revenue || item.price || 0)}</div>
                    <div class="text-sm text-gray-500">${item.sold || 0} sold</div>
                </div>
            </div>
        `).join('');

        container.innerHTML = itemsHtml;
    }

    // ==================== DAILY INSIGHT ====================
    async loadDailyInsight() {
        try {
            const response = await fetch(`${this.apiBase}daily-insight/`);
            if (!response.ok) throw new Error('Failed to load insight');
            
            const data = await response.json();
            if (data.success) {
                const insightEl = document.getElementById('daily-insight');
                if (insightEl) insightEl.textContent = data.insight || 'No insight available';
                
                const timeEl = document.getElementById('insight-time');
                if (timeEl) timeEl.textContent = data.time || '--';
            }
        } catch (error) {
            console.error('Insight load error:', error);
            const insightEl = document.getElementById('daily-insight');
            if (insightEl) insightEl.textContent = 'Unable to generate insight at this time.';
        }
    }

    // ==================== HELPERS ====================
    updateElement(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    formatCurrency(value) {
        return parseFloat(value).toFixed(2);
    }

    formatPercent(value) {
        return parseFloat(value).toFixed(1);
    }

    formatChange(value) {
        const change = parseFloat(value) || 0;
        if (change > 0) {
            return `<span class="text-green-600"><i class="fas fa-arrow-up mr-1"></i>${Math.abs(change).toFixed(1)}%</span>`;
        } else if (change < 0) {
            return `<span class="text-red-600"><i class="fas fa-arrow-down mr-1"></i>${Math.abs(change).toFixed(1)}%</span>`;
        }
        return `<span class="text-gray-600"><i class="fas fa-minus mr-1"></i>0%</span>`;
    }

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            if (show) {
                overlay.classList.remove('hidden');
            } else {
                overlay.classList.add('hidden');
            }
        }
    }
}

// Make available globally
window.RestaurantDashboard = RestaurantDashboard;

console.log('Executive Dashboard JavaScript loaded successfully');