// static/js/profit/profit-dashboard.js - COMPLETE FIXED VERSION
class ProfitDashboard {
    constructor() {
        this.apiBase = '/api/inventory/profit/';
        this.currentScope = 'branch'; // 'branch' | 'restaurant'
        this.selectedBranchId = null;
        this.accessibleBranches = [];
        this.profitTrendChart = null;
        this.topItemsChart = null;
        this.userRole = null;
        this.managerScope = null;
        
        this.init();
    }

    init() {
        this.loadUserInfo();
        this.checkAuth();
        this.setupDatePicker();
        this.setupScopeSelector();
        this.loadAccessibleBranches();
        this.loadDashboard();
        this.setupEventListeners();
        this.setupAutoRefresh();
    }

    loadUserInfo() {
        // Get user info from HTML data attributes
        this.userRole = document.body.dataset.userRole || 'manager';
        this.managerScope = document.body.dataset.managerScope || 'branch';
        this.restaurantId = document.body.dataset.restaurantId || '';
        this.branchId = document.body.dataset.branchId || '';
        
        console.log('User Info:', {
            role: this.userRole,
            scope: this.managerScope,
            restaurantId: this.restaurantId,
            branchId: this.branchId
        });
        
        // Set initial scope based on user permissions
        if (this.managerScope === 'restaurant') {
            this.currentScope = 'restaurant';
        } else {
            this.currentScope = 'branch';
            this.selectedBranchId = this.branchId || null;
        }
    }

    checkAuth() {
        if (typeof authManager !== 'undefined' && !authManager.isAuthenticated()) {
            window.location.href = '/login/';
        }
    }

    async loadAccessibleBranches() {
        if (this.userRole !== 'manager' && this.userRole !== 'admin') {
            return;
        }
        
        try {
            const response = await fetch('/api/accounts/user-branches/', {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.accessibleBranches = data.branches || [];
                    this.updateBranchSelector();
                }
            }
        } catch (error) {
            console.warn('Could not load accessible branches:', error);
        }
    }

    updateBranchSelector() {
        const selector = document.getElementById('branch-selector');
        if (!selector || this.accessibleBranches.length <= 1) return;
        
        selector.innerHTML = '';
        
        // Add "All Branches" option for multi-branch managers
        if (this.managerScope === 'restaurant') {
            const allOption = document.createElement('option');
            allOption.value = '';
            allOption.textContent = 'All Accessible Branches';
            allOption.selected = !this.selectedBranchId;
            selector.appendChild(allOption);
        }
        
        // Add individual branch options
        this.accessibleBranches.forEach(branch => {
            const option = document.createElement('option');
            option.value = branch.id;
            option.textContent = branch.name;
            option.selected = this.selectedBranchId == branch.id;
            selector.appendChild(option);
        });
        
        selector.classList.remove('hidden');
    }

    setupDatePicker() {
        const picker = document.getElementById('date-range-picker');
        if (picker) {
            flatpickr(picker, {
                mode: 'range',
                dateFormat: 'Y-m-d',
                onChange: (selectedDates, dateStr) => {
                    if (selectedDates.length === 2) {
                        this.loadCustomDateRange(selectedDates[0], selectedDates[1]);
                    }
                }
            });
        }
    }

    setupScopeSelector() {
        const toggleBtn = document.getElementById('view-toggle-btn');
        const viewIndicator = document.getElementById('view-indicator');
        const branchSelector = document.getElementById('branch-selector');
        
        if (!toggleBtn) return;
        
        // Set initial button text based on scope
        this.updateScopeButton(toggleBtn, viewIndicator);
        
        // Handle scope toggle
        toggleBtn.addEventListener('click', () => {
            const currentView = this.currentScope || 'branch';
            const newScope = currentView === 'branch' ? 'restaurant' : 'branch';
            
            this.currentScope = newScope;
            
            // Update UI
            this.updateScopeButton(toggleBtn, viewIndicator);
            
            // Show/hide branch selector
            if (branchSelector) {
                if (newScope === 'branch' && this.accessibleBranches.length > 1) {
                    branchSelector.classList.remove('hidden');
                } else {
                    branchSelector.classList.add('hidden');
                }
            }
            
            // Reload dashboard with new scope
            this.loadDashboard();
            
            // Show notification
            showToast(`Switched to ${newScope} view`, 'info');
        });
        
        // Handle branch selection
        if (branchSelector) {
            branchSelector.addEventListener('change', (e) => {
                this.selectedBranchId = e.target.value || null;
                this.loadDashboard();
            });
        }
    }

