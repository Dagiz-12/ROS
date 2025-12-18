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
        this.init();
    }

    init() {
        this.checkAuth();
        this.loadTables();
        this.loadMenu();
        this.setupEventListeners();
        this.restoreCart();
    }

    checkAuth() {
        const token = localStorage.getItem('access_token');
        const role = localStorage.getItem('user_role');
        
        if (!token) {
            window.location.href = '/login/';
            return;
        }
        
        if (!['waiter', 'manager', 'admin'].includes(role)) {
            window.location.href = '/login/';
        }
    }

    getAuthHeaders() {
        return window.authManager.getAuthHeaders();
    }

    async loadTables() {
        try {
            const response = await fetch(`${this.apiBase}/tables/?is_active=true&status=available`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                this.renderTables(data.results || data);
            }
        } catch (error) {
            console.error('Error loading tables:', error);
            this.showError('Failed to load tables');
        }
    }

    renderTables(tables) {
        const container = document.getElementById('tables-container');
        if (!container) return;

        if (!tables || tables.length === 0) {
            container.innerHTML = '<div class="text-red-600 p-4">No available tables</div>';
            return;
        }

        container.innerHTML = tables.map(table => `
            <button onclick="waiterNewOrder.selectTable(${table.id}, ${table.table_number})" 
                    class="table-btn border-2 rounded-xl p-4 text-center hover:border-red-500 hover:bg-red-50 transition w-full ${this.selectedTableId === table.id ? 'border-red-500 bg-red-50' : 'border-gray-300'}">
                <div class="text-2xl font-bold">${table.table_number}</div>
                <div class="text-sm text-gray-600">${table.capacity || 4} seats</div>
                <div class="text-xs text-green-600 mt-1">Available</div>
            </button>
        `).join('');
    }

    async loadMenu() {
        try {
            const response = await fetch(`${this.menuApi}/restaurant-menu/`, {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                this.menuItems = data.items || data || [];
                this.categories = data.categories || [];
                this.renderCategories();
                this.renderMenuItems();
            }
        } catch (error) {
            console.error('Error loading menu:', error);
            this.loadSampleMenu();
        }
    }

    renderCategories() {
        const container = document.getElementById('categories-container');
        if (!container) return;

        container.innerHTML = `
            <button onclick="waiterNewOrder.filterMenuByCategory('all')" 
                    class="category-btn px-4 py-2 rounded-full whitespace-nowrap transition ${this.currentCategory === 'all' ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}">
                All Items
            </button>
            ${this.categories.map(cat => `
                <button onclick="waiterNewOrder.filterMenuByCategory(${cat.id})" 
                        class="category-btn px-4 py-2 rounded-full whitespace-nowrap transition ${this.currentCategory === cat.id ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}">
                    ${cat.name}
                </button>
            `).join('')}
        `;
    }

    renderMenuItems(filteredItems = null) {
        const itemsToShow = filteredItems || this.menuItems;
        const container = document.getElementById('menu-items-container');
        if (!container) return;

        if (!itemsToShow || itemsToShow.length === 0) {
            container.innerHTML = `
                <div class="col-span-2 text-center py-12 text-gray-500">
                    <i class="fas fa-utensils text-3xl mb-3"></i>
                    <p>No menu items found</p>
                </div>
            `;
            return;
        }

        container.innerHTML = itemsToShow.map(item => `
            <div class="menu-item bg-white border rounded-xl p-4 hover:shadow-md transition">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-gray-900">${item.name}</h3>
                    <span class="font-bold text-red-600">$${item.price ? item.price.toFixed(2) : '0.00'}</span>
                </div>
                <p class="text-sm text-gray-600 mb-3">${item.description || ''}</p>
                <div class="flex justify-between items-center">
                    <span class="text-xs text-gray-500">
                        <i class="fas fa-clock mr-1"></i> ${item.preparation_time || 15} min
                    </span>
                    <button onclick="waiterNewOrder.addToCart(${item.id}, '${item.name.replace(/'/g, "\\'")}', ${item.price})" 
                            class="bg-red-50 text-red-600 px-3 py-1 rounded text-sm hover:bg-red-100 transition ${!item.is_available ? 'opacity-50 cursor-not-allowed' : ''}"
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

        // Update UI
        document.querySelectorAll('.table-btn').forEach(btn => {
            btn.classList.remove('border-red-500', 'bg-red-50');
        });
        event.target.classList.add('border-red-500', 'bg-red-50');

        // Update table selection display
        document.getElementById('table-selection').innerHTML = `
            <i class="fas fa-table mr-1"></i> Table ${tableNumber}
        `;

        // Enable/disable submit button
        this.updateSubmitButton();
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
                price: itemPrice,
                quantity: quantity,
                specialInstructions: '',
            });
        }

        this.updateCart();
        this.showToast(`${itemName} added to cart!`);
        this.saveCart();
    }

    updateCart() {
        // Calculate totals
        const subtotal = this.cart.reduce(
            (sum, item) => sum + item.price * item.quantity, 0
        );
        const tax = subtotal * 0.15;
        const total = subtotal + tax;

        // Update counts
        const totalItems = this.cart.reduce((sum, item) => sum + item.quantity, 0);
        document.getElementById('cart-count').textContent = totalItems;
        document.getElementById('cart-subtotal').textContent = `$${subtotal.toFixed(2)}`;
        document.getElementById('cart-tax').textContent = `$${tax.toFixed(2)}`;
        document.getElementById('cart-total').textContent = `$${total.toFixed(2)}`;

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
                    <i class="fas fa-shopping-cart text-3xl mb-3"></i>
                    <p>Cart is empty</p>
                    <p class="text-sm">Add items from the menu</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.cart.map((item, index) => `
            <div class="border-b pb-3 mb-3 last:border-0 last:mb-0">
                <div class="flex justify-between items-start mb-1">
                    <div>
                        <div class="font-bold">${item.name}</div>
                        <div class="text-sm text-red-600">$${item.price.toFixed(2)} each</div>
                    </div>
                    <button onclick="waiterNewOrder.removeFromCart(${index})" 
                            class="text-gray-400 hover:text-red-600 transition">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="flex items-center justify-between">
                    <div class="flex items-center">
                        <button onclick="waiterNewOrder.updateQuantity(${index}, -1)" 
                                class="w-6 h-6 bg-gray-100 rounded-full hover:bg-gray-200 transition">-</button>
                        <span class="mx-3 font-bold">${item.quantity}</span>
                        <button onclick="waiterNewOrder.updateQuantity(${index}, 1)" 
                                class="w-6 h-6 bg-gray-100 rounded-full hover:bg-gray-200 transition">+</button>
                    </div>
                    <span class="font-bold">$${(item.price * item.quantity).toFixed(2)}</span>
                </div>
                
                <div class="mt-2">
                    <input type="text" 
                           class="w-full p-1 border rounded text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent" 
                           placeholder="Add instructions"
                           value="${item.specialInstructions}"
                           onchange="waiterNewOrder.updateInstructions(${index}, this.value)">
                </div>
            </div>
        `).join('');
    }

    removeFromCart(index) {
        this.cart.splice(index, 1);
        this.updateCart();
        this.saveCart();
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
        if (this.cart.length === 0) return;
        if (confirm('Clear all items from cart?')) {
            this.cart = [];
            this.updateCart();
            localStorage.removeItem('waiter_cart');
        }
    }

    updateSubmitButton() {
        const submitBtn = document.getElementById('submit-order-btn');
        if (submitBtn) {
            submitBtn.disabled = !this.selectedTableId || this.cart.length === 0;
        }
    }

    async submitOrder() {
        if (!this.selectedTableId || this.cart.length === 0) return;

        const customerName = document.getElementById('customer-name')?.value.trim() || '';
        const specialInstructions = document.getElementById('special-instructions')?.value.trim() || '';

        // Prepare order data
        const orderData = {
            table_id: this.selectedTableId,
            order_type: 'waiter',
            customer_name: customerName || 'Guest',
            items: this.cart.map(item => ({
                menu_item_id: item.id,
                quantity: item.quantity,
                special_instructions: item.specialInstructions,
            })),
            special_instructions: specialInstructions,
        };

        try {
            const response = await fetch(`${this.apiBase}/orders/`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify(orderData)
            });

            if (response.ok) {
                const result = await response.json();
                window.authManager.showToast(`Order #${result.order_number} created successfully!`, 'success');

                // Reset form
                this.cart = [];
                this.selectedTableId = null;
                this.selectedTableNumber = null;
                if (document.getElementById('customer-name')) {
                    document.getElementById('customer-name').value = '';
                }
                if (document.getElementById('special-instructions')) {
                    document.getElementById('special-instructions').value = '';
                }
                this.updateCart();
                this.loadTables();
                localStorage.removeItem('waiter_cart');

                // Redirect to orders page after delay
                setTimeout(() => {
                    window.location.href = '/waiter/orders/';
                }, 2000);
            } else {
                const error = await response.json();
                window.authManager.showToast(`Error: ${error.error || 'Failed to create order'}`, 'error');
            }
        } catch (error) {
            console.error('Error submitting order:', error);
            window.authManager.showToast('Failed to submit order. Please try again.', 'error');
        }
    }

    filterMenuByCategory(categoryId) {
        this.currentCategory = categoryId;
        
        // Update active category buttons
        document.querySelectorAll('.category-btn').forEach(btn => {
            if ((categoryId === 'all' && btn.textContent === 'All Items') ||
                btn.textContent === this.categories.find(c => c.id === categoryId)?.name) {
                btn.classList.remove('bg-gray-200', 'text-gray-700');
                btn.classList.add('bg-red-600', 'text-white');
            } else {
                btn.classList.remove('bg-red-600', 'text-white');
                btn.classList.add('bg-gray-200', 'text-gray-700');
            }
        });

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
    }

    setupEventListeners() {
        // Submit order button
        document.getElementById('submit-order-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.submitOrder();
        });

        // Search functionality
        document.getElementById('menu-search')?.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const filteredItems = this.menuItems.filter(
                item => item.name.toLowerCase().includes(searchTerm) ||
                       item.description?.toLowerCase().includes(searchTerm)
            );
            this.renderMenuItems(filteredItems);
        });

        // Clear cart button
        document.querySelector('[onclick="clearCart()"]')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.clearCart();
        });

        // Save cart on page unload
        window.addEventListener('beforeunload', () => {
            this.saveCart();
        });
    }

    saveCart() {
        if (this.cart.length > 0 || this.selectedTableId) {
            const cartData = {
                cart: this.cart,
                tableId: this.selectedTableId,
                tableNumber: this.selectedTableNumber,
                timestamp: new Date().getTime()
            };
            localStorage.setItem('waiter_cart', JSON.stringify(cartData));
        }
    }

    restoreCart() {
        try {
            const saved = localStorage.getItem('waiter_cart');
            if (saved) {
                const cartData = JSON.parse(saved);
                // Check if cart is less than 1 hour old
                const oneHourAgo = new Date().getTime() - (60 * 60 * 1000);
                if (cartData.timestamp && cartData.timestamp > oneHourAgo) {
                    this.cart = cartData.cart || [];
                    if (cartData.tableId) {
                        this.selectedTableId = cartData.tableId;
                        this.selectedTableNumber = cartData.tableNumber;
                        this.updateCart();
                        // Need to wait for tables to load before selecting
                        setTimeout(() => {
                            this.selectTable(cartData.tableId, cartData.tableNumber);
                        }, 1000);
                    }
                } else {
                    // Clear old cart
                    localStorage.removeItem('waiter_cart');
                }
            }
        } catch (error) {
            console.error('Error restoring cart:', error);
            localStorage.removeItem('waiter_cart');
        }
    }

    showToast(message) {
        window.authManager.showToast(message, 'success');
    }

    showError(message) {
        window.authManager.showToast(message, 'error');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.waiterNewOrder = new WaiterNewOrder();
});