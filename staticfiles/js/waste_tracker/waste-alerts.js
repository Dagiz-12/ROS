// static/js/waste_tracker/waste-alerts.js
class WasteAlertsManager {
    constructor() {
        this.apiBase = '/api/waste/';
        this.selectedAlerts = new Set();
        this.currentAlertId = null;
        this.init();
    }

    init() {
        this.loadAlerts();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Select all checkbox
        document.getElementById('select-all-alerts')?.addEventListener('change', (e) => {
            this.toggleSelectAll(e.target.checked);
        });

        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.filterAlerts(e.target.dataset.filter);
            });
        });
    }

    async loadAlerts() {
        try {
            this.showLoading();
            
            // Load alerts
            const response = await this.apiRequest('GET', 'alerts/');
            const alerts = response.results || [];
            
            // Load summary counts
            const summary = await this.loadAlertSummary();
            
            this.renderAlerts(alerts);
            this.updateSummary(summary);
            this.hideLoading();
            
        } catch (error) {
            console.error('Error loading alerts:', error);
            this.showError('Failed to load alerts');
            this.hideLoading();
        }
    }

    async loadAlertSummary() {
        try {
            // Get active alerts count
            const activeResponse = await this.apiRequest('GET', 'alerts/?is_resolved=false');
            
            // Get pending waste reviews
            const pendingResponse = await this.apiRequest('GET', 'records/pending_approval/');
            
            // Get recurring issues
            const recurringResponse = await this.apiRequest('GET', 'records/recurring_issues/');
            
            return {
                activeAlerts: activeResponse.count || activeResponse.results?.length || 0,
                pendingReviews: pendingResponse.count || pendingResponse.results?.length || 0,
                recurringIssues: recurringResponse.recurring_issues?.length || 0
            };
            
        } catch (error) {
            console.error('Error loading summary:', error);
            return {
                activeAlerts: 0,
                pendingReviews: 0,
                recurringIssues: 0
            };
        }
    }

    renderAlerts(alerts) {
        const container = document.getElementById('alerts-table-body');
        const emptyState = document.getElementById('empty-alerts-state');
        
        if (!alerts || alerts.length === 0) {
            if (container) container.innerHTML = '';
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }
        
        if (emptyState) emptyState.classList.add('hidden');
        
        const rows = alerts.map(alert => `
            <tr class="alert-row ${alert.is_read ? '' : 'unread'} ${alert.is_resolved ? 'resolved' : 'unresolved'}">
                <td>
                    <input type="checkbox" 
                           class="alert-checkbox" 
                           value="${alert.id}"
                           ${this.selectedAlerts.has(alert.id) ? 'checked' : ''}>
                </td>
                <td>
                    <div class="alert-type ${alert.alert_type}">
                        <i class="fas fa-${this.getAlertIcon(alert.alert_type)} mr-2"></i>
                        ${this.formatAlertType(alert.alert_type)}
                    </div>
                </td>
                <td>
                    <div class="font-medium">${alert.title}</div>
                    <div class="text-sm text-gray-500 truncate max-w-xs">${alert.message}</div>
                </td>
                <td>
                    ${alert.waste_record?.stock_item?.name || 'N/A'}
                </td>
                <td>
                    ${alert.waste_record?.total_cost ? `$${parseFloat(alert.waste_record.total_cost).toFixed(2)}` : 'N/A'}
                </td>
                <td>
                    <span class="status-badge ${alert.is_resolved ? 'status-resolved' : 'status-active'}">
                        ${alert.is_resolved ? 'Resolved' : 'Active'}
                    </span>
                    ${!alert.is_read ? '<span class="badge badge-blue ml-2">Unread</span>' : ''}
                </td>
                <td>
                    <div class="text-sm">${this.formatDate(alert.created_at)}</div>
                    <div class="text-xs text-gray-500">${this.formatTimeAgo(alert.created_at)}</div>
                </td>
                <td>
                    <div class="flex space-x-2">
                        ${!alert.is_read ? `
                        <button onclick="window.wasteAlertsManager.markAlertRead(${alert.id})" 
                                class="action-btn btn-sm btn-outline"
                                title="Mark as read">
                            <i class="fas fa-check"></i>
                        </button>
                        ` : ''}
                        
                        ${!alert.is_resolved ? `
                        <button onclick="window.wasteAlertsManager.openResolveModal(${alert.id})" 
                                class="action-btn btn-sm btn-success"
                                title="Resolve alert">
                            <i class="fas fa-check-circle"></i>
                        </button>
                        ` : ''}
                        
                        <button onclick="window.wasteAlertsManager.viewAlertDetails(${alert.id})" 
                                class="action-btn btn-sm btn-primary"
                                title="View details">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
        
        if (container) container.innerHTML = rows;
        
        // Add checkbox event listeners
        this.setupCheckboxListeners();
    }

    updateSummary(summary) {
        document.getElementById('active-alerts-count').textContent = summary.activeAlerts;
        document.getElementById('pending-reviews-count').textContent = summary.pendingReviews;
        document.getElementById('recurring-issues-count').textContent = summary.recurringIssues;
        
        // Update trend (would need historical data)
        document.getElementById('trend-count').textContent = '—';
    }

    // Utility Methods
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

    formatAlertType(type) {
        const types = {
            'threshold_exceeded': 'Threshold',
            'recurring_issue': 'Recurring',
            'approval_needed': 'Approval',
            'target_at_risk': 'Target'
        };
        return types[type] || type;
    }

    formatDate(timestamp) {
        if (!timestamp) return 'N/A';
        return new Date(timestamp).toLocaleDateString();
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

    // Selection Methods
    setupCheckboxListeners() {
        document.querySelectorAll('.alert-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const alertId = parseInt(e.target.value);
                if (e.target.checked) {
                    this.selectedAlerts.add(alertId);
                } else {
                    this.selectedAlerts.delete(alertId);
                }
                this.updateBulkActions();
            });
        });
    }

    toggleSelectAll(checked) {
        const checkboxes = document.querySelectorAll('.alert-checkbox');
        this.selectedAlerts.clear();
        
        checkboxes.forEach(checkbox => {
            checkbox.checked = checked;
            if (checked) {
                this.selectedAlerts.add(parseInt(checkbox.value));
            }
        });
        
        this.updateBulkActions();
    }

    updateBulkActions() {
        const bulkActions = document.getElementById('bulk-actions');
        const selectedCount = document.getElementById('selected-count');
        
        if (this.selectedAlerts.size > 0) {
            if (bulkActions) bulkActions.classList.remove('hidden');
            if (selectedCount) selectedCount.textContent = this.selectedAlerts.size;
        } else {
            if (bulkActions) bulkActions.classList.add('hidden');
        }
    }

    // Action Methods
    async markAlertRead(alertId) {
        try {
            await this.apiRequest('POST', `alerts/${alertId}/mark_read/`);
            this.showSuccess('Alert marked as read');
            this.loadAlerts();
        } catch (error) {
            console.error('Error marking alert read:', error);
            this.showError('Failed to mark alert as read');
        }
    }

    async markSelectedRead() {
        if (this.selectedAlerts.size === 0) return;
        
        try {
            const promises = Array.from(this.selectedAlerts).map(alertId =>
                this.apiRequest('POST', `alerts/${alertId}/mark_read/`)
            );
            
            await Promise.all(promises);
            this.showSuccess(`${this.selectedAlerts.size} alerts marked as read`);
            this.selectedAlerts.clear();
            this.loadAlerts();
        } catch (error) {
            console.error('Error marking alerts read:', error);
            this.showError('Failed to mark alerts as read');
        }
    }

    openResolveModal(alertId) {
        this.currentAlertId = alertId;
        document.getElementById('resolve-modal').classList.remove('hidden');
    }

    closeResolveModal() {
        this.currentAlertId = null;
        document.getElementById('resolve-modal').classList.add('hidden');
        document.getElementById('resolve-notes').value = '';
    }

    async confirmResolve() {
        if (!this.currentAlertId) return;
        
        const notes = document.getElementById('resolve-notes').value.trim();
        if (!notes) {
            this.showError('Please provide resolution notes');
            return;
        }
        
        try {
            await this.apiRequest('POST', `alerts/${this.currentAlertId}/resolve/`, {
                notes: notes
            });
            
            this.showSuccess('Alert resolved successfully');
            this.closeResolveModal();
            this.loadAlerts();
        } catch (error) {
            console.error('Error resolving alert:', error);
            this.showError('Failed to resolve alert');
        }
    }

    async resolveSelected() {
        if (this.selectedAlerts.size === 0) return;
        
        const notes = prompt('Enter resolution notes for all selected alerts:');
        if (!notes) return;
        
        try {
            const promises = Array.from(this.selectedAlerts).map(alertId =>
                this.apiRequest('POST', `alerts/${alertId}/resolve/`, { notes: notes })
            );
            
            await Promise.all(promises);
            this.showSuccess(`${this.selectedAlerts.size} alerts resolved`);
            this.selectedAlerts.clear();
            this.loadAlerts();
        } catch (error) {
            console.error('Error resolving alerts:', error);
            this.showError('Failed to resolve alerts');
        }
    }

    viewAlertDetails(alertId) {
        window.location.href = `/waste/alerts/${alertId}/`;
    }

    filterAlerts(filter) {
        // Update filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filter);
        });
        
        // Filter logic would be implemented here
        // For now, reload with filter parameter
        this.loadAlerts();
    }

    async runAlertChecks() {
        try {
            this.showLoading('Running alert checks...');
            
            const response = await this.apiRequest('POST', 'alerts/run-checks/');
            
            if (response.success) {
                this.showSuccess(`Alert checks completed. Created ${response.total_alerts_created} new alerts.`);
                this.loadAlerts();
            }
        } catch (error) {
            console.error('Error running alert checks:', error);
            this.showError('Failed to run alert checks');
        } finally {
            this.hideLoading();
        }
    }

    clearSelection() {
        this.selectedAlerts.clear();
        document.querySelectorAll('.alert-checkbox').forEach(cb => cb.checked = false);
        document.getElementById('select-all-alerts').checked = false;
        this.updateBulkActions();
    }

    // UI Helpers
    showLoading(message = 'Loading...') {
        // Implement loading indicator
        console.log(message);
    }

    hideLoading() {
        // Hide loading indicator
    }

    showSuccess(message) {
        alert(`Success: ${message}`);
    }

    showError(message) {
        alert(`Error: ${message}`);
    }

    // API Helper
    async apiRequest(method, endpoint, data = null) {
        const url = `${this.apiBase}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json'
        };
        
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const csrfToken = this.getCsrfToken();
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

    getCsrfToken() {
        // Get CSRF token from cookie or meta tag
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.wasteAlertsManager = new WasteAlertsManager();
});

// Global functions for HTML onclick handlers
function runAlertChecks() {
    if (window.wasteAlertsManager) {
        window.wasteAlertsManager.runAlertChecks();
    }
}

function markAllRead() {
    if (window.wasteAlertsManager) {
        // Select all alerts and mark them read
        const checkboxes = document.querySelectorAll('.alert-checkbox');
        checkboxes.forEach(cb => cb.checked = true);
        
        const alertIds = Array.from(checkboxes).map(cb => parseInt(cb.value));
        window.wasteAlertsManager.selectedAlerts = new Set(alertIds);
        window.wasteAlertsManager.markSelectedRead();
    }
}