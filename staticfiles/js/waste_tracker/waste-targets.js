// static/js/waste_tracker/waste-targets.js
class WasteTargetsManager {
    constructor() {
        this.apiBase = '/api/waste/';
        this.currentTarget = null;
        this.init();
    }

    init() {
        this.loadTargets();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Create target button
        document.getElementById('create-target')?.addEventListener('click', () => {
            this.openCreateModal();
        });

        // Period filter
        document.getElementById('period-filter')?.addEventListener('change', (e) => {
            this.loadTargets(e.target.value);
        });

        // Target status filter
        document.getElementById('status-filter')?.addEventListener('change', (e) => {
            this.filterTargetsByStatus(e.target.value);
        });
    }

    async loadTargets(period = 'all') {
        try {
            this.showLoading('Loading targets...');
            
            const endpoint = period === 'all' ? 'targets/' : `targets/?period=${period}`;
            const response = await this.apiRequest('GET', endpoint);
            
            if (response.success) {
                this.renderTargets(response.targets);
                this.renderProgressSummary(response.summary);
            }
        } catch (error) {
            console.error('Error loading targets:', error);
            this.showError('Failed to load targets');
        } finally {
            this.hideLoading();
        }
    }

    renderTargets(targets) {
        const container = document.getElementById('targets-container');
        if (!container) return;

        if (!targets || targets.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-bullseye text-4xl text-gray-300 mb-4"></i>
                    <h3 class="text-lg font-medium text-gray-700">No waste targets set</h3>
                    <p class="text-gray-500">Create your first waste reduction target to start tracking progress.</p>
                    <button onclick="window.wasteTargetsManager.openCreateModal()" 
                            class="mt-4 btn btn-primary">
                        <i class="fas fa-plus mr-2"></i>Create Target
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = targets.map(target => `
            <div class="target-card ${this.getTargetStatusClass(target)}">
                <div class="target-header">
                    <div class="target-title">
                        <h3>${target.name}</h3>
                        <span class="target-period">${this.formatPeriod(target.period)}</span>
                    </div>
                    <div class="target-actions">
                        <button onclick="window.wasteTargetsManager.editTarget(${target.id})" 
                                class="btn btn-sm btn-outline mr-2">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button onclick="window.wasteTargetsManager.deleteTarget(${target.id})" 
                                class="btn btn-sm btn-danger">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                
                <div class="target-body">
                    <div class="target-metrics">
                        <div class="metric">
                            <div class="metric-label">Target</div>
                            <div class="metric-value">$${parseFloat(target.target_value).toFixed(2)}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Current</div>
                            <div class="metric-value">$${parseFloat(target.current_value).toFixed(2)}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Progress</div>
                            <div class="metric-value ${target.progress >= 0 ? 'text-green-600' : 'text-red-600'}">
                                ${target.progress >= 0 ? '+' : ''}${target.progress.toFixed(1)}%
                            </div>
                        </div>
                    </div>
                    
                    <div class="progress-bar-container">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${Math.min(Math.max(target.completion_percentage, 0), 100)}%"></div>
                        </div>
                        <div class="progress-labels">
                            <span>$${parseFloat(target.current_value).toFixed(2)}</span>
                            <span>$${parseFloat(target.target_value).toFixed(2)}</span>
                        </div>
                    </div>
                    
                    <div class="target-details">
                        <div class="detail">
                            <i class="fas fa-calendar"></i>
                            <span>${target.start_date} - ${target.end_date}</span>
                        </div>
                        <div class="detail">
                            <i class="fas fa-chart-line"></i>
                            <span>${target.target_type.replace('_', ' ')} target</span>
                        </div>
                        <div class="detail">
                            <i class="fas fa-user"></i>
                            <span>Created by: ${target.created_by}</span>
                        </div>
                    </div>
                    
                    ${target.description ? `
                    <div class="target-description">
                        <p>${target.description}</p>
                    </div>
                    ` : ''}
                </div>
                
                <div class="target-footer">
                    <span class="target-status ${this.getTargetStatusClass(target)}">
                        ${this.getTargetStatusText(target)}
                    </span>
                    <span class="target-days-left">
                        ${this.getDaysLeft(target.end_date)} days left
                    </span>
                </div>
            </div>
        `).join('');
    }

    renderProgressSummary(summary) {
        const summaryEl = document.getElementById('progress-summary');
        if (!summaryEl || !summary) return;

        summaryEl.innerHTML = `
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-icon bg-green-100">
                        <i class="fas fa-check-circle text-green-600"></i>
                    </div>
                    <div class="summary-content">
                        <div class="summary-value">${summary.on_track}</div>
                        <div class="summary-label">On Track</div>
                    </div>
                </div>
                
                <div class="summary-item">
                    <div class="summary-icon bg-yellow-100">
                        <i class="fas fa-exclamation-triangle text-yellow-600"></i>
                    </div>
                    <div class="summary-content">
                        <div class="summary-value">${summary.at_risk}</div>
                        <div class="summary-label">At Risk</div>
                    </div>
                </div>
                
                <div class="summary-item">
                    <div class="summary-icon bg-red-100">
                        <i class="fas fa-times-circle text-red-600"></i>
                    </div>
                    <div class="summary-content">
                        <div class="summary-value">${summary.off_track}</div>
                        <div class="summary-label">Off Track</div>
                    </div>
                </div>
                
                <div class="summary-item">
                    <div class="summary-icon bg-blue-100">
                        <i class="fas fa-chart-line text-blue-600"></i>
                    </div>
                    <div class="summary-content">
                        <div class="summary-value">$${parseFloat(summary.total_savings).toFixed(2)}</div>
                        <div class="summary-label">Total Savings</div>
                    </div>
                </div>
            </div>
        `;
    }

    openCreateModal() {
        // Show create target modal
        const modal = document.getElementById('create-target-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.resetForm();
        }
    }

    closeCreateModal() {
        const modal = document.getElementById('create-target-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        this.currentTarget = null;
    }

    async createTarget() {
        const form = document.getElementById('target-form');
        if (!form) return;

        const formData = new FormData(form);
        const targetData = {
            name: formData.get('name'),
            target_type: formData.get('target_type'),
            period: formData.get('period'),
            target_value: parseFloat(formData.get('target_value')),
            start_date: formData.get('start_date'),
            end_date: formData.get('end_date'),
            description: formData.get('description'),
            alert_threshold: parseFloat(formData.get('alert_threshold')) || 10
        };

        try {
            this.showLoading('Creating target...');
            
            const response = await this.apiRequest('POST', 'targets/', targetData);
            
            if (response.success) {
                this.showSuccess('Target created successfully');
                this.closeCreateModal();
                this.loadTargets();
            }
        } catch (error) {
            console.error('Error creating target:', error);
            this.showError('Failed to create target');
        } finally {
            this.hideLoading();
        }
    }

    async editTarget(targetId) {
        try {
            this.showLoading('Loading target...');
            
            const response = await this.apiRequest('GET', `targets/${targetId}/`);
            
            if (response.success) {
                this.currentTarget = response.target;
                this.openEditModal(response.target);
            }
        } catch (error) {
            console.error('Error loading target:', error);
            this.showError('Failed to load target');
        } finally {
            this.hideLoading();
        }
    }

    openEditModal(target) {
        const modal = document.getElementById('create-target-modal');
        const form = document.getElementById('target-form');
        
        if (!modal || !form) return;

        // Populate form
        document.getElementById('target-name').value = target.name;
        document.getElementById('target-type').value = target.target_type;
        document.getElementById('target-period').value = target.period;
        document.getElementById('target-value').value = target.target_value;
        document.getElementById('start-date').value = target.start_date;
        document.getElementById('end-date').value = target.end_date;
        document.getElementById('target-description').value = target.description || '';
        document.getElementById('alert-threshold').value = target.alert_threshold || 10;

        // Update modal title
        document.querySelector('#create-target-modal .modal-title').textContent = 'Edit Target';
        
        modal.classList.remove('hidden');
    }

    async updateTarget() {
        if (!this.currentTarget) return;

        const form = document.getElementById('target-form');
        const formData = new FormData(form);
        
        const updateData = {
            name: formData.get('name'),
            target_type: formData.get('target_type'),
            period: formData.get('period'),
            target_value: parseFloat(formData.get('target_value')),
            start_date: formData.get('start_date'),
            end_date: formData.get('end_date'),
            description: formData.get('description'),
            alert_threshold: parseFloat(formData.get('alert_threshold')) || 10
        };

        try {
            this.showLoading('Updating target...');
            
            const response = await this.apiRequest('PUT', `targets/${this.currentTarget.id}/`, updateData);
            
            if (response.success) {
                this.showSuccess('Target updated successfully');
                this.closeCreateModal();
                this.loadTargets();
            }
        } catch (error) {
            console.error('Error updating target:', error);
            this.showError('Failed to update target');
        } finally {
            this.hideLoading();
        }
    }

    async deleteTarget(targetId) {
        if (!confirm('Are you sure you want to delete this target?')) return;

        try {
            this.showLoading('Deleting target...');
            
            const response = await this.apiRequest('DELETE', `targets/${targetId}/`);
            
            if (response.success) {
                this.showSuccess('Target deleted successfully');
                this.loadTargets();
            }
        } catch (error) {
            console.error('Error deleting target:', error);
            this.showError('Failed to delete target');
        } finally {
            this.hideLoading();
        }
    }

    filterTargetsByStatus(status) {
        const targets = document.querySelectorAll('.target-card');
        targets.forEach(target => {
            const shouldShow = status === 'all' || target.classList.contains(status);
            target.style.display = shouldShow ? 'block' : 'none';
        });
    }

    // Helper methods
    getTargetStatusClass(target) {
        if (target.completion_percentage >= 100) return 'status-completed';
        if (target.progress >= 0) return 'status-on-track';
        if (target.days_left < 7 && target.completion_percentage < 80) return 'status-at-risk';
        return 'status-off-track';
    }

    getTargetStatusText(target) {
        if (target.completion_percentage >= 100) return 'Completed';
        if (target.progress >= 0) return 'On Track';
        if (target.days_left < 7 && target.completion_percentage < 80) return 'At Risk';
        return 'Off Track';
    }

    formatPeriod(period) {
        const periods = {
            'daily': 'Daily',
            'weekly': 'Weekly',
            'monthly': 'Monthly',
            'quarterly': 'Quarterly',
            'yearly': 'Yearly'
        };
        return periods[period] || period;
    }

    getDaysLeft(endDate) {
        const end = new Date(endDate);
        const today = new Date();
        const diffTime = end - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return Math.max(diffDays, 0);
    }

    resetForm() {
        const form = document.getElementById('target-form');
        if (form) {
            form.reset();
            
            // Set default end date to 30 days from now
            const endDate = new Date();
            endDate.setDate(endDate.getDate() + 30);
            document.getElementById('end-date').value = endDate.toISOString().split('T')[0];
            
            // Update modal title
            document.querySelector('#create-target-modal .modal-title').textContent = 'Create New Target';
        }
    }

    // Utility methods
    showLoading(message) {
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
            
            return await response.json();
        } catch (error) {
            console.error(`API Error:`, error);
            throw error;
        }
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.wasteTargetsManager = new WasteTargetsManager();
});