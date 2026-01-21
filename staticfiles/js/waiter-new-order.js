// static/js/waiter-new-order.js
class WaiterNewOrder {
    constructor() {
        this.apiBase = '/api/tables';
        this.menuApi = '/api/menu';
        this.selectedTableId = null;
        this.selectedTableNumber = null;
        this.cart = [];
        this.menuItems = [];
        this.categories = [];
        this.currentCategory = 'all';
        this.isLoading = false;
        this.init();
    }

    async init() {
        await this.checkAuth();
        await Promise.all([
            this.loadTables(),
            this.loadMenu()
        ]);
        this.setupEventListeners();
        this.restoreCart();
    }

    async checkAuth() {
        const token = localStorage.getItem('access_token');
        const role = localStorage.getItem('user_role');
        
        if (!token) {
            window.location.href = '/login/';
            return false;
        }
        
        if (!['waiter', 'manager', 'admin'].includes(role)) {
            window.location.href = '/login/';
            return false;
        }
        
        return true;
    }

    getAuthHeaders() {
        const token = localStorage.getItem('access_token');
        const csrfToken = this.getCookie('csrftoken');
        
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'X-CSRFToken': csrfToken,
            'Accept': 'application/json'
        };
    }

    getCookie(name) {
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

    async loadTables() {
        try {
            this.showLoading('tables-container', 'Loading tables...');
            const response = await fetch(`${this.apiBase}/tables/?is_active=true&status=available`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                this.renderTables(data.results || data);
                return data;
            } else if (response.status === 403) {
                this.showError('You don\'t have permission to view tables');
                return [];
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('Error loading tables:', error);
            this.showError('Failed to load tables', 'tables-container');
            return [];
        }
    }

    renderTables(tables) {
        const container = document.getElementById('tables-container');
        if (!container) return;

        if (!tables || tables.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center p-8 text-gray-500">
                    <i class="fas fa-table text-3xl mb-3"></i>
                    <p>No tables available</p>
                    <p class="text-sm">Contact manager to add tables</p>
                </div>
            `;
            return;
        }

        container.innerHTML = tables.map(table => `
            <button onclick="window.waiterNewOrder.selectTable(${table.id}, ${table.table_number})" 
                    class="table-btn border-2 rounded-xl p-3 md:p-4 text-center transition-all duration-200 active:scale-95 touch-manipulation
                           ${this.selectedTableId === table.id ? 
                             'border-red-500 bg-red-50 shadow-sm' : 
                             'border-gray-300 hover:border-red-300 hover:bg-red-50/50'}">
                <div class="text-xl md:text-2xl font-bold mb-1">${table.table_number}</div>
                <div class="text-xs md:text-sm text-gray-600 mb-1">${table.capacity || 4} seats</div>
                <div class="text-xs text-green-600">
                    <i class="fas fa-check-circle mr-1"></i>Available
                </div>
            </button>
        `).join('');
    }

    async loadMenu() {
        try {
            this.showLoading('menu-items-container', 'Loading menu...');
            const response = await fetch(`${this.menuApi}/restaurant-menu/`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                // Handle different API response formats
                if (data.categories && data.restaurant) {
                    // New format with categories array
                    this.categories = data.categories;
                    this.menuItems = [];
                    data.categories.forEach(category => {
                        if (category.items && Array.isArray(category.items)) {
                            category.items.forEach(item => {
                                item.category_id = category.id;
                                this.menuItems.push(item);
                            });
                        }
                    });
                } else if (Array.isArray(data)) {
                    // Old format - array of items
                    this.menuItems = data;
                    this.extractCategoriesFromItems();
                }
                
                this.renderCategories();
                this.renderMenuItems();
                return data;
            }
        } catch (error) {
            console.error('Error loading menu:', error);
            this.showError('Failed to load menu', 'menu-items-container');
            this.loadSampleMenu();
        }
    }

    extractCategoriesFromItems() {
        const categoryMap = new Map();
        this.menuItems.forEach(item => {
            if (item.category_id && item.category_name) {
                if (!categoryMap.has(item.category_id)) {
                    categoryMap.set(item.category_id, {
                        id: item.category_id,
                        name: item.category_name
                    });
                }
            }
        });
        this.categories = Array.from(categoryMap.values());
    }

    renderCategories() {
        const container = document.getElementById('categories-container');
        if (!container) return;

        container.innerHTML = `
            <button onclick="window.waiterNewOrder.filterMenuByCategory('all')" 
                    class="category-btn px-3 md:px-4 py-2 rounded-full whitespace-nowrap transition-all duration-200 active:scale-95 touch-manipulation
                           ${this.currentCategory === 'all' ? 
                             'bg-red-600 text-white shadow-sm' : 
                             'bg-gray-100 text-gray-700 hover:bg-gray-200'}">
                All Items
            </button>
            ${this.categories.map(cat => `
                <button onclick="window.waiterNewOrder.filterMenuByCategory(${cat.id})" 
                        class="category-btn px-3 md:px-4 py-2 rounded-full whitespace-nowrap transition-all duration-200 active:scale-95 touch-manipulation
                               ${this.currentCategory === cat.id ? 
                                 'bg-red-600 text-white shadow-sm' : 
                                 'bg-gray-100 text-gray-700 hover:bg-gray-200'}">
                    ${cat.name}
                </button>
            `).join('')}
        `;

        // Make categories scrollable on mobile
        container.classList.add('overflow-x-auto', 'scrollbar-hide', 'pb-2');
    }

    renderMenuItems(filteredItems = null) {
        const itemsToShow = filteredItems || this.menuItems;
        const container = document.getElementById('menu-items-container');
        if (!container) return;

        if (!itemsToShow || itemsToShow.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center p-8 md:p-12 text-gray-500">
                    <i class="fas fa-utensils text-3xl md:text-4xl mb-3"></i>
                    <p class="text-base md:text-lg">No menu items found</p>
                    <p class="text-sm md:text-base">Try a different category or search term</p>
                </div>
            `;
            return;
        }

        container.innerHTML = itemsToShow.map(item => `
            <div class="menu-item bg-white border rounded-xl p-3 md:p-4 hover:shadow-md transition-all duration-200 
                        active:shadow-sm active:scale-[0.995] touch-manipulation">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-gray-900 text-sm md:text-base truncate pr-2">${item.name}</h3>
                    <span class="font-bold text-red-600 text-sm md:text-base whitespace-nowrap">
                        ${item.price ? 'ETB ' + parseFloat(item.price).toFixed(2) : 'ETB 0.00'}
                    </span>
                </div>
                <p class="text-xs md:text-sm text-gray-600 mb-3 line-clamp-2">${item.description || 'No description'}</p>
                <div class="flex justify-between items-center">
                    <span class="text-xs text-gray-500">
                        <i class="fas fa-clock mr-1"></i> ${item.preparation_time || 15} min
                    </span>
                    <button onclick="window.waiterNewOrder.addToCart(${item.id}, '${item.name.replace(/'/g, "\\'")}', ${item.price || 0})" 
                            class="bg-red-50 text-red-600 px-3 py-1 rounded-lg text-xs md:text-sm hover:bg-red-100 transition-all duration-200 
                                   active:scale-95 touch-manipulation ${!item.is_available ? 'opacity-50 cursor-not-allowed' : ''}"
                            ${!item.is_available ? 'disabled' : ''}>
                        <i class="fas fa-plus mr-1"></i>Add
                    </button>
                </div>
            </div>
        `).join('');
    }

    loadSampleMenu() {
        // Sample data for development
        this.categories = [
            { id: 1, name: 'Appetizers' },
            { id: 2, name: 'Main Course' },
            { id: 3, name: 'Desserts' },
            { id: 4, name: 'Drinks' },
        ];

        this.menuItems = [
            {
                id: 1,
                name: 'Margherita Pizza',
                description: 'Classic pizza with tomato sauce and mozzarella',
                price: 12.99,
                category_id: 2,
                preparation_time: 20,
                is_available: true,
            },
            {
                id: 2,
                name: 'Caesar Salad',
                description: 'Fresh romaine lettuce with Caesar dressing',
                price: 8.99,
                category_id: 1,
                preparation_time: 10,
                is_available: true,
            },
            {
                id: 3,
                name: 'Chocolate Cake',
                description: 'Rich chocolate cake with ganache',
                price: 6.99,
                category_id: 3,
                preparation_time: 5,
                is_available: true,
            },
            {
                id: 4,
                name: 'Iced Tea',
                description: 'Refreshing iced tea with lemon',
                price: 2.99,
                category_id: 4,
                preparation_time: 2,
                is_available: true,
            },
        ];

        this.renderCategories();
        this.renderMenuItems();
    }

    selectTable(tableId, tableNumber) {
        this.selectedTableId = tableId;
        this.selectedTableNumber = tableNumber;

        // Update UI - remove highlights from all buttons
        document.querySelectorAll('.table-btn').forEach(btn => {
            btn.classList.remove('border-red-500', 'bg-red-50', 'shadow-sm');
            btn.classList.add('border-gray-300');
        });
        
        // Add highlight to selected button
        const selectedBtn = event.target.closest('.table-btn');
        if (selectedBtn) {
            selectedBtn.classList.add('border-red-500', 'bg-red-50', 'shadow-sm');
            selectedBtn.classList.remove('border-gray-300');
        }

        // Update table selection display
        const tableSelectionEl = document.getElementById('table-selection');
        if (tableSelectionEl) {
            tableSelectionEl.innerHTML = `
                <div class="flex items-center text-sm md:text-base">
                    <i class="fas fa-table mr-2 text-red-600"></i>
                    <span class="font-medium">Table ${tableNumber}</span>
                </div>
            `;
        }

        // Enable/disable submit button
        this.updateSubmitButton();
        this.saveCart();
    }

    addToCart(itemId, itemName, itemPrice, quantity = 1) {
        // Check if item already in cart
        const existingIndex = this.cart.findIndex(item => item.id === itemId);

        if (existingIndex > -1) {
            this.cart[existingIndex].quantity += quantity;
        } else {
            this.cart.push({
                id: itemId,
                name: itemName,
                price: parseFloat(itemPrice),
                quantity: quantity,
                specialInstructions: '',
            });
        }

        this.updateCart();
        this.showToast(`${itemName} added to cart!`, 'success');
        this.saveCart();
        
        // Provide haptic feedback on mobile
        if ('vibrate' in navigator) {
            navigator.vibrate(50);
        }
    }

    updateCart() {
        // Calculate totals
        const subtotal = this.cart.reduce(
            (sum, item) => sum + (item.price * item.quantity), 0
        );
        const tax = subtotal * 0.15;
        const total = subtotal + tax;

        // Update counts
        const totalItems = this.cart.reduce((sum, item) => sum + item.quantity, 0);
        
        const cartCountEl = document.getElementById('cart-count');
        if (cartCountEl) {
            cartCountEl.textContent = totalItems;
            // Add animation for cart count change
            cartCountEl.classList.add('scale-125');
            setTimeout(() => cartCountEl.classList.remove('scale-125'), 300);
        }
        
        const cartSubtotalEl = document.getElementById('cart-subtotal');
        if (cartSubtotalEl) cartSubtotalEl.textContent = `ETB ${subtotal.toFixed(2)}`;
        
        const cartTaxEl = document.getElementById('cart-tax');
        if (cartTaxEl) cartTaxEl.textContent = `ETB ${tax.toFixed(2)}`;
        
        const cartTotalEl = document.getElementById('cart-total');
        if (cartTotalEl) cartTotalEl.textContent = `ETB ${total.toFixed(2)}`;

        // Render cart items
        this.renderCartItems();

        // Enable/disable submit button
        this.updateSubmitButton();
    }

    renderCartItems() {
        const container = document.getElementById('cart-items-container');
        if (!container) return;

        if (this.cart.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-shopping-cart text-3xl md:text-4xl mb-3"></i>
                    <p class="text-base md:text-lg">Cart is empty</p>
                    <p class="text-sm md:text-base">Add items from the menu</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.cart.map((item, index) => `
            <div class="cart-item border-b pb-3 mb-3 last:border-0 last:mb-0 last:pb-0 animate-slideIn">
                <div class="flex justify-between items-start mb-2">
                    <div class="flex-1 min-w-0 mr-2">
                        <div class="font-bold text-sm md:text-base truncate">${item.name}</div>
                        <div class="text-xs md:text-sm text-red-600">ETB ${item.price.toFixed(2)} each</div>
                    </div>
                    <button onclick="window.waiterNewOrder.removeFromCart(${index})" 
                            class="flex-shrink-0 text-gray-400 hover:text-red-600 transition-colors duration-200
                                   active:scale-95 touch-manipulation">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center">
                        <button onclick="window.waiterNewOrder.updateQuantity(${index}, -1)" 
                                class="quantity-btn w-8 h-8 md:w-10 md:h-10 bg-gray-100 rounded-lg hover:bg-gray-200 
                                       transition-all duration-200 active:scale-95 touch-manipulation flex items-center justify-center">
                            <i class="fas fa-minus text-xs"></i>
                        </button>
                        <span class="mx-3 font-bold text-base md:text-lg min-w-[2rem] text-center">${item.quantity}</span>
                        <button onclick="window.waiterNewOrder.updateQuantity(${index}, 1)" 
                                class="quantity-btn w-8 h-8 md:w-10 md:h-10 bg-gray-100 rounded-lg hover:bg-gray-200 
                                       transition-all duration-200 active:scale-95 touch-manipulation flex items-center justify-center">
                            <i class="fas fa-plus text-xs"></i>
                        </button>
                    </div>
                    <span class="font-bold text-sm md:text-base">ETB ${(item.price * item.quantity).toFixed(2)}</span>
                </div>
                
                <div class="mt-2">
                    <input type="text" 
                           class="w-full p-2 border rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent
                                  placeholder:text-gray-400" 
                           placeholder="Add special instructions..."
                           value="${item.specialInstructions}"
                           onchange="window.waiterNewOrder.updateInstructions(${index}, this.value)"
                           onblur="window.waiterNewOrder.saveCart()">
                </div>
            </div>
        `).join('');
    }

    removeFromCart(index) {
        this.cart.splice(index, 1);
        this.updateCart();
        this.saveCart();
        this.showToast('Item removed from cart', 'warning');
    }

    updateQuantity(index, delta) {
        this.cart[index].quantity += delta;
        if (this.cart[index].quantity <= 0) {
            this.removeFromCart(index);
        } else {
            this.updateCart();
            this.saveCart();
        }
    }

    updateInstructions(index, instructions) {
        this.cart[index].specialInstructions = instructions;
        this.saveCart();
    }

    clearCart() {
        if (this.cart.length === 0) {
            this.showToast('Cart is already empty', 'info');
            return;
        }
        
        if (confirm('Clear all items from cart? This action cannot be undone.')) {
            this.cart = [];
            this.updateCart();
            localStorage.removeItem('waiter_cart');
            this.showToast('Cart cleared', 'warning');
        }
    }

    updateSubmitButton() {
        const submitBtn = document.getElementById('submit-order-btn');
        if (submitBtn) {
            const isDisabled = !this.selectedTableId || this.cart.length === 0;
            submitBtn.disabled = isDisabled;
            submitBtn.classList.toggle('opacity-50', isDisabled);
            submitBtn.classList.toggle('cursor-not-allowed', isDisabled);
        }
    }

    // Update the submitOrder method in waiter-new-order.js

// Update submitOrder method in waiter-new-order.js

async submitOrder() {
    if (!this.selectedTableId || this.cart.length === 0) {
        this.showToast('Please select a table and add items to cart', 'error');
        return;
    }

    const customerNameEl = document.getElementById('customer-name');
    const customerName = customerNameEl?.value.trim() || '';
    const specialInstructionsEl = document.getElementById('special-instructions');
    const specialInstructions = specialInstructionsEl?.value.trim() || '';

    // Prepare items for API
    const items = this.cart.map(item => ({
        menu_item: item.id, // Must match serializer field name
        quantity: item.quantity,
        special_instructions: item.specialInstructions || ''
    }));

    // Prepare order data
    const orderData = {
        table: this.selectedTableId,
        order_type: 'waiter', // Fixed as waiter for this interface
        customer_name: customerName || 'Guest',
        notes: specialInstructions,
        is_priority: false,
        items: items
    };

    console.log('Submitting order:', orderData);

    try {
        this.showLoading('submit-order-btn', 'Creating order...');
        
        // Use unified endpoint
        const response = await fetch(`${this.apiBase}/orders/create-with-items/`, {
            method: 'POST',
            headers: this.getAuthHeaders(),
            body: JSON.stringify(orderData)
        });

        const responseText = await response.text();
        console.log('API Response:', response.status, responseText);
        
        if (response.ok) {
            const result = JSON.parse(responseText);
            
            if (result.success) {
                this.showToast(`Order #${result.order.order_number} created successfully!`, 'success');
                
                // Reset form
                this.resetOrderForm();
                
                // Redirect to orders page
                setTimeout(() => {
                    window.location.href = '/waiter/orders/';
                }, 1500);
            } else {
                // Handle validation errors
                let errorMsg = result.message || 'Order creation failed';
                if (result.errors) {
                    errorMsg += ': ' + JSON.stringify(result.errors);
                }
                throw new Error(errorMsg);
            }
        } else {
            let errorMessage = `HTTP ${response.status}`;
            try {
                const errorData = JSON.parse(responseText);
                if (errorData.errors) {
                    // Format Django serializer errors
                    errorMessage = Object.entries(errorData.errors)
                        .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
                        .join('; ');
                } else {
                    errorMessage = errorData.error || errorData.detail || JSON.stringify(errorData);
                }
            } catch (e) {
                errorMessage = responseText;
            }
            throw new Error(errorMessage);
        }
        
    } catch (error) {
        console.error('Error creating order:', error);
        this.showToast(`Failed to create order: ${error.message}`, 'error');
    } finally {
        this.hideLoading('submit-order-btn', 'Submit to Kitchen');
    }
}

    resetOrderForm() {
        this.cart = [];
        this.selectedTableId = null;
        this.selectedTableNumber = null;
        
        const customerNameEl = document.getElementById('customer-name');
        if (customerNameEl) customerNameEl.value = '';
        
        const specialInstructionsEl = document.getElementById('special-instructions');
        if (specialInstructionsEl) specialInstructionsEl.value = '';
        
        this.updateCart();
        this.loadTables();
        localStorage.removeItem('waiter_cart');
        
        // Reset table selection display
        const tableSelectionEl = document.getElementById('table-selection');
        if (tableSelectionEl) {
            tableSelectionEl.innerHTML = 'No table selected';
        }
    }

    filterMenuByCategory(categoryId) {
        this.currentCategory = categoryId;
        
        // Update active category buttons
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.classList.remove('bg-red-600', 'text-white', 'shadow-sm');
            btn.classList.add('bg-gray-100', 'text-gray-700');
        });
        
        // Find and activate the selected button
        const categoryButtons = document.querySelectorAll('.category-btn');
        if (categoryId === 'all') {
            categoryButtons[0]?.classList.add('bg-red-600', 'text-white', 'shadow-sm');
            categoryButtons[0]?.classList.remove('bg-gray-100', 'text-gray-700');
        } else {
            const selectedBtn = Array.from(categoryButtons).find(btn => 
                btn.textContent === this.categories.find(c => c.id === categoryId)?.name
            );
            if (selectedBtn) {
                selectedBtn.classList.add('bg-red-600', 'text-white', 'shadow-sm');
                selectedBtn.classList.remove('bg-gray-100', 'text-gray-700');
            }
        }

        // Filter items
        let filteredItems;
        if (categoryId === 'all') {
            filteredItems = this.menuItems;
        } else {
            filteredItems = this.menuItems.filter(
                item => item.category_id === categoryId
            );
        }

        this.renderMenuItems(filteredItems);
        
        // Scroll to top of menu on mobile
        if (window.innerWidth < 768) {
            document.getElementById('menu-items-container')?.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
            });
        }
    }

    setupEventListeners() {
        // Submit order button
        const submitBtn = document.getElementById('submit-order-btn');
        if (submitBtn) {
            submitBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.submitOrder();
            });
        }

        // Search functionality with debounce
        const searchInput = document.getElementById('menu-search');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    const searchTerm = e.target.value.toLowerCase().trim();
                    if (searchTerm === '') {
                        this.filterMenuByCategory(this.currentCategory);
                        return;
                    }
                    
                    const filteredItems = this.menuItems.filter(
                        item => item.name.toLowerCase().includes(searchTerm) ||
                               (item.description || '').toLowerCase().includes(searchTerm)
                    );
                    this.renderMenuItems(filteredItems);
                }, 300);
            });
        }

        // Clear cart button
        const clearCartBtn = document.querySelector('[onclick*="clearCart"]');
        if (clearCartBtn) {
            clearCartBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.clearCart();
            });
        }

        // Cart preview button
        const cartPreviewBtn = document.getElementById('cart-preview');
        if (cartPreviewBtn) {
            cartPreviewBtn.addEventListener('click', () => {
                if (this.cart.length > 0) {
                    const cartSection = document.querySelector('.lg\\:col-span-1');
                    if (cartSection) {
                        cartSection.scrollIntoView({ 
                            behavior: 'smooth', 
                            block: 'start' 
                        });
                    }
                }
            });
        }

        // Save cart on page unload
        window.addEventListener('beforeunload', () => {
            this.saveCart();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter to submit order
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.submitOrder();
            }
            
            // Escape to clear search
            if (e.key === 'Escape') {
                const searchInput = document.getElementById('menu-search');
                if (searchInput && document.activeElement === searchInput) {
                    searchInput.value = '';
                    this.filterMenuByCategory(this.currentCategory);
                }
            }
        });

        // Touch event optimizations for mobile
        if ('ontouchstart' in window) {
            // Add touch-specific optimizations
            document.querySelectorAll('button, input, .menu-item').forEach(el => {
                el.classList.add('touch-manipulation');
            });
        }
    }

    saveCart() {
        if (this.cart.length > 0 || this.selectedTableId) {
            const cartData = {
                cart: this.cart,
                tableId: this.selectedTableId,
                tableNumber: this.selectedTableNumber,
                timestamp: new Date().getTime()
            };
            try {
                localStorage.setItem('waiter_cart', JSON.stringify(cartData));
            } catch (e) {
                console.warn('LocalStorage is full, clearing old data...');
                localStorage.clear();
                localStorage.setItem('waiter_cart', JSON.stringify(cartData));
            }
        }
    }

    restoreCart() {
        try {
            const saved = localStorage.getItem('waiter_cart');
            if (saved) {
                const cartData = JSON.parse(saved);
                // Check if cart is less than 2 hours old
                const twoHoursAgo = Date.now() - (2 * 60 * 60 * 1000);
                if (cartData.timestamp && cartData.timestamp > twoHoursAgo) {
                    this.cart = cartData.cart || [];
                    if (cartData.tableId) {
                        this.selectedTableId = cartData.tableId;
                        this.selectedTableNumber = cartData.tableNumber;
                        this.updateCart();
                    }
                } else {
                    localStorage.removeItem('waiter_cart');
                }
            }
        } catch (error) {
            console.error('Error restoring cart:', error);
            localStorage.removeItem('waiter_cart');
        }
    }

    showToast(message, type = 'info') {
        // Use auth-manager if available
        if (window.authManager && window.authManager.showToast) {
            window.authManager.showToast(message, type);
            return;
        }

        // Fallback toast implementation
        const toast = document.createElement('div');
        const typeClass = {
            'success': 'bg-green-500',
            'error': 'bg-red-500',
            'warning': 'bg-yellow-500',
            'info': 'bg-blue-500'
        }[type] || 'bg-gray-800';
        
        toast.className = `fixed top-4 right-4 ${typeClass} text-white px-4 py-3 rounded-lg shadow-lg z-50 animate-slideInRight max-w-md`;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('animate-slideOutRight');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    showError(message, containerId = null) {
        if (containerId) {
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = `
                    <div class="col-span-full text-center p-8 text-red-600">
                        <i class="fas fa-exclamation-triangle text-3xl mb-3"></i>
                        <p>${message}</p>
                        <button onclick="window.location.reload()" 
                                class="mt-2 text-sm text-red-600 hover:text-red-800 underline">
                            Retry
                        </button>
                    </div>
                `;
            }
        }
        this.showToast(message, 'error');
    }

    showLoading(containerId, message = 'Loading...') {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="col-span-full text-center p-8 text-gray-500">
                    <div class="spinner w-12 h-12 border-4 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p>${message}</p>
                </div>
            `;
        }
    }

    hideLoading(containerId, restoreText) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = restoreText;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.waiterNewOrder = new WaiterNewOrder();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateY(10px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    .animate-slideIn {
        animation: slideIn 0.3s ease;
    }
    .animate-slideInRight {
        animation: slideInRight 0.3s ease;
    }
    .animate-slideOutRight {
        animation: slideOutRight 0.3s ease;
    }
    .touch-manipulation {
        touch-action: manipulation;
    }
    .scrollbar-hide {
        -ms-overflow-style: none;
        scrollbar-width: none;
    }
    .scrollbar-hide::-webkit-scrollbar {
        display: none;
    }
    .line-clamp-2 {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    @media (max-width: 768px) {
        .menu-item {
            min-height: 120px;
        }
        .table-btn {
            min-width: 80px;
        }
    }
`;
document.head.appendChild(style);