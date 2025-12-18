# tables/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Table, Cart, CartItem, Order, OrderItem
import qrcode
import io
from django.core.files.base import ContentFile


# ============ INLINE ADMIN CLASSES ============
class CartItemInline(admin.TabularInline):
    """Inline admin for Cart Items"""
    model = CartItem
    extra = 1
    readonly_fields = ['total_price']
    fields = ['menu_item', 'quantity', 'special_instructions', 'total_price']

    def total_price(self, obj):
        return f"${obj.total_price:.2f}"
    total_price.short_description = 'Total'


class OrderItemInline(admin.TabularInline):
    """Inline admin for Order Items"""
    model = OrderItem
    extra = 1
    readonly_fields = ['total_price']
    fields = ['menu_item', 'quantity', 'unit_price',
              'special_instructions', 'total_price']

    def total_price(self, obj):
        return f"${obj.total_price:.2f}"
    total_price.short_description = 'Total'


# ============ TABLE ADMIN ============
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    """Admin interface for Table model"""
    list_display = [
        'table_number',
        'table_name',
        'branch_display',
        'capacity',
        'status',
        'is_active',
        'qr_code_preview',
        'qr_expiry_status'
    ]

    list_filter = ['status', 'is_active', 'branch', 'created_at']
    search_fields = ['table_number', 'table_name', 'location_description']
    readonly_fields = [
        'qr_code_preview',
        'qr_expiry_status',
        'created_at',
        'updated_at',
        'qr_token'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('branch', 'table_number', 'table_name', 'capacity')
        }),
        ('Status & Location', {
            'fields': ('status', 'location_description', 'is_active')
        }),
        ('QR Code Information', {
            'fields': ('qr_token', 'qr_expires_at', 'qr_code', 'qr_code_preview', 'qr_expiry_status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['generate_qr_codes', 'mark_as_available', 'mark_as_occupied']

    # Custom display methods
    def branch_display(self, obj):
        return obj.branch.name if obj.branch else "No Branch"
    branch_display.short_description = 'Branch'

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="100" height="100" />',
                obj.qr_code.url
            )
        return "No QR Code"
    qr_code_preview.short_description = 'QR Code'

    def qr_expiry_status(self, obj):
        if obj.qr_expires_at:
            if obj.is_qr_valid():
                return format_html(
                    '<span style="color: green;">✓ Valid (expires {})</span>',
                    obj.qr_expires_at.strftime('%Y-%m-%d %H:%M')
                )
            else:
                return format_html(
                    '<span style="color: red;">✗ Expired</span>'
                )
        return "No QR Token"
    qr_expiry_status.short_description = 'QR Status'

    # Custom actions
    def generate_qr_codes(self, request, queryset):
        """Admin action to generate QR codes for selected tables"""
        for table in queryset:
            table.refresh_qr_token()
        self.message_user(
            request,
            f"Successfully generated QR codes for {queryset.count()} tables."
        )
    generate_qr_codes.short_description = "Generate/Refresh QR Codes"

    def mark_as_available(self, request, queryset):
        """Mark selected tables as available"""
        updated = queryset.update(status='available')
        self.message_user(request, f"Marked {updated} tables as available.")
    mark_as_available.short_description = "Mark as Available"

    def mark_as_occupied(self, request, queryset):
        """Mark selected tables as occupied"""
        updated = queryset.update(status='occupied')
        self.message_user(request, f"Marked {updated} tables as occupied.")
    mark_as_occupied.short_description = "Mark as Occupied"


# ============ CART ADMIN ============
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin interface for Cart model"""
    list_display = [
        'id',
        'user_display',
        'table_display',
        'item_count',
        'total_price_display',
        'created_at',
        'is_active'
    ]

    list_filter = ['is_active', 'created_at', 'table__branch']
    search_fields = ['user__username', 'table__table_number', 'session_id']
    readonly_fields = ['created_at', 'updated_at', 'total_price', 'item_count']

    fieldsets = (
        ('Cart Information', {
            'fields': ('session_id', 'user', 'table', 'is_active')
        }),
        ('Calculations', {
            'fields': ('total_price', 'item_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [CartItemInline]
    actions = ['deactivate_carts', 'convert_to_orders']

    # Custom display methods
    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.username} ({obj.user.role})"
        return f"Guest: {obj.session_id}"
    user_display.short_description = 'User'

    def table_display(self, obj):
        return f"Table {obj.table.table_number}"
    table_display.short_description = 'Table'

    def total_price_display(self, obj):
        return f"${obj.total_price:.2f}"
    total_price_display.short_description = 'Total Price'

    # Custom actions
    def deactivate_carts(self, request, queryset):
        """Deactivate selected carts"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} carts.")
    deactivate_carts.short_description = "Deactivate Carts"

    def convert_to_orders(self, request, queryset):
        """Convert carts to orders (for testing)"""
        from .models import Order, OrderItem

        converted = 0
        for cart in queryset.filter(is_active=True):
            if cart.items.exists():
                # Create order from cart
                order = Order.objects.create(
                    table=cart.table,
                    waiter=request.user if request.user.role in [
                        'waiter', 'admin'] else None,
                    order_type='waiter',
                    status='confirmed',
                    subtotal=cart.total_price,
                    total_amount=cart.total_price
                )

                # Convert cart items to order items
                for cart_item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        menu_item=cart_item.menu_item,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.menu_item.price,
                        special_instructions=cart_item.special_instructions
                    )

                # Deactivate cart
                cart.is_active = False
                cart.save()
                converted += 1

        self.message_user(request, f"Converted {converted} carts to orders.")
    convert_to_orders.short_description = "Convert to Orders"


