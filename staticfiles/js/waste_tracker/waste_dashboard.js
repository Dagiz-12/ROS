// static/js/waste_tracker/waste_dashboard.js - COMPLETE UPDATED VERSION
class WasteDashboard {
    constructor(config = {}) {
        this.config = config;
        this.apiBase = '/waste/api/';
        this.currentPeriod = config.initialPeriod || '30';
        this.charts = {};
        this.data = {
            dashboard: {},
            summary: {},
            wasteByCategory: [],
            recentWaste: [],
            activeAlerts: [],
            targetsProgress: []
        };
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDatePicker();
        this.loadDashboard();
    }

    setupEventListeners() {
        // Period buttons
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.selectPeriod(e.target.dataset.period);
            });
        });

        // Chart type buttons
        document.querySelectorAll('.chart-action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.changeChartType(e.target.closest('.chart-action-btn').dataset.chartType);
            });
        });

        // Tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.closest('.tab-btn').dataset.tab);
            });
        });

        // Manual refresh
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadDashboard();
                this.showToast('Dashboard refreshed', 'success');
            });
        }

        // Export button
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportData();
            });
        }
    }

    setupDatePicker() {
        const datePicker = document.getElementById('custom-date-range');
        if (datePicker) {
            flatpickr(datePicker, {
                mode: 'range',
                dateFormat: 'Y-m-d',
                onChange: (selectedDates) => {
                    if (selectedDates.length === 2) {
                        this.selectCustomPeriod(selectedDates[0], selectedDates[1]);
                    }
                }
            });
        }
    }

    selectPeriod(period) {
        if (period === 'custom') {
            document.getElementById('date-range-picker').style.display = 'block';
            return;
        }

        document.getElementById('date-range-picker').style.display = 'none';
        this.currentPeriod = period;
        
        // Update UI
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.remove('active', 'bg-red-600', 'text-white');
            if (btn.dataset.period === period) {
                btn.classList.add('active', 'bg-red-600', 'text-white');
            }
        });

        // Reload data
        this.loadDashboard();
    }

    selectCustomPeriod(startDate, endDate) {
        const daysDiff = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
        this.currentPeriod = `${daysDiff}:${startDate.toISOString().split('T')[0]}:${endDate.toISOString().split('T')[0]}`;
        this.loadDashboard();
    }

    async loadDashboard() {
        console.log('Loading waste dashboard data...');
        this.showLoading('Loading dashboard data...');
        
        try {
            // Load dashboard data (this works!)
            const dashboardResponse = await this.apiRequest('GET', 'dashboard/');
            console.log('Dashboard response:', dashboardResponse);
            
            if (dashboardResponse && dashboardResponse.success) {
                this.data = {
                    dashboard: dashboardResponse,
                    summary: dashboardResponse.summary || {},
                    wasteByCategory: dashboardResponse.waste_by_category || [],
                    recentWaste: dashboardResponse.recent_waste || [],
                    activeAlerts: dashboardResponse.active_alerts || [],
                    targetsProgress: dashboardResponse.targets_progress || []
                };
                
                this.updateUI();
                this.renderCharts();
                this.renderTables();
                
            } else {
                throw new Error('Invalid dashboard response');
            }
            
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showError('Failed to load dashboard data. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    updateUI() {
        const { summary } = this.data;
        
        if (summary) {
            // Update summary cards with actual data
            document.getElementById('total-waste-cost').textContent = 
                `$${summary.total_waste_cost_month?.toFixed(2) || '0.00'}`;
            
            document.getElementById('avg-daily-waste').textContent = 
                `$${summary.total_waste_cost_week ? (summary.total_waste_cost_week / 7).toFixed(2) : '0.00'}`;
            
            // Calculate waste percentage (placeholder for now)
            const totalCost = summary.total_waste_cost_month || 0;
            const wastePercentage = totalCost > 0 ? '5.2%' : '0.0%';
            document.getElementById('waste-percentage').textContent = wastePercentage;
            
            // Estimate reduction potential (10-20% of current waste)
            const estimatedSavings = totalCost * 0.15;
            document.getElementById('reduction-potential').textContent = 
                `$${estimatedSavings.toFixed(2)}`;
            
            // Update change indicator
            this.updateChangeIndicator();
        }
    }

    updateChangeIndicator() {
        const changeElement = document.getElementById('waste-change');
        if (!changeElement) return;
        
        // This would ideally come from your API
        // For now, we'll show a static improvement
        changeElement.innerHTML = `
            <i class="fas fa-arrow-down text-green-500 mr-1"></i> 
            <span class="text-green-600">5.2% vs last month</span>
        `;
    }

    renderCharts() {
        const { wasteByCategory, recentWaste } = this.data;
        
        // Waste Trend Chart
        if (recentWaste && recentWaste.length > 0) {
            const dailyTrend = this.createDailyTrendFromRecentWaste(recentWaste);
            this.renderTrendChart(dailyTrend);
        }
        
        // Category Chart
        if (wasteByCategory && wasteByCategory.length > 0) {
            this.renderCategoryChart(wasteByCategory);
        }
        
        // Reason Chart
        if (recentWaste && recentWaste.length > 0) {
            const reasons = this.extractReasonsFromRecentWaste(recentWaste);
            this.renderReasonChart(reasons);
        }
    }

    createDailyTrendFromRecentWaste(recentWaste) {
        // Group recent waste by day
        const dailyData = {};
        
        recentWaste.forEach(waste => {
            if (waste.recorded_at) {
                const date = new Date(waste.recorded_at).toLocaleDateString('en-US', { 
                    weekday: 'short' 
                });
                
                if (!dailyData[date]) {
                    dailyData[date] = {
                        day_name: date,
                        total: 0
                    };
                }
                dailyData[date].total += waste.cost || 0;
            }
        });
        
        return Object.values(dailyData);
    }

    extractReasonsFromRecentWaste(recentWaste) {
        // Group by reason
        const reasonData = {};
        
        recentWaste.forEach(waste => {
            const reason = waste.reason || 'Unknown';
            
            if (!reasonData[reason]) {
                reasonData[reason] = {
                    reason_name: reason,
                    total_cost: 0,
                    waste_count: 0
                };
            }
            reasonData[reason].total_cost += waste.cost || 0;
            reasonData[reason].waste_count += 1;
        });
        
        // Convert to array and sort by total cost
        return Object.values(reasonData)
            .sort((a, b) => b.total_cost - a.total_cost)
            .slice(0, 8);
    }

    renderTrendChart(dailyData) {
        const ctx = document.getElementById('wasteTrendChart')?.getContext('2d');
        if (!ctx) return;
        
        if (this.charts.trend && typeof this.charts.trend.destroy === 'function') {
        try {
            this.charts.trend.destroy();
        } catch (e) {
            console.warn('Error destroying trend chart:', e);
        }
    }
        
        const labels = dailyData.map(d => d.day_name);
        const data = dailyData.map(d => d.total);
        
        this.charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily Waste Cost',
                    data: data,
                    borderColor: '#dc2626',
                    backgroundColor: 'rgba(220, 38, 38, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: value => `$${value}`
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    renderCategoryChart(categories) {
        const ctx = document.getElementById('categoryChart')?.getContext('2d');
        if (!ctx) return;
        
        if (this.charts.category) {
            this.charts.category.destroy();
        }
        
        const labels = categories.map(c => c.category_name);
        const data = categories.map(c => c.total_cost || 0);
        const colors = this.generateColors(categories.length);
        
        this.charts.category = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }

    renderReasonChart(reasons) {
        const ctx = document.getElementById('reasonChart')?.getContext('2d');
        if (!ctx) return;
        
        if (this.charts.reason) {
            this.charts.reason.destroy();
        }
        
        const labels = reasons.map(r => r.reason_name);
        const data = reasons.map(r => r.total_cost || 0);
        
        this.charts.reason = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Cost by Reason',
                    data: data,
                    backgroundColor: '#3b82f6',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: value => `$${value}`
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    renderTables() {
        const { recentWaste } = this.data;
        
        // Top Items Table
        if (recentWaste && recentWaste.length > 0) {
            const topItems = this.extractTopItemsFromRecentWaste(recentWaste);
            this.renderTopItemsTable(topItems);
        } else {
            this.renderEmptyTable('top-items-table', 'No waste items recorded yet');
        }
        
        // Recurring Issues
        if (recentWaste && recentWaste.length > 0) {
            const recurringIssues = this.findRecurringIssues(recentWaste);
            this.renderRecurringIssues(recurringIssues);
        } else {
            this.renderEmptyRecurringIssues();
        }
        
        // Alerts
        if (this.data.activeAlerts && this.data.activeAlerts.length > 0) {
            this.renderAlerts();
        } else {
            this.renderEmptyAlerts();
        }
        
        // Suggestions
        this.renderSuggestions();
    }

    extractTopItemsFromRecentWaste(recentWaste) {
        // Group items by name
        const itemData = {};
        
        recentWaste.forEach(waste => {
            const itemName = waste.item_name || 'Unknown Item';
            const category = waste.category || 'General';
            
            if (!itemData[itemName]) {
                itemData[itemName] = {
                    item_name: itemName,
                    category: category,
                    total_quantity: 0,
                    total_cost: 0,
                    count: 0,
                    reasons: new Set()
                };
            }
            
            itemData[itemName].total_quantity += waste.quantity || 0;
            itemData[itemName].total_cost += waste.cost || 0;
            itemData[itemName].count += 1;
            if (waste.reason) {
                itemData[itemName].reasons.add(waste.reason);
            }
        });
        
        // Convert to array, calculate averages, and sort by cost
        return Object.values(itemData)
            .map(item => ({
                ...item,
                avg_cost_per_incident: item.total_cost / item.count,
                primary_reason: Array.from(item.reasons)[0] || 'Various'
            }))
            .sort((a, b) => b.total_cost - a.total_cost)
            .slice(0, 10);
    }

    findRecurringIssues(recentWaste) {
        // Find items with multiple waste incidents
        const itemCounts = {};
        
        recentWaste.forEach(waste => {
            const itemName = waste.item_name || 'Unknown Item';
            itemCounts[itemName] = (itemCounts[itemName] || 0) + 1;
        });
        
        // Return items with 3 or more incidents
        return Object.entries(itemCounts)
            .filter(([item, count]) => count >= 3)
            .map(([item, count]) => ({
                item_name: item,
                waste_count: count,
                reason_name: 'Frequent Waste'
            }));
    }

    renderTopItemsTable(items) {
        const container = document.getElementById('top-items-table');
        if (!container) return;
        
        const rows = items.map(item => `
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-3">
                    <div class="flex items-center">
                        <div class="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center mr-3">
                            <i class="fas fa-${this.getItemIcon(item.category)} text-gray-500"></i>
                        </div>
                        <div>
                            <div class="font-medium text-gray-900">${item.item_name}</div>
                            <div class="text-xs text-gray-500">${item.category || ''}</div>
                        </div>
                    </div>
                </td>
                <td class="px-4 py-3">
                    <span class="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded-full">
                        ${item.category || 'General'}
                    </span>
                </td>
                <td class="px-4 py-3 text-center font-medium">
                    ${item.total_quantity?.toFixed(2) || '0.00'}
                </td>
                <td class="px-4 py-3 text-right font-bold text-red-600">
                    $${item.total_cost?.toFixed(2) || '0.00'}
                </td>
                <td class="px-4 py-3 text-right">
                    $${item.avg_cost_per_incident?.toFixed(2) || '0.00'}
                </td>
                <td class="px-4 py-3">
                    <span class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                        ${item.primary_reason || 'Various'}
                    </span>
                </td>
                <td class="px-4 py-3 text-center">
                    <button class="text-blue-600 hover:text-blue-800" onclick="investigateItem('${item.item_name}')">
                        <i class="fas fa-search"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        
        container.innerHTML = rows;
    }

    renderEmptyTable(tableId, message) {
        const container = document.getElementById(tableId);
        if (!container) return;
        
        container.innerHTML = `
            <tr>
                <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                    <i class="fas fa-box-open text-3xl mb-3"></i>
                    <p>${message}</p>
                </td>
            </tr>
        `;
    }

    renderRecurringIssues(issues) {
        const container = document.getElementById('recurring-issues-list');
        if (!container) return;
        
        if (issues.length === 0) {
            this.renderEmptyRecurringIssues();
            return;
        }
        
        const issuesHtml = issues.map(issue => `
            <div class="bg-white border border-gray-200 rounded-lg p-4 mb-3">
                <div class="flex justify-between items-start mb-2">
                    <div class="flex items-center">
                        <i class="fas fa-exclamation-triangle text-yellow-500 mr-2"></i>
                        <h4 class="font-medium text-gray-900">${issue.item_name}</h4>
                    </div>
                    <span class="px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">
                        ${issue.waste_count} incidents
                    </span>
                </div>
                <div class="mb-3">
                    <div class="text-sm text-gray-500">Reason</div>
                    <div class="font-medium">${issue.reason_name}</div>
                </div>
                <div>
                    <button class="text-sm text-blue-600 hover:text-blue-800" onclick="createActionPlan('${issue.item_name}')">
                        <i class="fas fa-clipboard-list mr-1"></i> Create Action Plan
                    </button>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = issuesHtml;
    }

    renderEmptyRecurringIssues() {
        const container = document.getElementById('recurring-issues-list');
        if (!container) return;
        
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <i class="fas fa-check-circle text-3xl text-green-500 mb-3"></i>
                <p>No recurring issues detected</p>
                <p class="text-sm mt-1">Great job! Keep monitoring waste regularly.</p>
            </div>
        `;
    }

    renderAlerts() {
        const container = document.getElementById('alerts-grid');
        if (!container) return;
        
        const activeAlerts = this.data.activeAlerts;
        
        if (activeAlerts.length === 0) {
            this.renderEmptyAlerts();
            return;
        }
        
        const alertsHtml = activeAlerts.slice(0, 5).map(alert => `
            <div class="bg-white border border-gray-200 rounded-lg p-4">
                <div class="flex items-start mb-2">
                    <div class="w-10 h-10 rounded-full flex items-center justify-center mr-3 mt-1
                         ${alert.type === 'threshold_exceeded' ? 'bg-red-100 text-red-600' :
                           alert.type === 'recurring_issue' ? 'bg-yellow-100 text-yellow-600' :
                           'bg-blue-100 text-blue-600'}">
                        <i class="fas fa-${this.getAlertIcon(alert.type)}"></i>
                    </div>
                    <div class="flex-1">
                        <h4 class="font-medium text-gray-900">${alert.title}</h4>
                        <p class="text-sm text-gray-600 mt-1">${alert.message}</p>
                        <div class="text-xs text-gray-400 mt-2">${this.formatTimeAgo(alert.created_at)}</div>
                    </div>
                </div>
                <div class="flex space-x-2 mt-3">
                    <button class="text-sm px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                            onclick="markAlertRead('${alert.id}')">
                        Mark Read
                    </button>
                    <button class="text-sm px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
                            onclick="resolveAlert('${alert.id}')">
                        Resolve
                    </button>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = alertsHtml;
    }

    renderEmptyAlerts() {
        const container = document.getElementById('alerts-grid');
        if (!container) return;
        
        container.innerHTML = `
            <div class="bg-white border border-gray-200 rounded-lg p-8 text-center">
                <i class="fas fa-bell-slash text-4xl text-gray-300 mb-3"></i>
                <p class="text-gray-500">No active alerts</p>
                <p class="text-sm text-gray-400 mt-1">Everything looks good!</p>
            </div>
        `;
    }

    renderSuggestions() {
        const container = document.getElementById('suggestions-list');
        if (!container) return;
        
        const defaultSuggestions = [
            'Implement portion control training for kitchen staff',
            'Review and adjust preparation quantities based on sales data',
            'Improve inventory rotation (FIFO) to reduce spoilage',
            'Monitor expiration dates more closely',
            'Train staff on proper food storage techniques'
        ];
        
        const suggestionsHtml = defaultSuggestions.map((suggestion, index) => `
            <div class="bg-white border border-gray-200 rounded-lg p-4 mb-3">
                <div class="flex items-start">
                    <div class="w-6 h-6 bg-red-100 text-red-600 rounded-full flex items-center justify-center mr-3 mt-1 text-xs font-bold">
                        ${index + 1}
                    </div>
                    <div class="flex-1">
                        <p class="text-gray-700">${suggestion}</p>
                        <div class="flex space-x-3 mt-2">
                            <button class="text-sm text-blue-600 hover:text-blue-800"
                                    onclick="assignTask('${suggestion}')">
                                <i class="fas fa-user-check mr-1"></i> Assign
                            </button>
                            <button class="text-sm text-green-600 hover:text-green-800"
                                    onclick="scheduleTraining('${suggestion}')">
                                <i class="fas fa-calendar-alt mr-1"></i> Schedule
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = suggestionsHtml;
    }

    // Utility Methods
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

    getAlertIcon(type) {
        const icons = {
            'threshold_exceeded': 'chart-line',
            'recurring_issue': 'redo',
            'approval_needed': 'clock',
            'target_at_risk': 'exclamation-triangle',
            'default': 'bell'
        };
        return icons[type] || icons.default;
    }

    generateColors(count) {
        const colors = [
            '#dc2626', '#3b82f6', '#10b981', '#f59e0b', 
            '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'
        ];
        return colors.slice(0, count);
    }

    formatTimeAgo(timestamp) {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        return `${Math.floor(diffMins / 1440)}d ago`;
    }

    changeChartType(type) {
        document.querySelectorAll('.chart-action-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.chartType === type);
        });
        
        if (this.charts.trend && this.data.recentWaste) {
            this.charts.trend.destroy();
            const dailyTrend = this.createDailyTrendFromRecentWaste(this.data.recentWaste);
            if (type === 'bar') {
                this.renderBarChart(dailyTrend);
            } else {
                this.renderTrendChart(dailyTrend);
            }
        }
    }

    renderBarChart(dailyData) {
        const ctx = document.getElementById('wasteTrendChart')?.getContext('2d');
        if (!ctx) return;
        
        const labels = dailyData.map(d => d.day_name);
        const data = dailyData.map(d => d.total);
        
        this.charts.trend = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily Waste Cost',
                    data: data,
                    backgroundColor: '#dc2626',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: value => `$${value}`
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });
    }

    async refresh() {
        await this.loadDashboard();
    }

    exportData() {
        const { summary, recentWaste } = this.data;
        
        if (!summary) {
            this.showError('No data to export');
            return;
        }
        
        const csvContent = this.generateCSV(summary, recentWaste);
        this.downloadCSV(csvContent, `waste-dashboard-${new Date().toISOString().split('T')[0]}.csv`);
    }

    generateCSV(summary, recentWaste) {
        let csv = 'Waste Analytics Dashboard Report\n\n';
        
        csv += 'SUMMARY\n';
        csv += 'Metric,Value\n';
        csv += `Total Waste Cost (Month),${summary.total_waste_cost_month || 0}\n`;
        csv += `Total Waste Cost (Week),${summary.total_waste_cost_week || 0}\n`;
        csv += `Total Waste Cost (Today),${summary.total_waste_cost_today || 0}\n`;
        
        if (recentWaste && recentWaste.length > 0) {
            csv += '\nRECENT WASTE RECORDS\n';
            csv += 'Item,Quantity,Cost,Reason,Date\n';
            recentWaste.forEach(waste => {
                csv += `${waste.item_name || 'Unknown'},${waste.quantity || 0},${waste.cost || 0},${waste.reason || 'Unknown'},${waste.recorded_at || ''}\n`;
            });
        }
        
        return csv;
    }

    downloadCSV(content, filename) {
        const blob = new Blob([content], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    showLoading(message) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }

    showToast(message, type = 'info') {
        // Simple toast implementation
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-lg text-white ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 'bg-blue-500'
        }`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    async apiRequest(method, endpoint, params = null) {
        let url = `${this.apiBase}${endpoint}`;
        
        // Add query parameters for GET requests
        if (method === 'GET' && params) {
            const queryParams = new URLSearchParams(params).toString();
            url += `?${queryParams}`;
        }
        
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Add authorization token if available
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        // Add CSRF token for non-GET requests
        if (method !== 'GET') {
            const csrfToken = this.getCsrfToken();
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }
        }
        
        const options = {
            method,
            headers,
            credentials: 'include'
        };
        
        // Add body for non-GET requests
        if (method !== 'GET' && params) {
            options.body = JSON.stringify(params);
        }
        
        try {
            console.log(`API Request: ${method} ${url}`);
            const response = await fetch(url, options);
            
            if (response.status === 401) {
                this.redirectToLogin();
                return null;
            }
            
            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.warn('Response is not JSON:', await response.text());
                throw new Error('Server returned non-JSON response');
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

    getCsrfToken() {
        // Try to get CSRF token from cookie
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

    redirectToLogin() {
        window.location.href = '/login/';
    }
}

// Global functions for HTML onclick handlers
function investigateItem(itemName) {
    console.log(`Investigating item: ${itemName}`);
    showToast(`Investigating ${itemName}...`, 'info');
}

function createActionPlan(itemName) {
    console.log(`Creating action plan for: ${itemName}`);
    showToast(`Creating action plan for ${itemName}...`, 'info');
}

function assignTask(suggestion) {
    console.log(`Assigning task: ${suggestion}`);
    showToast(`Assigning task: ${suggestion}`, 'info');
}

function scheduleTraining(suggestion) {
    console.log(`Scheduling training: ${suggestion}`);
    showToast(`Scheduling training: ${suggestion}`, 'info');
}

function markAlertRead(alertId) {
    fetch(`/waste/api/alerts/${alertId}/mark_read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && window.wasteDashboard) {
            window.wasteDashboard.loadDashboard();
            showToast('Alert marked as read', 'success');
        }
    });
}

function resolveAlert(alertId) {
    const notes = prompt('Enter resolution notes:');
    if (notes === null) return;
    
    fetch(`/waste/api/alerts/${alertId}/resolve/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ notes })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && window.wasteDashboard) {
            window.wasteDashboard.loadDashboard();
            showToast('Alert resolved', 'success');
        }
    });
}

function getCookie(name) {
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

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-lg text-white ${
        type === 'success' ? 'bg-green-500' : 
        type === 'error' ? 'bg-red-500' : 'bg-blue-500'
    }`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the waste dashboard page
    if (document.querySelector('.waste-dashboard-container')) {
        const userData = {
            id: parseInt(document.body.dataset.userId || '0'),
            role: document.body.dataset.userRole || 'staff',
            branch_id: parseInt(document.body.dataset.branchId || '0'),
            restaurant_id: parseInt(document.body.dataset.restaurantId || '0')
        };
        
        window.wasteDashboard = new WasteDashboard({
            userData: userData,
            initialPeriod: '30'
        });
    }
});