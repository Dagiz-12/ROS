// static/js/admin/menu.js
class MenuManager {
    constructor() {
        this.apiBase = '/restaurant-admin/api/menu/';
        this.selectedItems = new Set();
        this.currentCategoryFilter = 'all';
        this.currentStatusFilter = 'all';
        this.init();
    }

    init() {

        

        this.setupEventListeners();
        this.setupFilters();
        this.setupSelectAll();
        this.setupProfitCalculator();
        this.loadCategories();
        this.loadMenuItems();
    }

    setupEventListeners() {
        // Refresh categories
        document.getElementById('refresh-categories')?.addEventListener('click', () => {
            this.loadCategories();
        });

        // Export/Import buttons
        document.getElementById('export-menu')?.addEventListener('click', () => {
            this.exportMenu();
        });

        document.getElementById('import-menu')?.addEventListener('click', () => {
            this.importMenu();
        });

        // Bulk action apply
        document.getElementById('apply-bulk-action')?.addEventListener('click', () => {
            this.applyBulkAction();
        });

        // Clear selection
        document.getElementById('clear-selection')?.addEventListener('click', () => {
            this.clearSelection();
        });
    }

    setupFilters() {
        // Category filter
        const categoryFilter = document.getElementById('category-filter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.currentCategoryFilter = e.target.value;
                this.filterItems();
            });
        }

        // Status filter
        const statusFilter = document.getElementById('status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.currentStatusFilter = e.target.value;
                this.filterItems();
            });
        }

        // Search filter
        const searchInput = document.getElementById('search-items');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchItems(e.target.value);
            });
        }
    }

    setupSelectAll() {
        const selectAll = document.getElementById('select-all-items');
        if (selectAll) {
            selectAll.addEventListener('change', (e) => {
                const checkboxes = document.querySelectorAll('.item-checkbox');
                checkboxes.forEach(checkbox => {
                    checkbox.checked = e.target.checked;
                    this.updateSelectedItem(checkbox.value, checkbox.checked);
                });
                this.updateSelectedCount();
            });

            // Individual checkboxes
            document.addEventListener('change', (e) => {
                if (e.target.classList.contains('item-checkbox')) {
                    this.updateSelectedItem(e.target.value, e.target.checked);
                    this.updateSelectedCount();
                }
            });
        }
    }

    setupProfitCalculator() {
        // Auto-calculate profit when price or cost changes
        const priceInput = document.getElementById('item-price');
        const costInput = document.getElementById('item-cost');

        if (priceInput && costInput) {
            const calculateProfit = () => {
                const price = parseFloat(priceInput.value) || 0;
                const cost = parseFloat(costInput.value) || 0;
                
                if (price > 0 && cost >= 0) {
                    const profit = price - cost;
                    const margin = (profit / price) * 100;
                    
                    // Update preview
                    const preview = document.getElementById('profit-preview');
                    if (preview) {
                        preview.classList.remove('hidden');
                        document.getElementById('preview-profit').textContent = 
                            `$${profit.toFixed(2)}`;
                        document.getElementById('preview-margin').textContent = 
                            `${margin.toFixed(1)}%`;
                        
                        // Recommendation
                        const recommendation = document.getElementById('preview-recommendation');
                        if (margin >= 60) {
                            recommendation.textContent = 'Excellent!';
                            recommendation.className = 'text-sm font-medium text-green-600';
                        } else if (margin >= 40) {
                            recommendation.textContent = 'Good';
                            recommendation.className = 'text-sm font-medium text-green-600';
                        } else if (margin >= 20) {
                            recommendation.textContent = 'Low';
                            recommendation.className = 'text-sm font-medium text-yellow-600';
                        } else {
                            recommendation.textContent = 'Very Low';
                            recommendation.className = 'text-sm font-medium text-red-600';
                        }
                    }
                }
            };

            priceInput.addEventListener('input', calculateProfit);
            costInput.addEventListener('input', calculateProfit);
        }
    }

    // ========== CATEGORY FUNCTIONS ==========

    openAddCategoryModal() {
        document.getElementById('category-modal-title').textContent = 'Add New Category';
        document.getElementById('category-form').reset();
        document.getElementById('category-id').value = '';
        document.getElementById('category-modal').classList.remove('hidden');
    }

    async openEditCategoryModal(categoryId) {
        try {
            const response = await fetch(`${this.apiBase}categories/${categoryId}/`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to fetch category');
            
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Failed to load category');
            
            const category = result.category;
            
            document.getElementById('category-modal-title').textContent = 'Edit Category';
            document.getElementById('category-id').value = category.id;
            document.getElementById('category-name').value = category.name;
            document.getElementById('category-description').value = category.description || '';
            document.getElementById('category-order').value = category.order_index;
            document.getElementById('category-status').value = category.is_active.toString();
            document.getElementById('category-modal').classList.remove('hidden');
            
        } catch (error) {
            showError('Failed to load category data');
            console.error('Error loading category:', error);
        }
    }

    closeCategoryModal() {
        document.getElementById('category-modal').classList.add('hidden');
    }

    async saveCategory() {
    const form = document.getElementById('category-form');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const categoryData = {
        name: document.getElementById('category-name').value,
        description: document.getElementById('category-description').value,
        order_index: parseInt(document.getElementById('category-order').value) || 0,
        is_active: document.getElementById('category-status').value === 'true'
    };

    const categoryId = document.getElementById('category-id').value;
    const isEdit = categoryId !== '';

    try {
        const url = isEdit ? `${this.apiBase}categories/${categoryId}/` : `${this.apiBase}categories/`;
        const method = isEdit ? 'PUT' : 'POST';

        const headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
            'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ''
        };

        const response = await fetch(url, {
            method: method,
            headers: headers,
            body: JSON.stringify(categoryData)
        });

        // Check if response is JSON before parsing
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response (likely CSRF error):', text.substring(0, 200));
            throw new Error('Server returned HTML error page. Check CSRF token.');
        }

        const result = await response.json();
        
        if (response.ok && result.success) {
            this.closeCategoryModal();
            await this.loadCategories();
            showSuccess(`Category ${isEdit ? 'updated' : 'created'} successfully`);
        } else {
            throw new Error(result.error || 'Failed to save category');
        }
    } catch (error) {
        console.error('Error saving category:', error);
        showError(error.message || 'Failed to save category');
    }
}

    async deleteCategory(categoryId) {
        showConfirm('Are you sure you want to delete this category?', async () => {
            try {
                const response = await fetch(`${this.apiBase}categories/${categoryId}/`, {
                    method: 'DELETE',
                    headers: this.getAuthHeaders()
                });

                const result = await response.json();
                
                if (response.ok && result.success) {
                    await this.loadCategories();
                    showSuccess('Category deleted successfully');
                } else {
                    throw new Error(result.error || 'Failed to delete category');
                }
            } catch (error) {
                showError(error.message || 'Failed to delete category');
                console.error('Error deleting category:', error);
            }
        });
    }

    // ========== MENU ITEM FUNCTIONS ==========

    openAddItemModal() {
        document.getElementById('menu-item-modal-title').textContent = 'Add New Menu Item';
        document.getElementById('menu-item-form').reset();
        document.getElementById('menu-item-id').value = '';
        document.getElementById('profit-preview').classList.add('hidden');
        
        // Clear image preview
        const preview = document.getElementById('image-preview');
        if (preview) {
            preview.innerHTML = '<div class="w-32 h-32 bg-gray-200 rounded-lg flex items-center justify-center mx-auto">' +
                               '<i class="fas fa-image text-gray-400 text-2xl"></i>' +
                               '</div>';
        }
        
        this.populateCategorySelect();
        document.getElementById('menu-item-modal').classList.remove('hidden');
    }

    async editMenuItem(itemId) {
        try {
            const response = await fetch(`${this.apiBase}items/${itemId}/`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to fetch item');
            
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Failed to load item');
            
            const item = result.item;
            
            // Populate form
            document.getElementById('menu-item-modal-title').textContent = 'Edit Menu Item';
            document.getElementById('menu-item-id').value = item.id;
            document.getElementById('item-name').value = item.name;
            document.getElementById('item-description').value = item.description || '';
            document.getElementById('item-category').value = item.category;
            document.getElementById('item-price').value = item.price;
            document.getElementById('item-cost').value = item.cost_price || '';
            document.getElementById('item-prep-time').value = item.preparation_time;
            
            // Set status
            const statusValue = item.is_available.toString();
            const statusInputs = document.querySelectorAll('input[name="item-status"]');
            statusInputs.forEach(input => {
                input.checked = input.value === statusValue;
            });
            
            // Show image if exists
            const preview = document.getElementById('image-preview');
            if (item.image) {
                preview.innerHTML = `<img src="${item.image}" alt="${item.name}" class="w-32 h-32 object-cover rounded-lg mx-auto">`;
            }
            
            // Calculate and show profit preview
            this.setupProfitCalculator(); // Re-trigger calculation
            
            document.getElementById('menu-item-modal').classList.remove('hidden');
            
        } catch (error) {
            showError('Failed to load item data');
            console.error('Error loading item:', error);
        }
    }

    closeMenuItemModal() {
        document.getElementById('menu-item-modal').classList.add('hidden');
    }

    async saveMenuItem() {
    const form = document.getElementById('menu-item-form');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const formData = new FormData();
    const itemId = document.getElementById('menu-item-id').value;
    const isEdit = itemId !== '';

    // Add form data
    formData.append('name', document.getElementById('item-name').value);
    formData.append('description', document.getElementById('item-description').value);
    formData.append('category', document.getElementById('item-category').value);
    formData.append('price', document.getElementById('item-price').value);
    formData.append('cost_price', document.getElementById('item-cost').value || 0);
    formData.append('preparation_time', document.getElementById('item-prep-time').value);
    
    const statusValue = document.querySelector('input[name="item-status"]:checked')?.value;
    if (statusValue) {
        formData.append('is_available', statusValue);
    }

    // Add image if selected
    const imageInput = document.getElementById('item-image');
    if (imageInput && imageInput.files[0]) {
        formData.append('image', imageInput.files[0]);
    }

    try {
        const url = isEdit ? `${this.apiBase}items/${itemId}/` : `${this.apiBase}items/`;
        const method = isEdit ? 'PUT' : 'POST';

        // For FormData, create headers manually WITHOUT Content-Type
        const headers = {
            'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
            'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ''
        };

        const response = await fetch(url, {
            method: method,
            headers: headers,
            body: formData
        });

        // Check if response is JSON before parsing
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response (likely CSRF error):', text.substring(0, 200));
            throw new Error('Server returned HTML error page. Check CSRF token.');
        }

        const result = await response.json();
        
        if (response.ok && result.success) {
            this.closeMenuItemModal();
            await this.loadMenuItems();
            showSuccess(`Item ${isEdit ? 'updated' : 'created'} successfully`);
        } else {
            throw new Error(result.error || 'Failed to save item');
        }
    } catch (error) {
        console.error('Error saving item:', error);
        showError(error.message || 'Failed to save item');
    }
}

    async toggleItemStatus(itemId) {
        try {
            // First get current item
            const response = await fetch(`${this.apiBase}items/${itemId}/`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to fetch item');
            
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Failed to load item');
            
            const item = result.item;
            
            // Toggle status
            const newStatus = !item.is_available;
            
            // Update item
            const updateResponse = await fetch(`${this.apiBase}items/${itemId}/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getAuthHeaders()
                },
                body: JSON.stringify({ ...item, is_available: newStatus })
            });
            
            const updateResult = await updateResponse.json();
            
            if (updateResponse.ok && updateResult.success) {
                await this.loadMenuItems();
                showSuccess(`Item ${newStatus ? 'enabled' : 'disabled'} successfully`);
            } else {
                throw new Error(updateResult.error || 'Failed to update item');
            }
        } catch (error) {
            showError(error.message || 'Failed to toggle item status');
            console.error('Error toggling item status:', error);
        }
    }

    async deleteMenuItem(itemId) {
        showConfirm('Are you sure you want to delete this item?', async () => {
            try {
                const response = await fetch(`${this.apiBase}items/${itemId}/`, {
                    method: 'DELETE',
                    headers: this.getAuthHeaders()
                });

                const result = await response.json();
                
                if (response.ok && result.success) {
                    await this.loadMenuItems();
                    showSuccess('Item deleted successfully');
                } else {
                    throw new Error(result.error || 'Failed to delete item');
                }
            } catch (error) {
                showError(error.message || 'Failed to delete item');
                console.error('Error deleting item:', error);
            }
        });
    }

    // ========== DATA LOADING FUNCTIONS ==========

    async loadCategories() {
        try {
            const response = await fetch(`${this.apiBase}categories/`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to load categories');
            
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Failed to load categories');
            
            const categories = result.categories || result.results || [];
            this.renderCategories(categories);
            return categories;
        } catch (error) {
            showError('Failed to load categories');
            console.error('Error loading categories:', error);
            return [];
        }
    }

    async loadMenuItems() {
        try {
            const response = await fetch(`${this.apiBase}items/`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to load menu items');
            
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Failed to load menu items');
            
            const items = result.items || result.results || [];
            this.renderMenuItems(items);
            return items;
        } catch (error) {
            showError('Failed to load menu items');
            console.error('Error loading menu items:', error);
            return [];
        }
    }

    // ========== RENDERING FUNCTIONS ==========

    renderCategories(categories) {
        const container = document.getElementById('categories-container');
        if (!container) return;

        if (!categories || categories.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-8">
                    <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-folder-open text-gray-400 text-2xl"></i>
                    </div>
                    <h3 class="text-lg font-medium text-gray-900 mb-2">No Categories Found</h3>
                    <p class="text-gray-600 mb-4">Create categories to organize your menu items</p>
                    <button onclick="openAddCategoryModal()" class="btn-primary">
                        <i class="fas fa-plus mr-2"></i>Create First Category
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = categories.map(category => `
            <div class="category-card border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h3 class="font-bold text-gray-900">${category.name}</h3>
                        ${category.description ? `<p class="text-sm text-gray-600 mt-1">${category.description}</p>` : ''}
                    </div>
                    <span class="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
                        ${category.items_count || 0} items
                    </span>
                </div>
                
                <div class="flex items-center justify-between mt-4">
                    <div class="text-sm text-gray-500">
                        Order: ${category.order_index}
                        ${!category.is_active ? '<span class="ml-2 px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">Inactive</span>' : ''}
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="editCategory(${category.id})" 
                                class="text-blue-600 hover:text-blue-800 p-1 hover:bg-blue-50 rounded">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button onclick="deleteCategory(${category.id})" 
                                class="text-red-600 hover:text-red-800 p-1 hover:bg-red-50 rounded">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        // Update category filter options
        this.updateCategoryFilter(categories);
    }

    renderMenuItems(items) {
        const tbody = document.getElementById('menu-items-table');
        if (!tbody) return;

        if (!items || items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="px-6 py-8 text-center">
                        <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <i class="fas fa-utensils text-gray-400 text-2xl"></i>
                        </div>
                        <h3 class="text-lg font-medium text-gray-900 mb-2">No Menu Items Found</h3>
                        <p class="text-gray-600 mb-4">Add items to your menu</p>
                        <button onclick="openAddItemModal()" class="btn-primary">
                            <i class="fas fa-plus mr-2"></i>Add First Item
                        </button>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = items.map(item => `
            <tr class="hover:bg-gray-50 transition-colors" 
                data-category="${item.category}" 
                data-status="${item.is_available ? 'available' : 'unavailable'}">
                <td class="px-6 py-4 whitespace-nowrap">
                    <input type="checkbox" class="item-checkbox" value="${item.id}">
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        ${item.image ? `<img class="h-10 w-10 rounded-lg object-cover mr-3" src="${item.image}" alt="${item.name}">` : 
                        `<div class="h-10 w-10 rounded-lg bg-gray-200 flex items-center justify-center mr-3">
                            <i class="fas fa-utensils text-gray-500"></i>
                        </div>`}
                        <div>
                            <div class="text-sm font-medium text-gray-900">${item.name}</div>
                            <div class="text-sm text-gray-500">${item.category_name || 'Uncategorized'}</div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    $${parseFloat(item.price).toFixed(2)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    $${item.cost_price ? parseFloat(item.cost_price).toFixed(2) : '0.00'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${item.preparation_time || 15} min
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${item.is_available ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                        ${item.is_available ? 'Available' : 'Unavailable'}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${item.description ? (item.description.length > 50 ? item.description.substring(0, 50) + '...' : item.description) : '-'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div class="flex items-center justify-end space-x-2">
                        <button onclick="editMenuItem(${item.id})" 
                                class="text-blue-600 hover:text-blue-800 p-1 hover:bg-blue-50 rounded"
                                title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button onclick="toggleItemStatus(${item.id})" 
                                class="text-yellow-600 hover:text-yellow-800 p-1 hover:bg-yellow-50 rounded"
                                title="${item.is_available ? 'Disable' : 'Enable'}">
                            <i class="fas fa-${item.is_available ? 'eye-slash' : 'eye'}"></i>
                        </button>
                        <button onclick="deleteMenuItem(${item.id})" 
                                class="text-red-600 hover:text-red-800 p-1 hover:bg-red-50 rounded"
                                title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // Update item count
        const countElement = document.querySelector('.text-sm.text-gray-600');
        if (countElement) {
            countElement.textContent = `Showing ${items.length} of ${items.length} items`;
        }
    }

    updateCategoryFilter(categories) {
        const filter = document.getElementById('category-filter');
        if (!filter) return;

        const currentValue = filter.value;
        filter.innerHTML = '<option value="all">All Categories</option>' +
            categories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
        filter.value = currentValue;
    }

    // ========== FILTERING & SEARCHING ==========

    filterItems() {
        const rows = document.querySelectorAll('#menu-items-table tr');
        const categoryFilter = this.currentCategoryFilter;
        const statusFilter = this.currentStatusFilter;

        rows.forEach(row => {
            if (row.rowIndex === 0) return; // Skip header
            
            const category = row.dataset.category;
            const status = row.dataset.status;
            
            const categoryMatch = categoryFilter === 'all' || category === categoryFilter;
            const statusMatch = statusFilter === 'all' || status === statusFilter;
            
            row.style.display = categoryMatch && statusMatch ? '' : 'none';
        });

        this.updateVisibleCount();
    }

    searchItems(query) {
        const rows = document.querySelectorAll('#menu-items-table tr');
        const lowerQuery = query.toLowerCase();

        rows.forEach(row => {
            if (row.rowIndex === 0) return; // Skip header
            
            const name = row.querySelector('.text-sm.font-medium')?.textContent.toLowerCase() || '';
            const description = row.querySelector('td:nth-child(7)')?.textContent.toLowerCase() || '';
            
            const matches = name.includes(lowerQuery) || description.includes(lowerQuery);
            row.style.display = matches ? '' : 'none';
        });

        this.updateVisibleCount();
    }

    updateVisibleCount() {
        const visibleRows = document.querySelectorAll('#menu-items-table tr:not([style*="display: none"]):not(:first-child)');
        const totalRows = document.querySelectorAll('#menu-items-table tr:not(:first-child)').length;
        const countElement = document.querySelector('.text-sm.text-gray-600');
        if (countElement) {
            countElement.textContent = `Showing ${visibleRows.length} of ${totalRows} items`;
        }
    }

    // ========== BULK ACTIONS ==========

    applyBulkAction() {
        const action = document.getElementById('bulk-action').value;
        const selectedItems = Array.from(this.selectedItems);

        if (selectedItems.length === 0) {
            showError('No items selected');
            return;
        }

        switch (action) {
            case 'enable':
                this.bulkToggleStatus(selectedItems, true);
                break;
            case 'disable':
                this.bulkToggleStatus(selectedItems, false);
                break;
            case 'delete':
                this.bulkDelete(selectedItems);
                break;
            default:
                showError('Please select an action');
        }
    }

    async bulkToggleStatus(itemIds, status) {
        try {
            const promises = itemIds.map(async (id) => {
                // First get current item
                const getResponse = await fetch(`${this.apiBase}items/${id}/`, {
                    headers: this.getAuthHeaders()
                });
                
                if (!getResponse.ok) return null;
                
                const result = await getResponse.json();
                if (!result.success) return null;
                
                const item = result.item;
                
                // Update status
                const updateResponse = await fetch(`${this.apiBase}items/${id}/`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        ...this.getAuthHeaders()
                    },
                    body: JSON.stringify({ ...item, is_available: status })
                });
                
                return updateResponse;
            });

            await Promise.all(promises);
            await this.loadMenuItems();
            this.clearSelection();
            showSuccess(`Items ${status ? 'enabled' : 'disabled'} successfully`);
        } catch (error) {
            showError('Failed to update items');
            console.error('Error bulk updating:', error);
        }
    }

    async bulkDelete(itemIds) {
        showConfirm(`Are you sure you want to delete ${itemIds.length} items? This action cannot be undone.`, async () => {
            try {
                const promises = itemIds.map(id => 
                    fetch(`${this.apiBase}items/${id}/`, {
                        method: 'DELETE',
                        headers: this.getAuthHeaders()
                    })
                );

                await Promise.all(promises);
                await this.loadMenuItems();
                this.clearSelection();
                showSuccess('Items deleted successfully');
            } catch (error) {
                showError('Failed to delete items');
                console.error('Error bulk deleting:', error);
            }
        });
    }

    updateSelectedItem(itemId, selected) {
        if (selected) {
            this.selectedItems.add(itemId);
        } else {
            this.selectedItems.delete(itemId);
        }
    }

    updateSelectedCount() {
        const count = this.selectedItems.size;
        const element = document.getElementById('selected-count');
        if (element) {
            element.textContent = `${count} selected`;
            element.classList.toggle('hidden', count === 0);
        }
    }

    clearSelection() {
        this.selectedItems.clear();
        const checkboxes = document.querySelectorAll('.item-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        this.updateSelectedCount();
        
        // Also uncheck select all
        const selectAll = document.getElementById('select-all-items');
        if (selectAll) {
            selectAll.checked = false;
        }
    }

    // ========== EXPORT/IMPORT ==========

    async exportMenu() {
        try {
            const response = await fetch(`${this.apiBase}export/`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to export menu');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'menu_export.json';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showSuccess('Menu exported successfully');
        } catch (error) {
            showError('Failed to export menu');
            console.error('Error exporting menu:', error);
        }
    }

    async importMenu() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const loading = showLoading('Importing menu...');
            
            try {
                const text = await file.text();
                const data = JSON.parse(text);
                
                const response = await fetch(`${this.apiBase}import/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...this.getAuthHeaders()
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                
                if (response.ok && result.success) {
                    hideLoading();
                    showSuccess(result.message);
                    await this.loadCategories();
                    await this.loadMenuItems();
                } else {
                    throw new Error(result.error || 'Failed to import menu');
                }
            } catch (error) {
                hideLoading();
                showError(error.message || 'Failed to import menu');
                console.error('Error importing menu:', error);
            }
        };
        input.click();
    }

    // ========== UTILITY FUNCTIONS ==========

    async populateCategorySelect() {
        try {
            const response = await fetch(`${this.apiBase}categories/`, {
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) throw new Error('Failed to load categories');
            
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Failed to load categories');
            
            const categories = result.categories || result.results || [];
            const select = document.getElementById('item-category');
            if (!select) return;

            select.innerHTML = '<option value="">Select Category</option>' +
                categories
                    .filter(cat => cat.is_active)
                    .map(cat => `<option value="${cat.id}">${cat.name}</option>`)
                    .join('');
        } catch (error) {
            console.error('Error populating category select:', error);
        }
    }

    getCsrfToken() {
    // PRIMARY: Get from cookie (this is the correct one)
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match && match[1]) {
        console.log('Using CSRF token from cookie, length:', match[1].length);
        return match[1];  // Returns: "S0ryPaunaW7G4iCMa7awH2qxRmH2aK6z"
    }
    
    // FALLBACK: Try HTML input
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (csrfInput && csrfInput.value && csrfInput.value.length > 10) {
        console.log('Using CSRF token from input, length:', csrfInput.value.length);
        return csrfInput.value;
    }
    
    console.error('No valid CSRF token found!');
    return '';
}

    

    getAuthHeaders(contentType = 'application/json') {
        const headers = {};
        
        // Always include JWT token if available
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }
        
        // Include CSRF token for session auth (as fallback)
        const csrfToken = this.getCsrfToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        // Add Content-Type
        if (contentType) {
            headers['Content-Type'] = contentType;
        }
        
        console.log('Auth headers:', headers);
        return headers;
    }
}

// ========== GLOBAL FUNCTIONS FOR HTML ONCLICK ==========

function openAddCategoryModal() {
    window.menuManager.openAddCategoryModal();
}

function openAddItemModal() {
    window.menuManager.openAddItemModal();
}

function editCategory(categoryId) {
    window.menuManager.openEditCategoryModal(categoryId);
}

function deleteCategory(categoryId) {
    window.menuManager.deleteCategory(categoryId);
}

function editMenuItem(itemId) {
    window.menuManager.editMenuItem(itemId);
}

function toggleItemStatus(itemId) {
    window.menuManager.toggleItemStatus(itemId);
}

function deleteMenuItem(itemId) {
    window.menuManager.deleteMenuItem(itemId);
}

function saveCategory() {
    window.menuManager.saveCategory();
}

function closeCategoryModal() {
    window.menuManager.closeCategoryModal();
}

function saveMenuItem() {
    window.menuManager.saveMenuItem();
}

function closeMenuItemModal() {
    window.menuManager.closeMenuItemModal();
}

function exportMenu() {
    window.menuManager.exportMenu();
}

function importMenu() {
    window.menuManager.importMenu();
}

function applyBulkAction() {
    window.menuManager.applyBulkAction();
}

function clearSelection() {
    window.menuManager.clearSelection();
}

// ========== INITIALIZATION ==========

document.addEventListener('DOMContentLoaded', function() {
    window.menuManager = new MenuManager();
});