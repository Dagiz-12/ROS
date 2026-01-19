// static/js/profit/profit-intelligence.js
class ProfitDashboard {
    constructor(config) {
        this.apiBase = config.apiBase.replace(/\/$/, ''); // Remove trailing slash
        this.userRole = config.userRole;
        this.managerScope = config.managerScope;
        this.restaurantId = config.restaurantId;
        this.branchId = config.branchId;
        this.accessibleBranches = config.accessibleBranches || [];
        
        this.currentView = this.managerScope === 'restaurant' ? 'restaurant' : 'branch';
        this.selectedBranchId = this.branchId || (this.accessibleBranches[0]?.id || null);
        
        this.profitTrendChart = null;
        this.topItemsChart = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDatePicker();
        this.setupScopeSelector();
        this.loadDashboard();
        this.setupAutoRefresh();
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadDashboard();
            this.showToast('Dashboard refreshed', 'success');
        });

        // Period buttons
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const period = parseInt(e.target.dataset.period);
                this.loadProfitTrend(period);
                
                // Update button styles
                document.querySelectorAll('.period-btn').forEach(b => {
                    if (parseInt(b.dataset.period) === period) {
                        b.classList.add('bg-red-50', 'text-red-600');
                        b.classList.remove('hover:bg-gray-100');
                    } else {
                        b.classList.remove('bg-red-50', 'text-red-600');
                        b.classList.add('hover:bg-gray-100');
                    }
                });
            });
        });

        // Branch selector
        const branchSelector = document.getElementById('branch-selector');
        if (branchSelector) {
            branchSelector.addEventListener('change', (e) => {
                this.selectedBranchId = e.target.value || null;
                this.loadDashboard();
            });
        }
    }

    setupDatePicker() {
        const picker = document.getElementById('date-range-picker');
        if (!picker) return;

        flatpickr(picker, {
            mode: 'range',
            dateFormat: 'Y-m-d',
            onChange: (selectedDates, dateStr) => {
                if (selectedDates.length === 2) {
                    this.loadDateRange(selectedDates[0], selectedDates[1]);
                    document.getElementById('date-range-display').textContent = dateStr;
                }
            }
        });

        // Button to trigger date picker
        document.getElementById('date-range-btn')?.addEventListener('click', () => {
            picker._flatpickr.open();
        });
    }

    setupScopeSelector() {
        const toggleBtn = document.getElementById('view-toggle-btn');
        if (!toggleBtn) return;

        toggleBtn.addEventListener('click', () => {
            this.currentView = this.currentView === 'branch' ? 'restaurant' : 'branch';
            this.updateViewUI();
            this.loadDashboard();
        });
    }

    updateViewUI() {
        const toggleBtn = document.getElementById('view-toggle-btn');
        const viewIndicator = document.getElementById('view-indicator');
        const branchSelector = document.getElementById('branch-selector');

        if (this.currentView === 'restaurant') {
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="fas fa-store mr-2"></i>Switch to Branch View';
                toggleBtn.className = 'px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center';
            }
            if (viewIndicator) {
                viewIndicator.textContent = 'Viewing All Restaurant Branches';
            }
            if (branchSelector) {
                branchSelector.classList.add('hidden');
            }
        } else {
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="fas fa-building mr-2"></i>Switch to Restaurant View';
                toggleBtn.className = 'px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center';
            }
            if (viewIndicator) {
                const branchName = this.getSelectedBranchName();
                viewIndicator.textContent = `Viewing: ${branchName}`;
            }
            if (branchSelector && this.accessibleBranches.length > 1) {
                branchSelector.classList.remove('hidden');
            }
        }
    }

    getSelectedBranchName() {
        if (!this.selectedBranchId && this.accessibleBranches.length > 0) {
            return this.accessibleBranches[0].name;
        }
        
        const branch = this.accessibleBranches.find(b => b.id == this.selectedBranchId);
        return branch ? branch.name : 'Branch';
    }

    async loadDashboard() {
        this.showLoading(true);
        
        try {
            // Build query parameters
            const params = new URLSearchParams({
                view_level: this.currentView
            });
            
            if (this.currentView === 'branch' && this.selectedBranchId) {
                params.append('branch_id', this.selectedBranchId);
            }
            
            const response = await fetch(`${this.apiBase}?${params}`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.updateDashboard(data);
            } else {
                throw new Error(data.error || 'Failed to load dashboard');
            }
            
        } catch (error) {
            console.error('Dashboard load error:', error);
            this.showToast(`Error: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async loadProfitTrend(days) {
        try {
            const response = await fetch(`/profit-intelligence/api/daily/?days=${days}`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to load trend data');
            
            const data = await response.json();
            if (data.success) {
                this.createProfitTrendChart(data);
            }
        } catch (error) {
            console.error('Error loading profit trend:', error);
            this.showToast('Failed to load trend data', 'error');
        }
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
            }
        } catch (error) {
            console.error('Error loading date range:', error);
            this.showToast('Failed to load date range data', 'error');
        }
    }

    updateDashboard(data) {
        // Update KPI cards
        const today = data.today?.summary;
        if (today) {
            this.updateElement('today-revenue', `$${today.revenue?.toFixed(2) || '0.00'}`);
            this.updateElement('net-profit', `$${today.net_profit?.toFixed(2) || '0.00'}`);
            this.updateElement('profit-margin', `${today.profit_margin?.toFixed(1) || '0.0'}%`);
            this.updateElement('ingredient-cost', `$${today.cost_of_goods?.toFixed(2) || '0.00'}`);
            this.updateElement('waste-cost', `$${today.waste_cost?.toFixed(2) || '0.00'}`);
            this.updateElement('total-cost', `$${today.total_cost?.toFixed(2) || '0.00'}`);
            this.updateElement('today-orders', `${today.order_count || 0} orders`);
            this.updateElement('avg-order-value', `$${today.average_order_value?.toFixed(2) || '0.00'} avg`);
        }

        // Update change indicators
        const change = data.daily_change;
        if (change) {
            const revenueChange = change.percentage_change?.revenue || 0;
            const changeText = revenueChange >= 0 ? 
                `+${revenueChange.toFixed(1)}%` : 
                `${revenueChange.toFixed(1)}%`;
            
            this.updateElement('revenue-change', `vs yesterday: ${changeText}`);
        }

        // Update margin bar
        const marginBar = document.getElementById('margin-bar');
        const marginStatus = document.getElementById('margin-status');
        if (marginBar && marginStatus) {
            const margin = today?.profit_margin || 0;
            let width = Math.min(Math.max(margin, 0), 50);
            marginBar.style.width = `${width * 2}%`;
            
            if (margin >= 30) {
                marginBar.className = 'bg-green-600 h-2 rounded-full';
                marginStatus.textContent = 'Excellent';
                marginStatus.className = 'ml-2 text-sm text-green-600';
            } else if (margin >= 20) {
                marginBar.className = 'bg-yellow-600 h-2 rounded-full';
                marginStatus.textContent = 'Good';
                marginStatus.className = 'ml-2 text-sm text-yellow-600';
            } else if (margin >= 10) {
                marginBar.className = 'bg-orange-600 h-2 rounded-full';
                marginStatus.textContent = 'Fair';
                marginStatus.className = 'ml-2 text-sm text-orange-600';
            } else if (margin > 0) {
                marginBar.className = 'bg-red-600 h-2 rounded-full';
                marginStatus.textContent = 'Low';
                marginStatus.className = 'ml-2 text-sm text-red-600';
            } else {
                marginBar.className = 'bg-gray-300 h-2 rounded-full';
                marginStatus.textContent = 'No Data';
                marginStatus.className = 'ml-2 text-sm text-gray-600';
            }
        }

        // Update issues
        const issues = data.issues;
        if (issues) {
            const lossMakers = issues.loss_makers?.length || 0;
            const lowMargin = issues.low_margin_items?.length || 0;
            
            this.updateElement('issues-count', lossMakers + lowMargin);
            this.updateElement('loss-makers', lossMakers);
            this.updateElement('low-margin', lowMargin);
            this.updateElement('issues-summary', `(${lossMakers + lowMargin} items)`);
            
            // Update issues table
            this.updateIssuesTable(issues);
        }

        // Update suggestions
        const suggestions = issues?.price_suggestions;
        if (suggestions) {
            this.updateSuggestions(suggestions);
        }

        // Update charts if trend data available
        if (data.trend) {
            this.createProfitTrendChart(data.trend);
        }

        // Load top items
        this.loadTopItems();
    }

    updateIssuesTable(issues) {
        const container = document.getElementById('issues-table-body');
        if (!container) return;

        const lossMakers = issues.loss_makers || [];
        const lowMargin = issues.low_margin_items || [];
        const allIssues = [...lossMakers, ...lowMargin];

        if (allIssues.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="4" class="px-6 py-8 text-center text-gray-500">
                        <i class="fas fa-check-circle text-3xl text-green-500 mb-3"></i>
                        <p class="font-medium">No profit issues found!</p>
                        <p class="text-sm mt-1">All menu items are performing well.</p>
                    </td>
                </tr>
            `;
            return;
        }

        const rows = allIssues.slice(0, 5).map(item => `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4">
                    <div class="text-sm font-medium text-gray-900">${item.name || 'Unknown Item'}</div>
                </td>
                <td class="px-6 py-4">
                    <span class="px-2 py-1 text-xs font-medium rounded-full ${item.margin <= 0 ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}">
                        ${item.margin?.toFixed(1) || '0.0'}%
                    </span>
                </td>
                <td class="px-6 py-4">
                    ${item.margin <= 0 ? 
                        '<span class="text-red-600 font-medium">Loss Maker</span>' : 
                        '<span class="text-yellow-600 font-medium">Low Margin</span>'}
                </td>
                <td class="px-6 py-4">
                    <a href="/profit-intelligence/menu-analysis/#item-${item.id}" class="text-red-600 hover:text-red-900 text-sm">
                        <i class="fas fa-chart-line mr-1"></i> Analyze
                    </a>
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
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-check-circle text-3xl text-green-500 mb-3"></i>
                    <p class="font-medium">No suggestions needed</p>
                    <p class="text-sm mt-1">Your menu is well-optimized for profit.</p>
                </div>
            `;
            return;
        }

        const suggestionsHtml = suggestions.slice(0, 3).map(suggestion => `
            <div class="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div class="flex items-start">
                    <div class="flex-shrink-0">
                        <i class="fas fa-lightbulb text-yellow-500 text-xl"></i>
                    </div>
                    <div class="ml-3 flex-1">
                        <h4 class="text-sm font-medium text-yellow-800">Price Adjustment Suggested</h4>
                        <div class="mt-2 text-sm text-yellow-700">
                            <p><strong>${suggestion.item_name}</strong></p>
                            <p>Current: $${suggestion.current_price?.toFixed(2)} (${suggestion.current_margin?.toFixed(1)}% margin)</p>
                            <p>Suggested: <span class="font-bold">$${suggestion.suggested_price?.toFixed(2)}</span> (${suggestion.projected_margin?.toFixed(1)}% margin)</p>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = suggestionsHtml;
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
            }
        } catch (error) {
            console.error('Error loading top items:', error);
        }
    }

    createProfitTrendChart(trendData) {
        const ctx = document.getElementById('profitTrendChart')?.getContext('2d');
        if (!ctx) return;

        if (this.profitTrendChart) {
            this.profitTrendChart.destroy();
        }

        const dailyData = trendData.daily_data || [];
        const labels = dailyData.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
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
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => '$' + value
                        }
                    }
                }
            }
        });
    }

    createTopItemsChart(items) {
        const ctx = document.getElementById('topItemsChart')?.getContext('2d');
        if (!ctx) return;

        if (this.topItemsChart) {
            this.topItemsChart.destroy();
        }

        const labels = items.slice(0, 5).map(item => 
            item.name.length > 15 ? item.name.substring(0, 15) + '...' : item.name
        );
        const profitData = items.slice(0, 5).map(item => item.profit || 0);

        this.topItemsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Total Profit ($)',
                    data: profitData,
                    backgroundColor: 'rgba(220, 38, 38, 0.7)',
                    borderColor: '#dc2626',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => '$' + value
                        }
                    }
                }
            }
        });
    }

    getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };

        // Include JWT token if available
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }

        // Include CSRF token for session auth
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
        if (element) element.textContent = value;
    }

    showLoading(show) {
        const spinner = document.getElementById('loading-spinner');
        if (spinner) {
            spinner.style.display = show ? 'flex' : 'none';
        }
    }

    showToast(message, type = 'info') {
        // Use SweetAlert2 if available, otherwise console.log
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

    setupAutoRefresh() {
        // Refresh every 5 minutes
        setInterval(() => {
            this.loadDashboard();
        }, 5 * 60 * 1000);
    }

    updateDashboardWithDateRange(data) {
        // Custom logic for date range view
        console.log('Date range data:', data);
        // You can implement specific date range visualization here
    }
}

// Make available globally
window.ProfitDashboard = ProfitDashboard;

// Backwards-compatible static helper used by inline onclick handlers in templates
ProfitDashboard.setChartPeriod = function(days) {
    if (window.profitDashboard && typeof window.profitDashboard.loadProfitTrend === 'function') {
        window.profitDashboard.loadProfitTrend(days);
    }
};