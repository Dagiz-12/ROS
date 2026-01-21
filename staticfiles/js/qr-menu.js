// static/js/qr-menu.js

class QRMenu {
    constructor() {
        this.config = {
            restaurantId: null,
            tableId: null,
            tableToken: null,
            apiBase: window.location.origin + '/api',
            cart: {
                items: [],
                subtotal: 0,
                taxRate: 0.15,
            },
        };
        
        this.elements = {};
        this.activeCategory = 'all';
        this.menuData = {
            categories: [],
            items: []
        };
        
        this.initialize();
    }
    
    initialize() {
        this.cacheElements();
        this.parseUrlParameters();
        this.setupEventListeners();
        this.loadInitialData();
    }
    
    cacheElements() {
        // Cache all DOM elements
        const getElement = id => document.getElementById(id);
        
        this.elements = {
            // Header
            restaurantInitial: getElement('restaurant-initial'),
            restaurantName: getElement('restaurant-name'),
            tableNumber: getElement('table-number'),
            
            // Menu
            categories: getElement('categories'),
            menuItems: getElement('menu-items'),
            searchInput: getElement('search-input'),
            
            // Cart
            cartTableNumber: getElement('cart-table-number'),
            cartCount: getElement('cart-count'),
            cartItems: getElement('cart-items'),
            cartSubtotal: getElement('cart-subtotal'),
            cartTax: getElement('cart-tax'),
            cartTotal: getElement('cart-total'),
            cartToggle: getElement('cart-toggle'),
            closeCart: getElement('close-cart'),
            cartSidebar: getElement('cart-sidebar'),
            cartOverlay: getElement('cart-overlay'),
            submitOrder: getElement('submit-order'),
            clearCart: getElement('clear-cart'),
            specialInstructions: getElement('special-instructions'),
            
            // Loading
            loadingSpinner: getElement('loading-spinner'),
            
            // Toast
            toastContainer: getElement('toast-container')
        };
    }
    