    updateScopeButton(button, indicator) {
        if (!button) return;
        
        const scope = this.currentScope;
        const isRestaurantView = scope === 'restaurant';
        
        // Update button
        if (isRestaurantView) {
            button.innerHTML = '<i class="fas fa-building mr-2"></i>Switch to Branch View';
            button.className = 'px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center';
        } else {
            button.innerHTML = '<i class="fas fa-store mr-2"></i>Switch to Restaurant View';
            button.className = 'px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center';
        }
        
        // Update indicator
        if (indicator) {
            const branchCount = this.accessibleBranches.length;
            if (isRestaurantView) {
                indicator.textContent = `Viewing All Restaurant Branches (${branchCount} branches)`;
            } else {
                const branchName = this.getSelectedBranchName();
                indicator.textContent = `Viewing: ${branchName}`;
            }
        }
    }

    getSelectedBranchName() {
        if (!this.selectedBranchId && this.accessibleBranches.length > 0) {
            return this.accessibleBranches[0].name;
        }
        
        const branch = this.accessibleBranches.find(b => b.id == this.selectedBranchId);
        return branch ? branch.name : 'Branch Data';
    }

    setupEventListeners() {
        // Period buttons
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const period = parseInt(e.target.dataset.period);
                this.setChartPeriod(period);
            });
        });

        // Refresh button
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadDashboard();
            showToast('Dashboard refreshed', 'success');
        });
    }

    setupAutoRefresh() {
        // Refresh data every 5 minutes
        setInterval(() => {
            this.loadDashboard();
        }, 5 * 60 * 1000);
    }

    async loadDashboard() {
        const loading = showLoading('Loading profit dashboard...');
        
        try {
            // Build query parameters
            const params = new URLSearchParams({
                view_level: this.currentScope
            });
            
            if (this.currentScope === 'branch' && this.selectedBranchId) {
                params.append('branch_id', this.selectedBranchId);
            }
            
            const url = `${this.apiBase}dashboard/?${params.toString()}`;
            const response = await fetch(url, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.updateDashboard(data);
                this.updateCharts(data);
                this.updateTables(data);
                this.updateSuggestions(data);
                hideLoading();
            } else {
                throw new Error(data.error || 'Failed to load dashboard');
            }
            
        } catch (error) {
            hideLoading();
            showError('Failed to load dashboard data: ' + error.message);
            console.error('Dashboard load error:', error);
        }
    }

    async loadCustomDateRange(startDate, endDate) {
        const loading = showLoading('Loading data for selected period...');
        try {
            const params = new URLSearchParams({
                start_date: startDate.toISOString().split('T')[0],
                end_date: endDate.toISOString().split('T')[0]
            });

            const response = await fetch(`${this.apiBase}daily/?${params}`, {
                headers: this.getAuthHeaders()
            });

            if (!response.ok) throw new Error('Failed to load date range data');

            const data = await response.json();
            
            if (data.success) {
                showToast(`Loaded data for ${params.get('start_date')} to ${params.get('end_date')}`, 'success');
                // Update relevant parts of the dashboard
                this.updateDateRangeData(data);
            }
        } catch (error) {
            console.error('Error loading date range:', error);
            showError('Failed to load date range data');
        } finally {
            hideLoading();
        }
    }

    updateDashboard(data) {
        // Update KPI cards
        this.updateElement('today-profit', `$${data.today?.summary?.gross_profit?.toFixed(2) || '0.00'}`);
        this.updateElement('profit-margin', `${data.today?.summary?.profit_margin?.toFixed(1) || '0.0'}%`);
        this.updateElement('waste-cost', `$${data.waste?.summary?.total_waste_cost?.toFixed(2) || '0.00'}`);
        this.updateElement('issues-count', data.kpis?.items_with_issues || 0);

        // Update change indicators
        const change = data.daily_change || { profit: 0, revenue: 0 };
        const profitChangeElem = document.getElementById('profit-change');
        if (profitChangeElem) {
            if (change.profit > 0) {
                profitChangeElem.innerHTML = `<i class="fas fa-arrow-up text-green-500 mr-1"></i> +$${Math.abs(change.profit).toFixed(2)}`;
                profitChangeElem.className = 'text-green-600 text-sm font-medium';
            } else if (change.profit < 0) {
                profitChangeElem.innerHTML = `<i class="fas fa-arrow-down text-red-500 mr-1"></i> -$${Math.abs(change.profit).toFixed(2)}`;
                profitChangeElem.className = 'text-red-600 text-sm font-medium';
            } else {
                profitChangeElem.innerHTML = '<i class="fas fa-minus text-gray-500 mr-1"></i> No change';
                profitChangeElem.className = 'text-gray-600 text-sm font-medium';
            }
        }

        // Update today's details
        this.updateElement('today-orders', `${data.today?.summary?.order_count || 0} orders`);
        this.updateElement('today-margin', `${data.today?.summary?.profit_margin?.toFixed(1) || '0.0'}% margin`);

        // Update margin bar
        const marginBar = document.getElementById('margin-bar');
        const marginStatus = document.getElementById('margin-status');
        if (marginBar && marginStatus) {
            const margin = data.today?.summary?.profit_margin || 0;
            let width = Math.min(Math.max(margin, 0), 50);
            marginBar.style.width = `${width * 2}%`;
            
            if (margin >= 30) {
                marginBar.className = 'bg-green-600 h-2 rounded-full';
                marginStatus.textContent = 'Excellent';
                marginStatus.className = 'ml-2 text-sm text-green-600';
            } else if (margin >= 15) {
                marginBar.className = 'bg-yellow-600 h-2 rounded-full';
                marginStatus.textContent = 'Good';
                marginStatus.className = 'ml-2 text-sm text-yellow-600';
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

        // Update waste info
        this.updateElement('waste-percentage', `${data.waste?.summary?.waste_percentage?.toFixed(1) || '0.0'}%`);
        this.updateElement('waste-savings', `$${data.waste?.reduction_target?.savings_potential?.toFixed(2) || '0.00'} savings possible`);

        // Update issues info
        this.updateElement('loss-makers', `${data.issues?.summary?.loss_makers_count || 0} loss makers`);
        this.updateElement('low-margin', `${data.issues?.summary?.low_margin_count || 0} low margin`);
    }

    updateCharts(data) {
        if (data.trend) {
            this.createProfitTrendChart(data.trend);
        }
        if (data.menu_analysis?.top_profitable) {
            this.createTopItemsChart(data.menu_analysis.top_profitable);
        }
    }

    createProfitTrendChart(trendData) {
        const ctx = document.getElementById('profitTrendChart')?.getContext('2d');
        if (!ctx) return;

        // Destroy existing chart
        if (this.profitTrendChart) {
            this.profitTrendChart.destroy();
        }

        const labels = trendData.daily_data?.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }) || [];

        const profitData = trendData.daily_data?.map(d => d.profit) || [];
        const revenueData = trendData.daily_data?.map(d => d.revenue) || [];

        this.profitTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Daily Profit',
                        data: profitData,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Daily Revenue',
                        data: revenueData,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.4,
                        fill: true,
                        hidden: true // Hide by default to avoid clutter
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    x: {
                        grid: { display: false }
                    },
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

    createTopItemsChart(topItems) {
        const ctx = document.getElementById('topItemsChart')?.getContext('2d');
        if (!ctx) return;

        // Destroy existing chart
        if (this.topItemsChart) {
            this.topItemsChart.destroy();
        }

        const labels = topItems.map(item => 
            item.name.length > 15 ? item.name.substring(0, 15) + '...' : item.name
        );
        const profitData = topItems.map(item => item.gross_profit);
        const marginData = topItems.map(item => item.profit_margin);

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
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => `$${context.parsed.y.toFixed(2)} profit`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false }
                    },
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

    updateTables(data) {
        this.updateIssuesTable(data.issues);
        this.updateWasteTable(data.waste);
    }

    updateIssuesTable(issues) {
        const container = document.getElementById('issues-table-body');
        const summary = document.getElementById('issues-summary');
        
        if (!container) return;

        const lossMakers = issues?.issues?.loss_makers || [];
        const lowMargin = issues?.issues?.low_margin || [];
        
        if (lossMakers.length === 0 && lowMargin.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="4" class="px-6 py-8 text-center text-gray-500">
                        <i class="fas fa-check-circle text-3xl text-green-500 mb-3"></i>
                        <p class="font-medium">No profit issues found!</p>
                        <p class="text-sm mt-1">All menu items are performing well.</p>
                    </td>
                </tr>
            `;
            if (summary) summary.textContent = '(0 issues)';
            return;
        }

        // Combine issues
        const allIssues = [...lossMakers, ...lowMargin];
        
        const rows = allIssues.slice(0, 5).map(item => `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        <div class="ml-4">
                            <div class="text-sm font-medium text-gray-900">${item.name || 'Unknown Item'}</div>
                            <div class="text-sm text-gray-500">${item.category || 'Uncategorized'}</div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 py-1 text-xs font-medium rounded-full ${item.profit_margin <= 0 ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}">
                        ${item.profit_margin?.toFixed(1) || '0.0'}%
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    ${item.profit_margin <= 0 ? 
                        '<span class="text-red-600 font-medium">Loss Maker</span>' : 
                        '<span class="text-yellow-600 font-medium">Low Margin</span>'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <button onclick="ProfitDashboard.viewItemDetail(${item.id})" class="text-red-600 hover:text-red-900">
                        <i class="fas fa-chart-line mr-1"></i> Analyze
                    </button>
                </td>
            </tr>
        `).join('');

        container.innerHTML = rows;
        if (summary) summary.textContent = `(${allIssues.length} issues)`;
    }

    updateWasteTable(wasteData) {
        const container = document.getElementById('waste-table-body');
        if (!container) return;

        const wasteByCategory = wasteData?.by_category || [];
        
        if (wasteByCategory.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="4" class="px-6 py-8 text-center text-gray-500">
                        <i class="fas fa-check-circle text-3xl text-green-500 mb-3"></i>
                        <p class="font-medium">No waste recorded</p>
                        <p class="text-sm mt-1">Great job minimizing waste!</p>
                    </td>
                </tr>
            `;
            return;
        }

        const rows = wasteByCategory.slice(0, 5).map(item => `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">
                        ${(item.stock_item__category || 'Unknown').replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm text-gray-900">${parseFloat(item.total_quantity || 0).toFixed(2)}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm font-medium text-gray-900">$${parseFloat(item.total_cost || 0).toFixed(2)}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm text-gray-500">${item.transaction_count || 0} incidents</span>
                </td>
            </tr>
        `).join('');

        container.innerHTML = rows;
    }

    updateSuggestions(data) {
        const container = document.getElementById('suggestions-container');
        if (!container) return;

        const suggestions = data.issues?.suggestions || [];
        
        if (suggestions.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-check-circle text-3xl text-green-500 mb-3"></i>
                    <p class="font-medium">No suggestions needed</p>
                    <p class="text-sm mt-1">Your menu is well-optimized for profit.</p>
                </div>
            `;
            return;
        }

        // FIX: Use let instead of const for reassignment
        let suggestionsHtml = suggestions.slice(0, 3).map(suggestion => `
            <div class="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div class="flex items-start">
                    <div class="flex-shrink-0">
                        <i class="fas fa-exclamation-triangle text-yellow-500 text-xl"></i>
                    </div>
                    <div class="ml-3 flex-1">
                        <h4 class="text-sm font-medium text-yellow-800">Price Adjustment Suggested</h4>
                        <div class="mt-2 text-sm text-yellow-700">
                            <p><strong>${suggestion.item_name}</strong>: Current price $${suggestion.current_price?.toFixed(2) || '0.00'} (${suggestion.current_margin?.toFixed(1) || '0.0'}% margin)</p>
                            <p class="mt-1">Suggested price: <span class="font-bold">$${suggestion.suggested_price?.toFixed(2) || '0.00'}</span> (${suggestion.projected_margin?.toFixed(1) || '0.0'}% margin)</p>
                            <p class="mt-1 text-xs">${suggestion.reason || 'Low profit margin'}</p>
                        </div>
                        <div class="mt-3">
                            <button onclick="ProfitDashboard.applySuggestion(${suggestion.item_id}, ${suggestion.suggested_price})" class="px-3 py-1 text-xs bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200 font-medium mr-2">
                                Apply Suggestion
                            </button>
                            <button onclick="ProfitDashboard.ignoreSuggestion(${suggestion.item_id})" class="px-3 py-1 text-xs border border-yellow-300 text-yellow-700 rounded hover:bg-yellow-100">
                                Ignore
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        if (suggestions.length > 3) {
            suggestionsHtml += `
                <div class="text-center mt-4">
                    <button onclick="ProfitDashboard.viewAllSuggestions()" class="text-sm text-red-600 hover:text-red-700">
                        View ${suggestions.length - 3} more suggestions <i class="fas fa-arrow-right ml-1"></i>
                    </button>
                </div>
            `;
        }

        container.innerHTML = suggestionsHtml;
    }

    updateElement(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) element.textContent = value;
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
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Public static methods for button clicks
    static refreshDashboard() {
        window.profitDashboard?.loadDashboard();
    }

    static setChartPeriod(days) {
        if (window.profitDashboard) {
            window.profitDashboard.currentPeriod = days;
            window.profitDashboard.loadProfitTrend(days);
            
            // Update button styles
            document.querySelectorAll('.period-btn').forEach(btn => {
                const btnPeriod = parseInt(btn.dataset.period);
                if (btnPeriod === days) {
                    btn.classList.add('bg-red-50', 'text-red-600');
                    btn.classList.remove('hover:bg-gray-100');
                } else {
                    btn.classList.remove('bg-red-50', 'text-red-600');
                    btn.classList.add('hover:bg-gray-100');
                }
            });
        }
    }

    static viewAllItems() {
        window.location.href = '/restaurant-admin/menu/';
    }

    static viewProfitIssues() {
        // Implement navigation to detailed issues page
        console.log('Navigate to profit issues detail page');
    }

    static viewWasteAnalysis() {
        window.location.href = '/inventory/profit-dashboard/waste-analysis/';
    }

    static recordWaste() {
        // Implement waste recording modal
        console.log('Open waste recording modal');
    }

    static viewItemDetail(itemId) {
        console.log('View item detail:', itemId);
    }

    static applySuggestion(itemId, suggestedPrice) {
        console.log('Apply price suggestion for item:', itemId, 'Price:', suggestedPrice);
    }

    static ignoreSuggestion(itemId) {
        console.log('Ignore suggestion for item:', itemId);
    }

    static viewAllSuggestions() {
        console.log('View all suggestions');
    }

    async loadProfitTrend(days) {
        try {
            const response = await fetch(`${this.apiBase}trend/?days=${days}`, {
                headers: this.getAuthHeaders()
            });

            if (!response.ok) throw new Error('Failed to load trend data');

            const data = await response.json();
            if (data.success) {
                this.createProfitTrendChart(data);
            }
        } catch (error) {
            console.error('Error loading profit trend:', error);
            showError('Failed to load profit trend data');
        }
    }

    updateDateRangeData(data) {
        // Update relevant parts of the dashboard with date range data
        console.log('Update dashboard with date range data:', data);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.profitDashboard = new ProfitDashboard();
});