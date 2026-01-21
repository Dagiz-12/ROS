// static/js/waste_tracker/waste-reports.js
class WasteReportsManager {
    constructor() {
        this.apiBase = '/api/waste/';
        this.currentPeriod = 'month';
        this.currentReport = null;
        this.init();
    }

    init() {
        this.loadReportTypes();
        this.setupEventListeners();
        this.setupDatePicker();
    }

    setupEventListeners() {
        // Report type selection
        document.getElementById('report-type')?.addEventListener('change', (e) => {
            this.currentReport = e.target.value;
            this.updateReportForm();
        });

        // Generate report button
        document.getElementById('generate-report')?.addEventListener('click', () => {
            this.generateReport();
        });

        // Period selector
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.currentPeriod = e.target.dataset.period;
                this.updatePeriodSelection();
                this.loadRecentReports();
            });
        });

        // Export buttons
        document.getElementById('export-csv')?.addEventListener('click', () => {
            this.exportReport('csv');
        });

        document.getElementById('export-pdf')?.addEventListener('click', () => {
            this.exportReport('pdf');
        });
    }

    setupDatePicker() {
        const startDate = document.getElementById('start-date');
        const endDate = document.getElementById('end-date');
        
        if (startDate && endDate) {
            startDate.max = new Date().toISOString().split('T')[0];
            endDate.max = new Date().toISOString().split('T')[0];
            endDate.min = startDate.value;
            
            startDate.addEventListener('change', () => {
                endDate.min = startDate.value;
                if (endDate.value < startDate.value) {
                    endDate.value = startDate.value;
                }
            });
        }
    }

    async loadReportTypes() {
        try {
            const response = await this.apiRequest('GET', 'reports/types/');
            if (response.success) {
                this.renderReportTypes(response.types);
            }
        } catch (error) {
            console.error('Error loading report types:', error);
        }
    }

    renderReportTypes(types) {
        const select = document.getElementById('report-type');
        if (!select || !types) return;

        select.innerHTML = `
            <option value="">Select Report Type</option>
            ${types.map(type => `
                <option value="${type.id}">${type.name}</option>
            `).join('')}
        `;
    }

    updateReportForm() {
        const customFields = document.getElementById('custom-fields');
        if (!customFields) return;

        // Show different fields based on report type
        const fields = this.getReportFields(this.currentReport);
        
        if (fields.length > 0) {
            customFields.innerHTML = fields.map(field => `
                <div class="form-group">
                    <label>${field.label}</label>
                    ${this.renderFieldInput(field)}
                </div>
            `).join('');
            customFields.classList.remove('hidden');
        } else {
            customFields.classList.add('hidden');
        }
    }

    getReportFields(reportType) {
        const fieldDefinitions = {
            'daily_summary': [
                { name: 'include_charts', label: 'Include Charts', type: 'checkbox', default: true },
                { name: 'show_trends', label: 'Show Trends', type: 'checkbox', default: true }
            ],
            'category_analysis': [
                { name: 'group_by', label: 'Group By', type: 'select', options: ['day', 'week', 'month'], default: 'day' },
                { name: 'show_comparison', label: 'Show Comparison', type: 'checkbox', default: true }
            ],
            'station_performance': [
                { name: 'stations', label: 'Select Stations', type: 'multiselect', default: 'all' },
                { name: 'metric', label: 'Performance Metric', type: 'select', options: ['cost', 'quantity', 'efficiency'], default: 'cost' }
            ],
            'staff_performance': [
                { name: 'staff_role', label: 'Staff Role', type: 'select', options: ['all', 'chef', 'cook', 'prep'], default: 'all' },
                { name: 'show_individuals', label: 'Show Individual Performance', type: 'checkbox', default: false }
            ]
        };

        return fieldDefinitions[reportType] || [];
    }

    renderFieldInput(field) {
        switch(field.type) {
            case 'checkbox':
                return `<input type="checkbox" name="${field.name}" id="${field.name}" ${field.default ? 'checked' : ''} class="mr-2">`;
            
            case 'select':
                return `
                    <select name="${field.name}" id="${field.name}" class="w-full p-2 border rounded">
                        ${field.options.map(opt => `
                            <option value="${opt}" ${opt === field.default ? 'selected' : ''}>${opt}</option>
                        `).join('')}
                    </select>
                `;
            
            case 'multiselect':
                return `<select name="${field.name}" id="${field.name}" multiple class="w-full p-2 border rounded">
                    <option value="all" selected>All Stations</option>
                    <option value="grill">Grill</option>
                    <option value="fryer">Fryer</option>
                    <option value="prep">Prep Station</option>
                    <option value="salad">Salad Station</option>
                </select>`;
            
            default:
                return `<input type="text" name="${field.name}" id="${field.name}" class="w-full p-2 border rounded">`;
        }
    }

    async generateReport() {
        const reportType = document.getElementById('report-type')?.value;
        const startDate = document.getElementById('start-date')?.value;
        const endDate = document.getElementById('end-date')?.value;

        if (!reportType || !startDate || !endDate) {
            this.showError('Please fill all required fields');
            return;
        }

        const formData = {
            report_type: reportType,
            start_date: startDate,
            end_date: endDate
        };

        // Collect custom fields
        const customFields = document.querySelectorAll('#custom-fields input, #custom-fields select');
        customFields.forEach(field => {
            if (field.type === 'checkbox') {
                formData[field.name] = field.checked;
            } else if (field.multiple) {
                formData[field.name] = Array.from(field.selectedOptions).map(opt => opt.value);
            } else {
                formData[field.name] = field.value;
            }
        });

        try {
            this.showLoading('Generating report...');
            
            const response = await this.apiRequest('POST', 'reports/generate/', formData);
            
            if (response.success) {
                this.showSuccess('Report generated successfully');
                this.displayReport(response.report);
                this.saveToRecentReports(response.report);
                this.loadRecentReports();
            }
        } catch (error) {
            console.error('Error generating report:', error);
            this.showError('Failed to generate report');
        } finally {
            this.hideLoading();
        }
    }

    displayReport(report) {
        const preview = document.getElementById('report-preview');
        if (!preview) return;

        preview.innerHTML = `
            <div class="bg-white p-6 rounded-lg shadow">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-bold">${report.title}</h3>
                    <span class="text-sm text-gray-500">${report.generated_at}</span>
                </div>
                
                <div class="mb-4">
                    <div class="grid grid-cols-3 gap-4 mb-4">
                        <div class="stat-box">
                            <div class="stat-label">Total Waste Cost</div>
                            <div class="stat-value">$${parseFloat(report.total_cost).toFixed(2)}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Records</div>
                            <div class="stat-value">${report.total_records}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Average Daily</div>
                            <div class="stat-value">$${parseFloat(report.average_daily_cost).toFixed(2)}</div>
                        </div>
                    </div>
                </div>
                
                ${report.summary ? `
                <div class="mb-4">
                    <h4 class="font-semibold mb-2">Summary</h4>
                    <p class="text-gray-600">${report.summary}</p>
                </div>
                ` : ''}
                
                ${report.recommendations ? `
                <div class="mb-4">
                    <h4 class="font-semibold mb-2">Recommendations</h4>
                    <ul class="list-disc pl-5 text-gray-600">
                        ${report.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}
                
                <div class="mt-4 flex space-x-2">
                    <button onclick="window.wasteReportsManager.downloadReport('${report.id}')" 
                            class="btn btn-primary">
                        <i class="fas fa-download mr-2"></i>Download Report
                    </button>
                    <button onclick="window.wasteReportsManager.printReport()" 
                            class="btn btn-secondary">
                        <i class="fas fa-print mr-2"></i>Print
                    </button>
                </div>
            </div>
        `;
    }

    async loadRecentReports() {
        try {
            const response = await this.apiRequest('GET', `reports/recent/?period=${this.currentPeriod}`);
            
            if (response.success) {
                this.renderRecentReports(response.reports);
            }
        } catch (error) {
            console.error('Error loading recent reports:', error);
        }
    }

    renderRecentReports(reports) {
        const container = document.getElementById('recent-reports');
        if (!container) return;

        if (!reports || reports.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-file-alt text-3xl mb-3"></i>
                    <p>No reports generated yet</p>
                </div>
            `;
            return;
        }

        container.innerHTML = reports.map(report => `
            <div class="report-item border-b border-gray-200 py-3">
                <div class="flex justify-between items-center">
                    <div>
                        <div class="font-medium">${report.title}</div>
                        <div class="text-sm text-gray-500">
                            ${report.period} • Generated: ${report.generated_at}
                        </div>
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="window.wasteReportsManager.viewReport('${report.id}')" 
                                class="btn btn-sm btn-outline">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button onclick="window.wasteReportsManager.downloadReport('${report.id}')" 
                                class="btn btn-sm btn-primary">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    saveToRecentReports(report) {
        // This would typically be handled server-side
        console.log('Report saved:', report);
    }

    async downloadReport(reportId) {
        try {
            window.open(`${this.apiBase}reports/${reportId}/download/`, '_blank');
        } catch (error) {
            console.error('Error downloading report:', error);
            this.showError('Failed to download report');
        }
    }

    async viewReport(reportId) {
        try {
            const response = await this.apiRequest('GET', `reports/${reportId}/`);
            if (response.success) {
                this.displayReport(response.report);
            }
        } catch (error) {
            console.error('Error viewing report:', error);
            this.showError('Failed to load report');
        }
    }

    async exportReport(format) {
        if (!this.currentReport) {
            this.showError('Please generate a report first');
            return;
        }

        try {
            this.showLoading(`Exporting to ${format.toUpperCase()}...`);
            
            const response = await this.apiRequest('POST', 'reports/export/', {
                report_id: this.currentReport.id,
                format: format
            });
            
            if (response.success) {
                this.showSuccess(`Report exported as ${format.toUpperCase()}`);
                
                // Trigger download
                const link = document.createElement('a');
                link.href = response.download_url;
                link.download = `waste-report-${new Date().toISOString().split('T')[0]}.${format}`;
                link.click();
            }
        } catch (error) {
            console.error('Error exporting report:', error);
            this.showError('Failed to export report');
        } finally {
            this.hideLoading();
        }
    }

    printReport() {
        window.print();
    }

    updatePeriodSelection() {
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.period === this.currentPeriod);
        });
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
    window.wasteReportsManager = new WasteReportsManager();
});