// static/js/profit/profit-intelligence.js - ENHANCED VERSION
class ProfitDashboard {
    constructor(config) {
        // Configuration
        this.apiBase = config.apiBase;
        this.userRole = config.userRole;
        this.managerScope = config.managerScope;
        this.restaurantId = config.restaurantId;
        this.branchId = config.branchId;
        this.accessibleBranches = config.accessibleBranches || [];
        
        // State
        this.currentView = this.managerScope === 'restaurant' ? 'restaurant' : 'branch';
        this.selectedBranchId = this.branchId || (this.accessibleBranches[0]?.id || null);
        this.currentPeriod = 'today';
        
        // Charts
        this.profitTrendChart = null;
        this.topItemsChart = null;
        
        // Initialize
        this.init();
    }

    init() {
        console.log('ProfitDashboard initialized with config:', {
            apiBase: this.apiBase,
            userRole: this.userRole,
            restaurantId: this.restaurantId
        });
        
        // Load dashboard data
        this.loadDashboard();
        
        // Update last updated time
        this.updateLastUpdated();
    }

    async loadDashboard() {
        this.showLoading(true);
        
        try {
            console.log('Loading dashboard data...');
            
            // Build API URL
            const url = new URL(this.apiBase, window.location.origin);
            url.searchParams.set('view_level', this.currentView);
            
            if (this.currentView === 'branch' && this.selectedBranchId) {
                url.searchParams.set('branch_id', this.selectedBranchId);
            }
            
            console.log('Fetching from:', url.toString());
            
            const response = await fetch(url.toString(), {
                headers: this.getAuthHeaders(),
                credentials: 'include' // Include cookies for session auth
            });
            
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('API response:', data);
            
            if (data.success) {
                this.updateDashboard(data);
                this.showToast('Dashboard updated successfully', 'success');
            } else {
                throw new Error(data.error || 'API returned unsuccessful');
            }
            
        } catch (error) {
            console.error('Dashboard load error:', error);
            this.showToast(`Error: ${error.message}`, 'error');
            this.showFallbackData();
        } finally {
            this.showLoading(false);
            this.updateLastUpdated();
        }
    }

    updateDashboard(data) {
        console.log('Updating dashboard with data:', data);
        
        // Update KPI cards
        if (data.today) {
            // Helper to try multiple possible keys returned by different API shapes
            const pick = (obj, keys) => {
                for (let k of keys) {
                    if (obj && typeof obj[k] !== 'undefined' && obj[k] !== null) return obj[k];
                }
                return 0;
            };

            const revenue = pick(data.today, ['revenue', 'total_revenue']);
            const netProfit = pick(data.today, ['net_profit', 'profit', 'total_profit']);
            const profitMargin = pick(data.today, ['profit_margin', 'margin']);
            const costOfGoods = pick(data.today, ['cost_of_goods', 'ingredient_cost']);
            const wasteCost = pick(data.today, ['waste_cost', 'waste_cost']);
            const orderCount = pick(data.today, ['order_count', 'orders']);
            const avgOrderValue = pick(data.today, ['average_order_value', 'avg_order_value']) || (orderCount > 0 ? revenue / orderCount : 0);

            this.updateElement('today-revenue', `$${this.formatCurrency(revenue || 0)}`);
            this.updateElement('net-profit', `$${this.formatCurrency(netProfit || 0)}`);
            this.updateElement('profit-margin', `${this.formatPercent(profitMargin || 0)}%`);
            this.updateElement('ingredient-cost', `$${this.formatCurrency(costOfGoods || 0)}`);
            this.updateElement('waste-cost', `$${this.formatCurrency(wasteCost || 0)}`);
            this.updateElement('total-cost', `$${this.formatCurrency((costOfGoods || 0) + (wasteCost || 0))}`);
            this.updateElement('today-orders', orderCount || 0);
            this.updateElement('avg-order-value', `$${this.formatCurrency(avgOrderValue || 0)}`);

            // Update revenue change (compat: daily_change or trend percentage)
            const change = (data.daily_change && data.daily_change.revenue_change) || (data.trend && data.trend.trend_percentage) || 0;
            const changeElement = document.getElementById('revenue-change');
            if (changeElement) {
                if (change > 0) {
                    changeElement.innerHTML = `<i class="fas fa-arrow-up mr-1"></i>${Math.abs(change).toFixed(1)}%`;
                    changeElement.className = 'text-green-600 font-medium';
                } else if (change < 0) {
                    changeElement.innerHTML = `<i class="fas fa-arrow-down mr-1"></i>${Math.abs(change).toFixed(1)}%`;
                    changeElement.className = 'text-red-600 font-medium';
                } else {
                    changeElement.innerHTML = `<i class="fas fa-minus mr-1"></i>0%`;
                    changeElement.className = 'text-gray-600 font-medium';
                }
            }

            // Update margin bar
            this.updateMarginBar(profitMargin || 0);
        }
        
        // Update issues
        if (data.issues) {
            const lossMakers = data.issues.loss_makers || data.issues.loss_makers_count || 0;
            const lowMargin = data.issues.low_margin_items || data.issues.low_margin_count || 0;
            const totalIssues = lossMakers + lowMargin;
            
            this.updateElement('issues-count', totalIssues);
            this.updateElement('loss-makers', lossMakers);
            this.updateElement('low-margin', lowMargin);
            
            // Update issues table if data available
            if (data.recent_issues && Array.isArray(data.recent_issues)) {
                this.updateIssuesTable(data.recent_issues);
            }
        }
        
        // Update suggestions
        if (data.issues?.price_suggestions) {
            this.updateSuggestions(data.issues.price_suggestions);
            this.updateElement('suggestions-count', data.issues.price_suggestions.length || 0);
        }
        
        // Update charts
        if (data.daily_trend) {
            this.createProfitTrendChart(data.daily_trend);
        }
        
        // Load top items if not in data
        if (!data.top_items) {
            this.loadTopItems();
        }
        
        // Update view indicator
        this.updateViewIndicator();
    }

