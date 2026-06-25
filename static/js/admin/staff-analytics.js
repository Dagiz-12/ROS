// static/js/admin/staff-analytics.js
class StaffAnalytics {
    constructor() {
        this.apiBase = '/api/auth/';
        this.currentPeriod = 'week';
        this.currentRole = 'all';
        this.init();
    }

    init() {
        this.checkAuth();
        this.loadDashboard();
        this.setupEventListeners();
        this.setupAutoRefresh();
    }

    checkAuth() {
        if (typeof authManager !== 'undefined' && !authManager.isAuthenticated()) {
            window.location.href = '/login/';
        }
    }

    setupEventListeners() {
        // Period selector
        document.getElementById('period-selector')?.addEventListener('change', (e) => {
            this.currentPeriod = e.target.value;
            this.loadDashboard();
        });

        // Role selector
        document.getElementById('role-selector')?.addEventListener('change', (e) => {
            this.currentRole = e.target.value;
            this.loadDashboard();
        });

        // Refresh button
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadDashboard();
            showToast('Staff data refreshed', 'success');
        });
    }

    setupAutoRefresh() {
        // Refresh every 60 seconds
        setInterval(() => {
            this.loadDashboard();
        }, 60000);
    }

    async loadDashboard() {
        try {
            await Promise.all([
                this.loadLeaderboard(),
                this.loadStaffTable()
            ]);
            this.updateLastUpdated();
        } catch (error) {
            console.error('Staff analytics load error:', error);
            showToast('Failed to load staff data', 'error');
        }
    }

    async loadLeaderboard() {
        try {
            const url = `${this.apiBase}staff/leaderboard/?role=${this.currentRole}&limit=10`;
            const response = await fetch(url, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to load leaderboard');
            
            const data = await response.json();
            if (data.success) {
                this.renderLeaderboard(data.leaderboard);
                this.updateSummary(data.leaderboard);
            }
        } catch (error) {
            console.error('Leaderboard load error:', error);
        }
    }

    renderLeaderboard(leaderboard) {
        const container = document.getElementById('leaderboard-container');
        if (!container) return;

        if (!leaderboard || leaderboard.length === 0) {
            container.innerHTML = `
                <div class="p-8 text-center text-gray-500">
                    <i class="fas fa-users text-3xl mb-3"></i>
                    <p>No staff data available</p>
                </div>
            `;
            return;
        }

        const medals = ['🥇', '🥈', '🥉'];
        const colors = ['#dc2626', '#ea580c', '#d97706', '#3b82f6', '#8b5cf6'];
        
        const itemsHtml = leaderboard.map((staff, index) => `
            <div class="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors cursor-pointer" 
                 onclick="window.staffAnalytics?.showStaffDetail(${staff.id})">
                <div class="flex items-center flex-1 min-w-0">
                    <span class="w-8 text-center font-bold text-${index < 3 ? 'xl' : 'lg'} mr-3">
                        ${medals[index] || `#${index + 1}`}
                    </span>
                    <div class="flex-1 min-w-0">
                        <div class="font-medium text-gray-900">${staff.full_name || staff.username}</div>
                        <div class="text-sm text-gray-500">${staff.role.charAt(0).toUpperCase() + staff.role.slice(1)}</div>
                    </div>
                </div>
                <div class="flex items-center space-x-6">
                    <div class="text-right hidden sm:block">
                        <div class="text-sm text-gray-500">Orders</div>
                        <div class="font-medium">${staff.orders_handled || 0}</div>
                    </div>
                    <div class="text-right hidden md:block">
                        <div class="text-sm text-gray-500">Revenue</div>
                        <div class="font-medium">$${(staff.sales_value || 0).toFixed(2)}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-sm text-gray-500">Score</div>
                        <div class="flex items-center">
                            <div class="w-16 bg-gray-200 rounded-full h-1.5 mr-2">
                                <div class="h-1.5 rounded-full transition-all duration-500" 
                                     style="width: ${Math.min(staff.performance_score, 100)}%; background: ${colors[index % colors.length]};">
                                </div>
                            </div>
                            <span class="font-bold text-sm">${staff.performance_score.toFixed(1)}%</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = itemsHtml;
    }

    async loadStaffTable() {
        try {
            const url = `${this.apiBase}staff/performance/?period=${this.currentPeriod}&role=${this.currentRole}`;
            const response = await fetch(url, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to load staff table');
            
            const data = await response.json();
            if (data.success) {
                this.renderStaffTable(data.staff);
                this.updateSummaryCards(data.summary);
            }
        } catch (error) {
            console.error('Staff table load error:', error);
        }
    }

    renderStaffTable(staff) {
        const container = document.getElementById('staff-table-body');
        if (!container) return;

        if (!staff || staff.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-8 text-center text-gray-500">
                        <i class="fas fa-users text-3xl mb-3"></i>
                        <p>No staff members found</p>
                    </td>
                </tr>
            `;
            return;
        }

        const rows = staff.map(s => `
            <tr class="hover:bg-gray-50 transition-colors cursor-pointer" 
                onclick="window.staffAnalytics?.showStaffDetail(${s.id})">
                <td class="px-6 py-4">
                    <div class="flex items-center">
                        <div class="w-8 h-8 rounded-full flex items-center justify-center mr-3
                            ${s.role === 'waiter' ? 'bg-blue-100' : 
                              s.role === 'chef' ? 'bg-green-100' : 
                              'bg-purple-100'}">
                            <i class="fas fa-user ${s.role === 'waiter' ? 'text-blue-600' : 
                              s.role === 'chef' ? 'text-green-600' : 
                              'text-purple-600'}"></i>
                        </div>
                        <div>
                            <div class="font-medium text-gray-900">${s.full_name || s.username}</div>
                            <div class="text-xs text-gray-500">@${s.username}</div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4">
                    <span class="px-2 py-1 text-xs font-medium rounded-full
                        ${s.role === 'waiter' ? 'bg-blue-100 text-blue-800' : 
                          s.role === 'chef' ? 'bg-green-100 text-green-800' : 
                          'bg-purple-100 text-purple-800'}">
                        ${s.role.charAt(0).toUpperCase() + s.role.slice(1)}
                    </span>
                </td>
                <td class="px-6 py-4">
                    <div class="flex items-center">
                        <div class="w-24 bg-gray-200 rounded-full h-1.5 mr-2">
                            <div class="h-1.5 rounded-full transition-all duration-500
                                ${s.performance_score >= 70 ? 'bg-green-500' : 
                                  s.performance_score >= 50 ? 'bg-yellow-500' : 
                                  'bg-red-500'}"
                                style="width: ${Math.min(s.performance_score, 100)}%">
                            </div>
                        </div>
                        <span class="text-sm font-medium">${s.performance_score.toFixed(1)}%</span>
                    </div>
                </td>
                <td class="px-6 py-4">
                    <span class="font-medium">${s.orders_handled || s.orders_prepared || 0}</span>
                </td>
                <td class="px-6 py-4">
                    <span class="font-medium">$${(s.sales_value || 0).toFixed(2)}</span>
                </td>
                <td class="px-6 py-4">
                    <span class="flex items-center">
                        <span class="text-yellow-400 mr-1">★</span>
                        ${s.rating ? s.rating.toFixed(1) : '—'}
                    </span>
                </td>
                <td class="px-6 py-4">
                    <span class="text-sm capitalize">${s.current_shift || '—'}</span>
                </td>
            </tr>
        `).join('');

        container.innerHTML = rows;
    }

    updateSummaryCards(summary) {
        if (!summary) return;
        
        document.getElementById('total-staff').textContent = summary.total_staff || 0;
        document.getElementById('avg-performance').textContent = 
            summary.avg_performance ? `${summary.avg_performance.toFixed(1)}%` : '0%';
    }

    updateSummary(leaderboard) {
        if (leaderboard && leaderboard.length > 0) {
            const top = leaderboard[0];
            document.getElementById('top-performer').textContent = top.full_name || top.username;
        }
        
        // Calculate average prep time from chefs
        // This would need to be calculated from the API
    }

    async showStaffDetail(staffId) {
        try {
            const response = await fetch(`${this.apiBase}staff/${staffId}/performance/`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to load staff detail');
            
            const data = await response.json();
            if (data.success) {
                this.showStaffDetailModal(data.staff);
            }
        } catch (error) {
            console.error('Staff detail load error:', error);
            showToast('Failed to load staff details', 'error');
        }
    }

    showStaffDetailModal(staff) {
        // Create and show a modal with staff details
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div class="p-6 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <h3 class="text-lg font-bold text-gray-900">${staff.full_name || staff.username}</h3>
                        <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-gray-600">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>
                    <p class="text-sm text-gray-500">${staff.role.charAt(0).toUpperCase() + staff.role.slice(1)}</p>
                </div>
                <div class="p-6 space-y-4">
                    <div class="grid grid-cols-2 gap-4">
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <p class="text-sm text-gray-500">Performance Score</p>
                            <h4 class="text-2xl font-bold">${staff.performance_score.toFixed(1)}%</h4>
                        </div>
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <p class="text-sm text-gray-500">Rating</p>
                            <h4 class="text-2xl font-bold">${staff.rating ? staff.rating.toFixed(1) + ' ★' : '—'}</h4>
                        </div>
                        ${staff.role === 'waiter' ? `
                            <div class="bg-gray-50 p-4 rounded-lg">
                                <p class="text-sm text-gray-500">Orders Handled</p>
                                <h4 class="text-2xl font-bold">${staff.orders_handled}</h4>
                            </div>
                            <div class="bg-gray-50 p-4 rounded-lg">
                                <p class="text-sm text-gray-500">Sales Value</p>
                                <h4 class="text-2xl font-bold">$${(staff.sales_value || 0).toFixed(2)}</h4>
                            </div>
                        ` : staff.role === 'chef' ? `
                            <div class="bg-gray-50 p-4 rounded-lg">
                                <p class="text-sm text-gray-500">Orders Prepared</p>
                                <h4 class="text-2xl font-bold">${staff.orders_prepared}</h4>
                            </div>
                            <div class="bg-gray-50 p-4 rounded-lg">
                                <p class="text-sm text-gray-500">Avg Prep Time</p>
                                <h4 class="text-2xl font-bold">${staff.avg_prep_time || 0}m</h4>
                            </div>
                        ` : `
                            <div class="bg-gray-50 p-4 rounded-lg">
                                <p class="text-sm text-gray-500">Shift</p>
                                <h4 class="text-2xl font-bold capitalize">${staff.current_shift || '—'}</h4>
                            </div>
                            <div class="bg-gray-50 p-4 rounded-lg">
                                <p class="text-sm text-gray-500">Status</p>
                                <h4 class="text-2xl font-bold ${staff.is_active ? 'text-green-600' : 'text-red-600'}">
                                    ${staff.is_active ? 'Active' : 'Inactive'}
                                </h4>
                            </div>
                        `}
                    </div>
                    
                    <div class="mt-4">
                        <h4 class="font-medium text-gray-900 mb-2">Performance History</h4>
                        <div class="h-48">
                            <canvas id="staff-history-chart"></canvas>
                        </div>
                    </div>
                    
                    ${staff.recent_orders && staff.recent_orders.length > 0 ? `
                        <div>
                            <h4 class="font-medium text-gray-900 mb-2">Recent Orders</h4>
                            <div class="max-h-48 overflow-y-auto">
                                ${staff.recent_orders.map(order => `
                                    <div class="flex justify-between items-center py-2 border-b border-gray-100">
                                        <span class="font-medium">#${order.order_number}</span>
                                        <span>Table ${order.table || 'N/A'}</span>
                                        <span>$${order.total_amount.toFixed(2)}</span>
                                        <span class="text-xs text-gray-500">${new Date(order.placed_at).toLocaleDateString()}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
                <div class="p-6 border-t border-gray-200">
                    <button onclick="this.closest('.fixed').remove()" class="btn-secondary w-full">
                        Close
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Initialize chart after modal is rendered
        setTimeout(() => {
            this.createHistoryChart(staff.history);
        }, 100);
    }

    createHistoryChart(history) {
        const canvas = document.getElementById('staff-history-chart');
        if (!canvas || !history || history.length === 0) return;
        
        const ctx = canvas.getContext('2d');
        const data = history.map(h => h.performance_score || 0);
        const labels = history.map(h => {
            const date = new Date(h.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Performance Score',
                    data: data,
                    borderColor: '#dc2626',
                    backgroundColor: 'rgba(220, 38, 38, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: (value) => value + '%'
                        }
                    }
                }
            }
        });
    }

    updateLastUpdated() {
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const element = document.getElementById('leaderboard-updated');
        if (element) {
            element.textContent = `Updated ${timeString}`;
        }
    }

    getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }
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
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.staffAnalytics = new StaffAnalytics();
});

console.log('Staff Analytics JavaScript loaded');