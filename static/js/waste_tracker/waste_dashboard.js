// static/js/waste_tracker/waste-dashboard.js
class WasteDashboard {
    constructor(config) {
        this.config = config;
        this.apiBase = '/waste/api/';
        this.currentPeriod = config.initialPeriod || '30';
        this.charts = {};
        this.data = {};
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadDashboard();
        this.setupDatePicker();
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

        this.currentPeriod = period;
        
        // Update UI
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.period === period) {
                btn.classList.add('active');
            }
        });

        // Reload data
        this.loadDashboard();
    }

    selectCustomPeriod(startDate, endDate) {
        // Custom period logic
        const daysDiff = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
        this.currentPeriod = `${daysDiff}:${startDate.toISOString().split('T')[0]}:${endDate.toISOString().split('T')[0]}`;
        this.loadDashboard();
    }

    async loadDashboard() {
        this.showLoading();
        
        try {
            // Load analytics data
            const analytics = await this.apiRequest(
                'GET', 
                `analytics/detailed/?days=${this.currentPeriod}${this.config.userData.branch_id ? `&branch_id=${this.config.userData.branch_id}` : ''}`
            );
            
            // Load reduction potential
            const reductionPotential = await this.apiRequest(
                'GET',
                `analytics/reduction-potential/${this.config.userData.branch_id ? `?branch_id=${this.config.userData.branch_id}` : ''}`
            );
            
            // Load alerts
            const alerts = await this.apiRequest('GET', 'alerts/');
            
            this.data = {
                analytics: analytics.analytics || {},
                reductionPotential: reductionPotential.reduction_potential || {},
                alerts: alerts.results || []
            };
            
            this.updateUI();
            this.renderCharts();
            this.renderTables();
            
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showError('Failed to load dashboard data');
        } finally {
            this.hideLoading();
        }
    }

    updateUI() {
        const { analytics, reductionPotential } = this.data;
        
        // Update summary cards
        if (analytics.summary) {
            document.getElementById('total-waste-cost').textContent = 
                `$${analytics.summary.total_waste_cost.toFixed(2)}`;
            document.getElementById('waste-percentage').textContent = 
                `${analytics.summary.waste_percentage.toFixed(1)}%`;
            document.getElementById('avg-daily-waste').textContent = 
                `$${analytics.summary.avg_daily_waste.toFixed(2)}`;
        }
        
        if (reductionPotential.monthly_potential_savings) {
            document.getElementById('reduction-potential').textContent = 
                `$${reductionPotential.monthly_potential_savings.toFixed(2)}`;
        }
        
        // Update waste change indicator
        this.updateChangeIndicator();
    }

    renderCharts() {
        const { analytics } = this.data;
        
        // Waste Trend Chart
        this.renderTrendChart(analytics.daily_trend || []);
        
        // Category Chart
        this.renderCategoryChart(analytics.by_category || []);
        
        // Reason Chart
        this.renderReasonChart(analytics.by_reason || []);
    }

    renderTrendChart(dailyData) {
        const ctx = document.getElementById('wasteTrendChart')?.getContext('2d');
        if (!ctx) return;
        
        if (this.charts.trend) {
            this.charts.trend.destroy();
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
                    tension: 0.4
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
        const data = categories.map(c => c.total_cost);
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
        
        const topReasons = reasons.slice(0, 8);
        const labels = topReasons.map(r => r.reason_name);
        const data = topReasons.map(r => r.total_cost);
        
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
                    }
                }
            }
        });
    }

    renderTables() {
        const { analytics, reductionPotential } = this.data;
        
        // Top Items Table
        this.renderTopItemsTable(analytics.top_items || []);
        
        // Recurring Issues
        this.renderRecurringIssues(analytics.by_reason || []);
        
        // Suggestions
        this.renderSuggestions(reductionPotential.recommended_actions || []);
        
        // Alerts
        this.renderAlerts();
    }

    renderTopItemsTable(items) {
        const container = document.getElementById('top-items-table');
        if (!container) return;
        
        if (!items || items.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-8 text-gray-500">
                        <i class="fas fa-box-open text-3xl mb-3"></i>
                        <p>No waste data available</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        const rows = items.map(item => `
            <tr>
                <td>
                    <div class="flex items-center">
                        <div class="item-icon">
                            <i class="fas fa-${this.getItemIcon(item.category)}"></i>
                        </div>
                        <div class="ml-3">
                            <div class="font-medium">${item.item_name}</div>
                            <div class="text-xs text-gray-500">${item.unit}</div>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="category-badge">${item.category}</span>
                </td>
                <td class="text-center">
                    <span class="font-semibold">${item.total_quantity.toFixed(2)}</span>
                </td>
                <td class="text-right font-bold text-red-600">
                    $${item.total_cost.toFixed(2)}
                </td>
                <td class="text-right">
                    $${item.avg_cost_per_incident.toFixed(2)}
                </td>
                <td>
                    <span class="reason-chip">${item.primary_reason || 'Various'}</span>
                </td>
                <td>
                    <button class="action-btn" onclick="investigateItem(${item.item_id})">
                        <i class="fas fa-search"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        
        container.innerHTML = rows;
    }

    renderRecurringIssues(reasons) {
        const container = document.getElementById('recurring-issues-list');
        if (!container) return;
        
        const recurring = reasons.filter(r => r.waste_count >= 3);
        
        if (recurring.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-check-circle text-3xl text-green-500 mb-3"></i>
                    <p>No recurring issues detected</p>
                </div>
            `;
            return;
        }
        
        const issuesHtml = recurring.map(issue => `
            <div class="issue-card">
                <div class="issue-header">
                    <div class="issue-title">
                        <i class="fas fa-exclamation-triangle text-yellow-500"></i>
                        <h4>${issue.reason_name}</h4>
                    </div>
                    <span class="issue-count">${issue.waste_count} incidents</span>
                </div>
                <div class="issue-body">
                    <div class="issue-stats">
                        <div class="stat">
                            <span class="stat-label">Total Cost:</span>
                            <span class="stat-value">$${issue.total_cost.toFixed(2)}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Avg Cost:</span>
                            <span class="stat-value">$${issue.avg_cost_per_incident.toFixed(2)}</span>
                        </div>
                    </div>
                    <div class="issue-actions">
                        <button class="btn-sm btn-outline" onclick="createActionPlan(${issue.reason_id})">
                            <i class="fas fa-clipboard-list mr-1"></i> Action Plan
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = issuesHtml;
    }

    renderSuggestions(suggestions) {
        const container = document.getElementById('suggestions-list');
        if (!container) return;
        
        const defaultSuggestions = [
            'Implement portion control training for kitchen staff',
            'Review and adjust preparation quantities based on sales data',
            'Improve inventory rotation (FIFO) to reduce spoilage',
            'Monitor expiration dates more closely',
            'Train staff on proper food storage techniques'
        ];
        
        const list = suggestions.length > 0 ? suggestions : defaultSuggestions;
        
        const suggestionsHtml = list.map((suggestion, index) => `
            <div class="suggestion-card">
                <div class="suggestion-number">${index + 1}</div>
                <div class="suggestion-content">
                    <p>${suggestion}</p>
                    <div class="suggestion-actions">
                        <button class="action-link" onclick="assignTask('${suggestion}')">
                            <i class="fas fa-user-check mr-1"></i> Assign
                        </button>
                        <button class="action-link" onclick="scheduleTraining('${suggestion}')">
                            <i class="fas fa-calendar-alt mr-1"></i> Schedule
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = suggestionsHtml;
    }

    renderAlerts() {
        const container = document.getElementById('alerts-grid');
        if (!container) return;
        
        const alerts = this.data.alerts || [];
        const activeAlerts = alerts.filter(a => !a.is_resolved);
        
        if (activeAlerts.length === 0) {
            container.innerHTML = `
                <div class="alert-card no-alerts">
                    <i class="fas fa-bell-slash text-3xl text-gray-400"></i>
                    <p>No active alerts</p>
                </div>
            `;
            return;
        }
        
        const alertsHtml = activeAlerts.map(alert => `
            <div class="alert-card ${alert.alert_type}">
                <div class="alert-header">
                    <div class="alert-icon">
                        <i class="fas fa-${this.getAlertIcon(alert.alert_type)}"></i>
                    </div>
                    <div class="alert-title">
                        <h4>${alert.title}</h4>
                        <span class="alert-time">${this.formatTime(alert.created_at)}</span>
                    </div>
                </div>
                <div class="alert-body">
                    <p>${alert.message}</p>
                </div>
                <div class="alert-actions">
                    <button class="btn-sm" onclick="markAlertRead(${alert.id})">
                        Mark Read
                    </button>
                    <button class="btn-sm btn-outline" onclick="resolveAlert(${alert.id})">
                        Resolve
                    </button>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = alertsHtml;
    }

    // Utility Methods
    getItemIcon(category) {
        const icons = {
            'meat': 'drumstick-bite',
            'vegetable': 'carrot',
            'fruit': 'apple-alt',
            'dairy': 'cheese',
            'beverage': 'wine-bottle',
            'default': 'box'
        };
        return icons[category?.toLowerCase()] || icons.default;
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

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        return `${Math.floor(diffMins / 1440)}d ago`;
    }

    updateChangeIndicator() {
        // Implement comparison with previous period
        // This would require loading previous period data
    }

    changeChartType(type) {
        // Update chart type buttons
        document.querySelectorAll('.chart-action-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.chartType === type);
        });
        
        // Re-render trend chart with new type
        if (this.charts.trend && this.data.analytics.daily_trend) {
            this.charts.trend.destroy();
            if (type === 'bar') {
                this.renderBarChart(this.data.analytics.daily_trend);
            } else {
                this.renderTrendChart(this.data.analytics.daily_trend);
            }
        }
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        
        // Show/hide tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });
    }

    async refresh() {
        await this.loadDashboard();
    }

    exportData() {
        // Create CSV export
        const { analytics } = this.data;
        
        if (!analytics.summary) {
            this.showError('No data to export');
            return;
        }
        
        const csvContent = this.generateCSV(analytics);
        this.downloadCSV(csvContent, `waste-dashboard-${new Date().toISOString().split('T')[0]}.csv`);
    }

    generateCSV(data) {
        let csv = 'Waste Analytics Dashboard Report\n\n';
        
        // Summary section
        csv += 'SUMMARY\n';
        csv += 'Metric,Value\n';
        csv += `Total Waste Cost,${data.summary.total_waste_cost}\n`;
        csv += `Waste Percentage,${data.summary.waste_percentage}%\n`;
        csv += `Average Daily Waste,${data.summary.avg_daily_waste}\n`;
        csv += `Waste Count,${data.summary.waste_count}\n\n`;
        
        // Top items section
        csv += 'TOP WASTED ITEMS\n';
        csv += 'Item,Category,Quantity,Total Cost,Avg Cost,Primary Reason\n';
        (data.top_items || []).forEach(item => {
            csv += `${item.item_name},${item.category},${item.total_quantity},${item.total_cost},${item.avg_cost_per_incident},${item.primary_reason || ''}\n`;
        });
        
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

    showLoading() {
        // Show loading indicator
        const container = document.querySelector('.waste-dashboard-container');
        if (container) {
            container.classList.add('loading');
        }
    }

    hideLoading() {
        // Hide loading indicator
        const container = document.querySelector('.waste-dashboard-container');
        if (container) {
            container.classList.remove('loading');
        }
    }

    showError(message) {
        showToast(message, 'error');
    }

    async apiRequest(method, endpoint, data = null) {
        const url = `${this.apiBase}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json'
        };
        
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const csrfToken = getCookie('csrftoken');
        if (csrfToken && method !== 'GET') {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        const options = {
            method,
            headers,
            credentials: 'include'
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            
            if (response.status === 401) {
                // Token expired, redirect to login
                window.location.href = '/login/';
                return null;
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
}

// Helper functions
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
    // Implement toast notification
    alert(`${type.toUpperCase()}: ${message}`);
}

// Global functions for HTML onclick handlers
function investigateItem(itemId) {
    if (window.wasteDashboard) {
        // Open investigation modal or page
        window.location.href = `/waste/items/${itemId}/`;
    }
}

function createActionPlan(reasonId) {
    // Open action plan creation
    showToast('Action plan feature coming soon', 'info');
}

function markAlertRead(alertId) {
    fetch(`/api/waste/alerts/${alertId}/mark_read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && window.wasteDashboard) {
            window.wasteDashboard.loadAlerts();
            showToast('Alert marked as read', 'success');
        }
    });
}

function resolveAlert(alertId) {
    const notes = prompt('Enter resolution notes:');
    if (notes === null) return;
    
    fetch(`/api/waste/alerts/${alertId}/resolve/`, {
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
            window.wasteDashboard.loadAlerts();
            showToast('Alert resolved', 'success');
        }
    });
}

function assignTask(suggestion) {
    // Open task assignment modal
    showToast('Task assignment feature coming soon', 'info');
}

function scheduleTraining(suggestion) {
    // Open training scheduling
    showToast('Training scheduling feature coming soon', 'info');
}