    updateMarginBar(margin) {
        const marginBar = document.getElementById('margin-bar');
        const marginStatus = document.getElementById('margin-status');
        
        if (!marginBar || !marginStatus) return;
        
        let width = 0;
        let color = 'bg-gray-300';
        let status = 'No Data';
        let statusColor = 'text-gray-600';
        
        if (margin >= 40) {
            width = 100;
            color = 'bg-gradient-to-r from-green-400 to-green-600';
            status = 'Excellent';
            statusColor = 'text-green-600';
        } else if (margin >= 30) {
            width = 75;
            color = 'bg-gradient-to-r from-green-300 to-green-500';
            status = 'Good';
            statusColor = 'text-green-500';
        } else if (margin >= 20) {
            width = 50;
            color = 'bg-gradient-to-r from-yellow-400 to-yellow-600';
            status = 'Fair';
            statusColor = 'text-yellow-600';
        } else if (margin >= 10) {
            width = 25;
            color = 'bg-gradient-to-r from-orange-400 to-orange-600';
            status = 'Low';
            statusColor = 'text-orange-600';
        } else if (margin > 0) {
            width = 10;
            color = 'bg-gradient-to-r from-red-400 to-red-600';
            status = 'Critical';
            statusColor = 'text-red-600';
        }
        
        marginBar.className = `${color} h-2 rounded-full transition-all duration-500`;
        marginBar.style.width = `${width}%`;
        marginStatus.textContent = status;
        marginStatus.className = `text-xs font-medium ${statusColor}`;
    }