    parseUrlParameters() {
        // Extract restaurant_id and table_id from URL path
        const pathParts = window.location.pathname.split('/').filter(part => part);
        
        // URL format: /qr-menu/{restaurant_id}/{table_id}/
        if (pathParts.length >= 3 && pathParts[0] === 'qr-menu') {
            this.config.restaurantId = parseInt(pathParts[1]) || 1;
            this.config.tableId = parseInt(pathParts[2]) || 1;
        } else {
            // Default fallback
            this.config.restaurantId = 1;
            this.config.tableId = 1;
        }
        
        // Also check query parameters
        const urlParams = new URLSearchParams(window.location.search);
        this.config.tableToken = urlParams.get("token") || "demo-token";
        
        // Update UI with table info
        this.elements.tableNumber.textContent = this.config.tableId;
        this.elements.cartTableNumber.textContent = this.config.tableId;
        
        console.log(`QR Menu initialized for Restaurant ${this.config.restaurantId}, Table ${this.config.tableId}`);
    }
    
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadRestaurantData(),
                this.loadMenuData()
            ]);
        } catch (error) {
            console.error("Error loading initial data:", error);
            this.showError("Failed to load menu data. Please try again.");
        }
        this.loadCartFromStorage();
    }
    
    async loadRestaurantData() {
        try {
            const response = await fetch(
                `${this.config.apiBase}/restaurants/restaurants/${this.config.restaurantId}/`
            );
            
            if (response.ok) {
                const data = await response.json();
                this.elements.restaurantName.textContent = data.name || "Restaurant";
                this.elements.restaurantInitial.textContent = data.name ? data.name.charAt(0).toUpperCase() : 'R';
                document.title = `${data.name} - QR Menu`;
            } else {
                console.warn("Could not load restaurant data, using defaults");
            }
        } catch (error) {
            console.error("Error loading restaurant:", error);
        }
    }
    
    async loadMenuData() {
        try {
            this.showLoading();
            
            console.log(`Loading menu from: ${this.config.apiBase}/menu/public/${this.config.restaurantId}/`);
            const response = await fetch(
                `${this.config.apiBase}/menu/public/${this.config.restaurantId}/`
            );
            
            console.log(`Response status: ${response.status}`);
            
            if (response.ok) {
                const data = await response.json();
                console.log("Menu data structure:", data);
                
                // DEBUG: Log the actual data structure
                console.log("Categories:", data.categories);
                console.log("Items in first category:", data.categories?.[0]?.items);
                
                // Store the data
                this.menuData = data;
                
                // Extract all items from categories for filtering
                this.menuData.items = [];
                if (data.categories && Array.isArray(data.categories)) {
                    data.categories.forEach(category => {
                        if (category.items && Array.isArray(category.items)) {
                            category.items.forEach(item => {
                                item.category_id = category.id;
                                this.menuData.items.push(item);
                            });
                        }
                    });
                }
                
                console.log(`Loaded ${this.menuData.items.length} items`);
                
                // Render UI
                this.renderCategories(data.categories || []);
                this.renderMenuItems(this.menuData.items);
                
            } else {
                const errorText = await response.text();
                console.error("API Error response:", errorText);
                throw new Error(`Menu API Error: ${response.status}`);
            }
        } catch (error) {
            console.error("Error loading menu:", error);
            this.showError("Failed to load menu. Please refresh or contact staff.");
        } finally {
            this.hideLoading();
        }
    }
    
    renderCategories(categories) {
        if (!categories || !Array.isArray(categories)) {
            console.error("Invalid categories data:", categories);
            return;
        }
        
        this.elements.categories.innerHTML = '';
        
        // Add "All Items" category
        const allCategory = this.createCategoryElement("All Items", "all", this.activeCategory === 'all');
        this.elements.categories.appendChild(allCategory);
        
        // Add other categories
        categories.forEach(category => {
            if (!category || !category.name) {
                console.warn("Skipping invalid category:", category);
                return;
            }
            
            const isActive = this.activeCategory === category.id.toString();
            const categoryEl = this.createCategoryElement(
                category.name, 
                category.id, 
                isActive
            );
            this.elements.categories.appendChild(categoryEl);
        });
    }
    
    createCategoryElement(name, id, isActive = false) {
        const element = document.createElement('div');
        element.className = `category-tab px-4 py-2 rounded-full cursor-pointer transition flex-shrink-0 ${isActive ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`;
        element.textContent = name;
        element.dataset.categoryId = id;
        
        element.addEventListener('click', () => {
            this.filterItemsByCategory(id);
            
            // Update active state
            document.querySelectorAll('.category-tab').forEach(tab => {
                const tabId = tab.dataset.categoryId;
                if (tabId === id.toString()) {
                    tab.classList.remove('bg-gray-200', 'text-gray-700');
                    tab.classList.add('bg-red-600', 'text-white');
                } else {
                    tab.classList.remove('bg-red-600', 'text-white');
                    tab.classList.add('bg-gray-200', 'text-gray-700');
                }
            });
        });
        
        return element;
    }
    
    renderMenuItems(items) {
        if (!items || !Array.isArray(items)) {
            console.error("Invalid items data:", items);
            this.elements.menuItems.innerHTML = `
                <div class="col-span-3 text-center py-12 text-gray-500">
                    <i class="fas fa-exclamation-triangle text-4xl mb-4"></i>
                    <p>No menu items available</p>
                </div>
            `;
            return;
        }
        
        if (items.length === 0) {
            this.elements.menuItems.innerHTML = `
                <div class="col-span-3 text-center py-12 text-gray-500">
                    <i class="fas fa-utensils text-4xl mb-4"></i>
                    <p>No menu items available in this category</p>
                </div>
            `;
            return;
        }
        
        this.elements.menuItems.innerHTML = '';
        
        items.forEach(item => {
            if (!item || !item.name) {
                console.warn("Skipping invalid item:", item);
                return;
            }
            
            const itemEl = this.createMenuItemElement(item);
            this.elements.menuItems.appendChild(itemEl);
        });
    }
    
    createMenuItemElement(item) {
        const element = document.createElement('div');
        element.className = 'item-card bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition';
        
        const imageUrl = item.image || 'https://via.placeholder.com/400x300/FF6B6B/FFFFFF?text=Food';
        const isAvailable = item.is_available !== false;
        
        element.innerHTML = `
            <div class="relative">
                <img src="${imageUrl}" 
                     alt="${item.name}" 
                     class="w-full h-48 object-cover">
                ${!isAvailable ? `
                    <div class="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
                        <span class="bg-red-600 text-white px-3 py-1 rounded-full text-sm">Unavailable</span>
                    </div>
                ` : ''}
            </div>
            <div class="p-4">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-lg">${item.name}</h3>
                    <span class="font-bold text-red-600">${this.formatCurrency(item.price || 0)}</span>
                </div>
                <p class="text-gray-600 text-sm mb-4">${item.description || 'Delicious dish'}</p>
                <div class="flex justify-between items-center">
                    <span class="text-sm text-gray-500">
                        <i class="fas fa-clock mr-1"></i> ${item.preparation_time || 15} min
                    </span>
                    <button class="add-to-cart-btn bg-red-50 text-red-600 px-4 py-2 rounded-lg hover:bg-red-100 transition ${!isAvailable ? 'opacity-50 cursor-not-allowed' : ''}"
                            data-item-id="${item.id}"
                            data-item-name="${item.name}"
                            data-item-price="${item.price || 0}"
                            ${!isAvailable ? 'disabled' : ''}>
                        <i class="fas fa-plus mr-2"></i>Add
                    </button>
                </div>
            </div>
        `;
        
        // Add event listener to the button
        const button = element.querySelector('.add-to-cart-btn');
        if (button && isAvailable) {
            button.addEventListener('click', () => {
                this.addToCart(
                    item.id,
                    item.name,
                    item.price || 0
                );
            });
        }
        
        return element;
    }
    
    filterItemsByCategory(categoryId) {
        this.activeCategory = categoryId;
        
        let filteredItems = [];
        
        if (categoryId === 'all') {
            filteredItems = this.menuData.items;
        } else {
            filteredItems = this.menuData.items.filter(
                item => item.category_id && item.category_id.toString() === categoryId.toString()
            );
        }
        
        this.renderMenuItems(filteredItems);
    }
    
    // Cart Functions
    addToCart(itemId, itemName, itemPrice, quantity = 1) {
        const existingItemIndex = this.config.cart.items.findIndex(
            item => item.id === itemId
        );
        
        if (existingItemIndex > -1) {
            this.config.cart.items[existingItemIndex].quantity += quantity;
        } else {
            this.config.cart.items.push({
                id: itemId,
                name: itemName,
                price: itemPrice,
                quantity: quantity,
                specialInstructions: "",
            });
        }
        
        this.updateCart();
        this.showToast(`${itemName} added to cart!`, 'success');
    }
    
    updateCart() {
        // Calculate totals
        this.config.cart.subtotal = this.config.cart.items.reduce((total, item) => {
            return total + (item.price * item.quantity);
        }, 0);
        
        const tax = this.config.cart.subtotal * this.config.cart.taxRate;
        const total = this.config.cart.subtotal + tax;
        
        // Update UI
        this.elements.cartCount.textContent = this.config.cart.items.reduce(
            (sum, item) => sum + item.quantity,
            0
        );
        
        this.elements.cartSubtotal.textContent = this.formatCurrency(this.config.cart.subtotal);
        this.elements.cartTax.textContent = this.formatCurrency(tax);
        this.elements.cartTotal.textContent = this.formatCurrency(total);
        
        // Enable/disable submit button
        this.elements.submitOrder.disabled = this.config.cart.items.length === 0;
        
        // Render cart items
        this.renderCartItems();
        
        // Save to localStorage
        this.saveCartToStorage();
    }
    
    renderCartItems() {
        if (this.config.cart.items.length === 0) {
            this.elements.cartItems.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <i class="fas fa-shopping-cart text-4xl mb-4"></i>
                    <p>Your cart is empty</p>
                    <p class="text-sm mt-2">Add items from the menu</p>
                </div>
            `;
            return;
        }
        
        this.elements.cartItems.innerHTML = '';
        
        this.config.cart.items.forEach((item, index) => {
            const itemTotal = item.price * item.quantity;
            const itemEl = document.createElement('div');
            itemEl.className = 'cart-item-added bg-white border rounded-lg p-4 mb-3';
            itemEl.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <h4 class="font-bold">${item.name}</h4>
                    <button class="remove-item text-red-600 hover:text-red-800" data-index="${index}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="flex justify-between items-center">
                    <div class="flex items-center">
                        <button class="quantity-btn bg-gray-100 w-8 h-8 rounded-full" data-index="${index}" data-action="decrease">-</button>
                        <span class="mx-3 font-bold">${item.quantity}</span>
                        <button class="quantity-btn bg-gray-100 w-8 h-8 rounded-full" data-index="${index}" data-action="increase">+</button>
                    </div>
                    <span class="font-bold">${this.formatCurrency(itemTotal)}</span>
                </div>
                <div class="mt-2">
                    <input type="text" 
                           class="w-full p-2 border rounded text-sm" 
                           placeholder="Special instructions"
                           value="${item.specialInstructions || ''}"
                           data-index="${index}">
                </div>
            `;
            
            this.elements.cartItems.appendChild(itemEl);
        });
        
        // Add event listeners for cart item buttons
        this.elements.cartItems.querySelectorAll('.remove-item').forEach(button => {
            button.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.removeFromCart(index);
            });
        });
        
        this.elements.cartItems.querySelectorAll('.quantity-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                const action = e.currentTarget.dataset.action;
                this.updateQuantity(index, action);
            });
        });
        
        this.elements.cartItems.querySelectorAll('input[placeholder="Special instructions"]').forEach(input => {
            input.addEventListener('change', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.updateSpecialInstructions(index, e.currentTarget.value);
            });
        });
    }
    
    removeFromCart(index) {
        this.config.cart.items.splice(index, 1);
        this.updateCart();
        this.showToast('Item removed from cart', 'info');
    }
    
    updateQuantity(index, action) {
        if (action === 'increase') {
            this.config.cart.items[index].quantity += 1;
        } else if (action === 'decrease') {
            if (this.config.cart.items[index].quantity > 1) {
                this.config.cart.items[index].quantity -= 1;
            } else {
                this.removeFromCart(index);
                return;
            }
        }
        this.updateCart();
    }
    
    updateSpecialInstructions(index, instructions) {
        this.config.cart.items[index].specialInstructions = instructions;
        this.saveCartToStorage();
    }
    
    clearCart() {
        if (this.config.cart.items.length === 0) return;
        
        if (confirm('Are you sure you want to clear your cart?')) {
            this.config.cart.items = [];
            this.updateCart();
            this.showToast('Cart cleared', 'info');
        }
    }
    
    async submitOrder() {
        if (this.config.cart.items.length === 0) return;
        
        try {
            this.showLoading();
            
            const orderData = {
                table_id: this.config.tableId,
                order_type: "qr",
                customer_name: "QR Customer",
                items: this.config.cart.items.map(item => ({
                    menu_item_id: item.id,
                    quantity: item.quantity,
                    special_instructions: item.specialInstructions,
                })),
                special_instructions: this.elements.specialInstructions.value,
            };
            
            console.log('Submitting order:', orderData);
            
            const response = await fetch(
                `${this.config.apiBase}/tables/submit-qr-order/`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(orderData),
                }
            );
            
            if (response.ok) {
                const orderResult = await response.json();
                
                // Clear cart
                this.config.cart.items = [];
                this.elements.specialInstructions.value = '';
                this.updateCart();
                
                // Show success message
                this.showToast(`Order #${orderResult.order_number || 'N/A'} submitted successfully!`, 'success');
                this.closeCartSidebar();
                
            } else {
                const errorText = await response.text();
                throw new Error(`Order submission failed: ${errorText}`);
            }
            
        } catch (error) {
            console.error('Error submitting order:', error);
            this.showToast('Failed to submit order. Please try again.', 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    // Storage functions
    saveCartToStorage() {
        const cartData = {
            items: this.config.cart.items,
            tableId: this.config.tableId,
            timestamp: new Date().toISOString(),
        };
        localStorage.setItem(
            `restaurant_cart_${this.config.tableId}`,
            JSON.stringify(cartData)
        );
    }
    
    loadCartFromStorage() {
        const savedCart = localStorage.getItem(
            `restaurant_cart_${this.config.tableId}`
        );
        if (savedCart) {
            try {
                const cartData = JSON.parse(savedCart);
                this.config.cart.items = cartData.items || [];
                this.updateCart();
            } catch (error) {
                console.error('Error loading cart from storage:', error);
            }
        }
    }
    
    // UI Helpers
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `p-4 rounded-lg shadow-lg transform transition-transform duration-300 translate-x-full ${type === 'success' ? 'bg-green-500' : 'bg-red-500'} text-white`;
        toast.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} mr-3"></i>
                <span>${message}</span>
            </div>
        `;
        
        this.elements.toastContainer.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
        }, 10);
        
        // Remove after 3 seconds
        setTimeout(() => {
            toast.classList.add('translate-x-full');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
    
    showError(message) {
        this.elements.menuItems.innerHTML = `
            <div class="col-span-3 text-center py-12">
                <div class="bg-red-50 border border-red-200 rounded-lg p-6 inline-block">
                    <i class="fas fa-exclamation-triangle text-red-600 text-4xl mb-4"></i>
                    <p class="text-red-800 font-bold">${message}</p>
                    <button onclick="location.reload()" class="mt-4 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition">
                        Try Again
                    </button>
                </div>
            </div>
        `;
    }
    
    showLoading() {
        this.elements.loadingSpinner.classList.remove('hidden');
    }
    
    hideLoading() {
        this.elements.loadingSpinner.classList.add('hidden');
    }
    
    openCartSidebar() {
        this.elements.cartSidebar.classList.remove('translate-x-full');
        this.elements.cartOverlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
    
    closeCartSidebar() {
        this.elements.cartSidebar.classList.add('translate-x-full');
        this.elements.cartOverlay.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }
    
    formatCurrency(amount) {
        return `$${parseFloat(amount).toFixed(2)}`;
    }
    
    // Setup event listeners
    setupEventListeners() {
        // Cart toggle
        this.elements.cartToggle.addEventListener('click', () => this.openCartSidebar());
        this.elements.closeCart.addEventListener('click', () => this.closeCartSidebar());
        this.elements.cartOverlay.addEventListener('click', () => this.closeCartSidebar());
        
        // Order buttons
        this.elements.submitOrder.addEventListener('click', () => this.submitOrder());
        this.elements.clearCart.addEventListener('click', () => this.clearCart());
        
        // Search
        this.elements.searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            this.filterItemsBySearch(searchTerm);
        });
        
        // Close cart with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeCartSidebar();
            }
        });
    }
    
    filterItemsBySearch(searchTerm) {
        if (!searchTerm.trim()) {
            // If search is empty, show items based on active category
            if (this.activeCategory === 'all') {
                this.renderMenuItems(this.menuData.items);
            } else {
                const filtered = this.menuData.items.filter(
                    item => item.category_id && item.category_id.toString() === this.activeCategory.toString()
                );
                this.renderMenuItems(filtered);
            }
            return;
        }
        
        const filteredItems = this.menuData.items.filter(item => {
            const nameMatch = item.name && item.name.toLowerCase().includes(searchTerm);
            const descMatch = item.description && item.description.toLowerCase().includes(searchTerm);
            return nameMatch || descMatch;
        });
        
        this.renderMenuItems(filteredItems);
    }
}

// Make QRMenu available globally
window.QRMenu = QRMenu;