# ============ ORDER ADMIN ============
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model"""
    list_display = [
        'order_number',
        'table_display',
        'waiter_display',
        'status_badge',
        'order_type',
        'total_amount_display',
        'placed_at_time',
        'is_paid',
        'actions_column'
    ]

    list_filter = [
        'status',
        'order_type',
        'is_paid',
        'placed_at',
        'table__branch'
    ]

    search_fields = [
        'order_number',
        'table__table_number',
        'customer_name',
        'waiter__username'
    ]

    readonly_fields = [
        'order_number',
        'placed_at',
        'confirmed_at',
        'preparation_started_at',
        'ready_at',
        'served_at',
        'completed_at',
        'cancelled_at',
        'subtotal',
        'tax_amount',
        'service_charge',
        'total_amount',
        'preparation_time_display'
    ]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'table', 'waiter', 'customer_name')
        }),
        ('Order Details', {
            'fields': ('order_type', 'status', 'notes', 'is_priority')
        }),
        ('Financial Information', {
            'fields': ('subtotal', 'tax_amount', 'service_charge',
                       'discount_amount', 'total_amount', 'is_paid'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('placed_at', 'confirmed_at', 'preparation_started_at',
                       'ready_at', 'served_at', 'completed_at', 'cancelled_at',
                       'preparation_time_display'),
            'classes': ('collapse',)
        }),
    )

    inlines = [OrderItemInline]

    actions = [
        'mark_as_confirmed',
        'mark_as_preparing',
        'mark_as_ready',
        'mark_as_served',
        'mark_as_completed',
        'mark_as_paid'
    ]

    # Custom display methods
    def table_display(self, obj):
        return f"Table {obj.table.table_number}"
    table_display.short_description = 'Table'

    def waiter_display(self, obj):
        if obj.waiter:
            return f"{obj.waiter.username} ({obj.waiter.role})"
        return "No waiter assigned"
    waiter_display.short_description = 'Waiter'

    def status_badge(self, obj):
        """Display status with color-coded badge"""
        color_map = {
            'pending': 'gray',
            'confirmed': 'blue',
            'preparing': 'orange',
            'ready': 'green',
            'served': 'purple',
            'completed': 'darkgreen',
            'cancelled': 'red'
        }

        color = color_map.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def total_amount_display(self, obj):
        return f"${obj.total_amount:.2f}"
    total_amount_display.short_description = 'Total'

    def placed_at_time(self, obj):
        return obj.placed_at.strftime('%H:%M') if obj.placed_at else ''
    placed_at_time.short_description = 'Time'

    def preparation_time_display(self, obj):
        """Display preparation time"""
        time = obj.get_preparation_time()
        if time:
            return f"{time:.0f} minutes"
        return "Not started"
    preparation_time_display.short_description = 'Prep Time'

    def actions_column(self, obj):
        """Quick action buttons"""
        actions = []

        if obj.status == 'pending' and obj.requires_waiter_confirmation:
            url = reverse('admin:tables_order_mark_confirmed', args=[obj.pk])
            actions.append(f'<a href="{url}" class="button">Confirm</a>')

        if obj.status == 'confirmed':
            url = reverse('admin:tables_order_mark_preparing', args=[obj.pk])
            actions.append(f'<a href="{url}" class="button">Start Prep</a>')

        if obj.status == 'preparing':
            url = reverse('admin:tables_order_mark_ready', args=[obj.pk])
            actions.append(f'<a href="{url}" class="button">Mark Ready</a>')

        if obj.status == 'ready':
            url = reverse('admin:tables_order_mark_served', args=[obj.pk])
            actions.append(f'<a href="{url}" class="button">Mark Served</a>')

        if obj.status == 'served' and not obj.is_paid:
            url = reverse('admin:tables_order_mark_paid', args=[obj.pk])
            actions.append(f'<a href="{url}" class="button">Mark Paid</a>')

        return format_html(' '.join(actions))
    actions_column.short_description = 'Actions'

    # Custom admin URLs for quick actions
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:order_id>/mark-confirmed/',
                 self.admin_site.admin_view(self.mark_confirmed_view),
                 name='tables_order_mark_confirmed'),
            path('<int:order_id>/mark-preparing/',
                 self.admin_site.admin_view(self.mark_preparing_view),
                 name='tables_order_mark_preparing'),
            path('<int:order_id>/mark-ready/',
                 self.admin_site.admin_view(self.mark_ready_view),
                 name='tables_order_mark_ready'),
            path('<int:order_id>/mark-served/',
                 self.admin_site.admin_view(self.mark_served_view),
                 name='tables_order_mark_served'),
            path('<int:order_id>/mark-paid/',
                 self.admin_site.admin_view(self.mark_paid_view),
                 name='tables_order_mark_paid'),
        ]
        return custom_urls + urls

    # Action views
    def mark_confirmed_view(self, request, order_id):
        order = self.get_object(request, order_id)
        order.mark_confirmed(request.user)
        self.message_user(request, f"Order {order.order_number} confirmed.")
        return self.redirect_to_order(order_id)

    def mark_preparing_view(self, request, order_id):
        order = self.get_object(request, order_id)
        order.mark_preparing()
        self.message_user(
            request, f"Order {order.order_number} marked as preparing.")
        return self.redirect_to_order(order_id)

    def mark_ready_view(self, request, order_id):
        order = self.get_object(request, order_id)
        order.mark_ready()
        self.message_user(
            request, f"Order {order.order_number} marked as ready.")
        return self.redirect_to_order(order_id)

    def mark_served_view(self, request, order_id):
        order = self.get_object(request, order_id)
        order.mark_served()
        self.message_user(
            request, f"Order {order.order_number} marked as served.")
        return self.redirect_to_order(order_id)

    def mark_paid_view(self, request, order_id):
        order = self.get_object(request, order_id)
        order.is_paid = True
        order.save()
        self.message_user(
            request, f"Order {order.order_number} marked as paid.")
        return self.redirect_to_order(order_id)

    def redirect_to_order(self, order_id):
        from django.urls import reverse
        from django.shortcuts import redirect
        url = reverse('admin:tables_order_change', args=[order_id])
        return redirect(url)

    # Bulk actions
    def mark_as_confirmed(self, request, queryset):
        """Mark selected orders as confirmed"""
        for order in queryset:
            order.mark_confirmed(request.user)
        self.message_user(request, f"Confirmed {queryset.count()} orders.")
    mark_as_confirmed.short_description = "Mark as Confirmed"

    def mark_as_preparing(self, request, queryset):
        """Mark selected orders as preparing"""
        queryset.update(status='preparing',
                        preparation_started_at=timezone.now())
        self.message_user(
            request, f"Marked {queryset.count()} orders as preparing.")
    mark_as_preparing.short_description = "Mark as Preparing"

    def mark_as_ready(self, request, queryset):
        """Mark selected orders as ready"""
        queryset.update(status='ready', ready_at=timezone.now())
        self.message_user(
            request, f"Marked {queryset.count()} orders as ready.")
    mark_as_ready.short_description = "Mark as Ready"

    def mark_as_served(self, request, queryset):
        """Mark selected orders as served"""
        queryset.update(status='served', served_at=timezone.now())
        self.message_user(
            request, f"Marked {queryset.count()} orders as served.")
    mark_as_served.short_description = "Mark as Served"

    def mark_as_completed(self, request, queryset):
        """Mark selected orders as completed"""
        queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(
            request, f"Marked {queryset.count()} orders as completed.")
    mark_as_completed.short_description = "Mark as Completed"

    def mark_as_paid(self, request, queryset):
        """Mark selected orders as paid"""
        updated = queryset.update(is_paid=True)
        self.message_user(request, f"Marked {updated} orders as paid.")
    mark_as_paid.short_description = "Mark as Paid"


# ============ ORDER ITEM ADMIN ============
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin interface for OrderItem model"""
    list_display = [
        'id',
        'order_display',
        'menu_item_display',
        'quantity',
        'unit_price_display',
        'total_price_display'
    ]

    list_filter = ['order__status', 'order__table__branch']
    search_fields = ['order__order_number', 'menu_item__name']
    readonly_fields = ['unit_price', 'total_price']

    # Custom display methods
    def order_display(self, obj):
        return f"Order #{obj.order.order_number}"
    order_display.short_description = 'Order'

    def menu_item_display(self, obj):
        return obj.menu_item.name
    menu_item_display.short_description = 'Menu Item'

    def unit_price_display(self, obj):
        return f"${obj.unit_price:.2f}"
    unit_price_display.short_description = 'Unit Price'

    def total_price_display(self, obj):
        return f"${obj.total_price:.2f}"
    total_price_display.short_description = 'Total'


# ============ CART ITEM ADMIN ============
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Admin interface for CartItem model"""
    list_display = [
        'id',
        'cart_display',
        'menu_item_display',
        'quantity',
        'total_price_display',
        'created_at'
    ]

    list_filter = ['cart__table__branch', 'created_at']
    search_fields = ['cart__session_id', 'menu_item__name']
    readonly_fields = ['total_price', 'created_at']

    # Custom display methods
    def cart_display(self, obj):
        if obj.cart.user:
            return f"Cart #{obj.cart.id} ({obj.cart.user.username})"
        return f"Cart #{obj.cart.id} (Guest)"
    cart_display.short_description = 'Cart'

    def menu_item_display(self, obj):
        return obj.menu_item.name
    menu_item_display.short_description = 'Menu Item'

    def total_price_display(self, obj):
        return f"${obj.total_price:.2f}"
    total_price_display.short_description = 'Total'


# ============ REGISTER ALL MODELS ============
# Note: The @admin.register decorator above already registers them
# This is just for clarity