    updateIssuesTable(issues) {
        const container = document.getElementById('issues-table-body');
        if (!container) return;
        
        if (!issues || issues.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="4" class="px-6 py-8 text-center">
                        <div class="flex flex-col items-center justify-center py-4">
                            <div class="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mb-3">
                                <i class="fas fa-check-circle text-green-600 text-2xl"></i>
                            </div>
                            <p class="text-gray-500 font-medium">No profit issues found!</p>
                            <p class="text-sm text-gray-400 mt-1">All menu items are performing well.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        const rows = issues.slice(0, 5).map(item => `
            <tr class="hover:bg-gray-50 transition-colors">
                <td class="px-6 py-4">
                    <div class="flex items-center">
                        <div class="w-8 h-8 bg-gray-100 rounded mr-3 flex items-center justify-center">
                            <i class="fas fa-utensils text-gray-500"></i>
                        </div>
                        <div>
                            <div class="font-medium text-gray-900">${item.name || 'Unknown Item'}</div>
                            <div class="text-xs text-gray-500">${item.category || ''}</div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4">
                    <span class="px-3 py-1 text-xs font-medium rounded-full ${item.margin <= 0 ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}">
                        ${this.formatPercent(item.margin || 0)}%
                    </span>
                </td>
                <td class="px-6 py-4">
                    ${item.margin <= 0 ? 
                        '<span class="inline-flex items-center"><div class="w-2 h-2 bg-red-500 rounded-full mr-2"></div><span class="text-red-600 font-medium">Loss Maker</span></span>' : 
                        '<span class="inline-flex items-center"><div class="w-2 h-2 bg-yellow-500 rounded-full mr-2"></div><span class="text-yellow-600 font-medium">Low Margin</span></span>'}
                </td>
                <td class="px-6 py-4">
                    <button onclick="window.location.href='/profit-intelligence/menu-analysis/#item-${item.id}'" 
                            class="text-red-600 hover:text-red-900 text-sm font-medium flex items-center">
                        <i class="fas fa-chart-line mr-2"></i> Analyze
                    </button>
                </td>
            </tr>
        `).join('');
        
        container.innerHTML = rows;
    }

    updateSuggestions(suggestions) {
        const container = document.getElementById('suggestions-container');
        if (!container) return;
        
        if (!suggestions || suggestions.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8">
                    <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-check-circle text-green-600 text-2xl"></i>
                    </div>
                    <p class="text-gray-500 font-medium">No suggestions needed</p>
                    <p class="text-sm text-gray-400 mt-1">Your menu is well-optimized for profit.</p>
                </div>
            `;
            return;
        }
        
        const suggestionsHtml = suggestions.slice(0, 3).map(suggestion => `
            <div class="mb-4 p-4 bg-gradient-to-r from-blue-50 to-blue-100 border border-blue-200 rounded-lg hover:border-blue-300 transition-colors">
                <div class="flex items-start">
                    <div class="flex-shrink-0">
                        <div class="w-10 h-10 bg-blue-200 rounded-full flex items-center justify-center">
                            <i class="fas fa-lightbulb text-blue-600"></i>
                        </div>
                    </div>
                    <div class="ml-3 flex-1">
                        <h4 class="text-sm font-semibold text-blue-800">Increase Profit Margin</h4>
                        <div class="mt-2 space-y-2">
                            <div class="flex justify-between items-center">
                                <span class="text-sm text-gray-700">${suggestion.menu_item_name || 'Item'}</span>
                                <span class="text-sm font-bold text-blue-700">+${this.formatPercent(suggestion.expected_margin_impact || 0)}%</span>
                            </div>
                            <div class="flex justify-between items-center text-sm">
                                <span class="text-gray-600">Current: <span class="font-medium">$${this.formatCurrency(suggestion.current_price || 0)}</span></span>
                                <span class="text-gray-600">Suggested: <span class="font-bold text-green-700">$${this.formatCurrency(suggestion.suggested_price || 0)}</span></span>
                            </div>
                            <div class="text-xs text-gray-500 mt-1">
                                Expected profit increase: <span class="font-medium">$${this.formatCurrency(suggestion.revenue_impact || 0)}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = suggestionsHtml;
    }

    async loadProfitTrend(days) {
        try {
            const url = `/profit-intelligence/api/daily/?days=${days}`;
            const response = await fetch(url, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to load trend data');
            
            const data = await response.json();
            if (data.success) {
                this.createProfitTrendChart(data.daily_data || []);
                this.updateElement('trend-period', `Last ${days} days`);
                
                if (data.summary) {
                    const trendText = data.summary.trend_direction === 'up' ? 'increasing' : 
                                    data.summary.trend_direction === 'down' ? 'decreasing' : 'stable';
                    this.updateElement('trend-summary', `Profit trend is ${trendText}`);
                }
            }
        } catch (error) {
            console.error('Error loading profit trend:', error);
            this.showToast('Failed to load trend data', 'error');
        }
    }

    createProfitTrendChart(dailyData) {
        const ctx = document.getElementById('profitTrendChart')?.getContext('2d');
        if (!ctx || !dailyData || dailyData.length === 0) return;
        
        // Destroy existing chart
        if (this.profitTrendChart) {
            this.profitTrendChart.destroy();
        }
        
        const labels = dailyData.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        });
        
        const profitData = dailyData.map(d => d.profit || 0);
        
        this.profitTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily Profit',
                    data: profitData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `$${context.parsed.y.toFixed(2)} profit`
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
                            callback: (value) => `$${value}`
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                }
            }
        });
    }

    async loadTopItems() {
        try {
            const response = await fetch('/profit-intelligence/api/menu-items/?limit=5', {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) return;
            
            const data = await response.json();
            if (data.success && data.items) {
                this.createTopItemsChart(data.items);
                this.updateElement('top-items-summary', `Top ${data.items.length} items by profit`);
            }
        } catch (error) {
            console.error('Error loading top items:', error);
        }
    }

    createTopItemsChart(items) {
        const ctx = document.getElementById('topItemsChart')?.getContext('2d');
        if (!ctx || !items || items.length === 0) return;
        
        if (this.topItemsChart) {
            this.topItemsChart.destroy();
        }
        
        const labels = items.slice(0, 5).map(item => 
            item.name.length > 12 ? item.name.substring(0, 12) + '...' : item.name
        );
        
        const profitData = items.slice(0, 5).map(item => item.profit || 0);
        const colors = ['#dc2626', '#ea580c', '#d97706', '#059669', '#2563eb'];
        
        this.topItemsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Profit ($)',
                    data: profitData,
                    backgroundColor: colors,
                    borderColor: colors.map(color => color + 'CC'),
                    borderWidth: 1,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `$${context.parsed.y.toFixed(2)} profit`
                        }
                    }
                },
                scales: {
                    x: { 
                        grid: { display: false },
                        ticks: { 
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => `$${value}`
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                }
            }
        });
    }

    updateViewIndicator() {
        const indicator = document.getElementById('view-indicator');
        if (!indicator) return;
        
        let text = `<i class="fas fa-building mr-1"></i> ${this.currentView === 'restaurant' ? 'All Branches' : this.getSelectedBranchName()}`;
        indicator.innerHTML = text;
    }

    getSelectedBranchName() {
        if (!this.selectedBranchId && this.accessibleBranches.length > 0) {
            return this.accessibleBranches[0].name;
        }
        
        const branch = this.accessibleBranches.find(b => b.id == this.selectedBranchId);
        return branch ? branch.name : 'Selected Branch';
    }

    getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };

        // Include JWT token if available
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }

        // Include CSRF token for Django session auth
        const csrfToken = this.getCsrfToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        return headers;
    }

    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return null;
    }

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

    showLoading(show) {
        // You can implement a loading spinner if needed
        if (show) {
            console.log('Loading...');
        }
    }

    showToast(message, type = 'info') {
        if (typeof Swal !== 'undefined') {
            const Toast = Swal.mixin({
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true,
                didOpen: (toast) => {
                    toast.addEventListener('mouseenter', Swal.stopTimer);
                    toast.addEventListener('mouseleave', Swal.resumeTimer);
                }
            });

            Toast.fire({
                icon: type,
                title: message
            });
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    showFallbackData() {
        // Show fallback data when API fails
        this.updateElement('today-revenue', '$125.50');
        this.updateElement('net-profit', '$75.50');
        this.updateElement('profit-margin', '60.2%');
        this.updateElement('today-orders', '1');
        this.showToast('Showing sample data. Check API connection.', 'warning');
    }

    updateLastUpdated() {
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        this.updateElement('last-updated', `${timeString}`);
    }

    async loadDateRange(startDate, endDate) {
        try {
            const params = new URLSearchParams({
                start_date: startDate.toISOString().split('T')[0],
                end_date: endDate.toISOString().split('T')[0]
            });
            
            const response = await fetch(`/profit-intelligence/api/daily/?${params}`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to load date range data');
            
            const data = await response.json();
            if (data.success) {
                this.updateDashboardWithDateRange(data);
                this.showToast(`Loaded data for ${params.get('start_date')} to ${params.get('end_date')}`, 'success');
            }
        } catch (error) {
            console.error('Error loading date range:', error);
            this.showToast('Failed to load date range data', 'error');
        }
    }

    updateDashboardWithDateRange(data) {
        // Custom implementation for date range view
        console.log('Date range data loaded:', data);
        // Update your dashboard with date range specific data
        if (data.daily_data && data.daily_data.length > 0) {
            this.createProfitTrendChart(data.daily_data);
            this.updateElement('data-coverage', `${data.daily_data.length} days`);
        }
    }
}

// Make available globally
window.ProfitDashboard = ProfitDashboard;

console.log('Profit Intelligence Dashboard JavaScript loaded successfully');