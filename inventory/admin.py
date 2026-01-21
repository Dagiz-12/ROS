# inventory/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import StockItem, StockTransaction, StockAlert, Recipe, InventoryReport
from decimal import Decimal


class StockItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'current_quantity', 'unit', 'cost_per_unit',
                    'minimum_quantity', 'reorder_quantity',  # Added these
                    'stock_value', 'is_low_stock_display', 'needs_reorder_display', 'restaurant', 'branch']
    list_filter = ['category', 'is_active', 'restaurant', 'branch']
    search_fields = ['name', 'description', 'supplier']
    list_editable = ['minimum_quantity', 'reorder_quantity',
                     'cost_per_unit']  # These are now in list_display
    readonly_fields = ['stock_value', 'is_low_stock',
                       'needs_reorder', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'unit')
        }),
        ('Stock Levels', {
            'fields': ('current_quantity', 'minimum_quantity', 'reorder_quantity')
        }),
        ('Cost Information', {
            'fields': ('cost_per_unit', 'last_purchase_price')
        }),
        ('Supplier Information', {
            'fields': ('supplier', 'supplier_code')
        }),
        ('Restaurant', {
            'fields': ('restaurant', 'branch')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Calculated Fields', {
            'fields': ('stock_value', 'is_low_stock', 'needs_reorder')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def is_low_stock_display(self, obj):
        if obj.is_low_stock:
            return format_html('<span style="color: red; font-weight: bold;">⚠ LOW</span>')
        return format_html('<span style="color: green;">✓ OK</span>')
    is_low_stock_display.short_description = 'Stock Status'

    def needs_reorder_display(self, obj):
        if obj.needs_reorder:
            return format_html('<span style="color: orange; font-weight: bold;">🔄 REORDER</span>')
        return 'No'
    needs_reorder_display.short_description = 'Reorder Needed'

    def stock_value(self, obj):
        return f"${obj.stock_value:.2f}"
    stock_value.short_description = 'Stock Value'


class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_date', 'stock_item', 'transaction_type', 'quantity',
                    'unit_cost', 'total_cost', 'user', 'restaurant', 'branch']
    list_filter = ['transaction_type',
                   'transaction_date', 'restaurant', 'branch']
    search_fields = ['stock_item__name', 'reference_number', 'reason']
    readonly_fields = ['created_at']
    date_hierarchy = 'transaction_date'

    fieldsets = (
        ('Transaction Details', {
            'fields': ('stock_item', 'transaction_type', 'quantity', 'unit_cost', 'total_cost')
        }),
        ('Reference Information', {
            'fields': ('reference_number', 'reason')
        }),
        ('Related Items', {
            'fields': ('order', 'menu_item')
        }),
        ('User Information', {
            'fields': ('user',)
        }),
        ('Restaurant', {
            'fields': ('restaurant', 'branch')
        }),
        ('Timestamps', {
            'fields': ('transaction_date', 'created_at')
        }),
    )


class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'stock_item', 'alert_type', 'message_short',
                    'resolved_display', 'restaurant', 'branch']
    list_filter = ['alert_type', 'resolved',
                   'created_at', 'restaurant', 'branch']
    search_fields = ['stock_item__name', 'message']
    readonly_fields = ['created_at', 'resolved_at', 'resolved_by']
    actions = ['mark_as_resolved']

    def message_short(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_short.short_description = 'Message'

    def resolved_display(self, obj):
        if obj.resolved:
            return format_html('<span style="color: green;">✓ Resolved</span>')
        return format_html('<span style="color: red; font-weight: bold;">⚠ Active</span>')
    resolved_display.short_description = 'Status'

    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(
            resolved=True, resolved_at=timezone.now(), resolved_by=request.user)
        self.message_user(request, f'{updated} alert(s) marked as resolved.')
    mark_as_resolved.short_description = "Mark selected alerts as resolved"


# Update the RecipeAdmin in inventory/admin.py

class RecipeAdmin(admin.ModelAdmin):
    list_display = ['menu_item', 'stock_item', 'quantity_required', 'unit_display',
                    'ingredient_cost_display', 'waste_factor', 'restaurant']
    list_filter = ['menu_item__category', 'stock_item__category']
    search_fields = ['menu_item__name', 'stock_item__name']
    readonly_fields = ['ingredient_cost', 'created_at', 'updated_at']

    # Add form field customization
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'quantity_required':
            field.initial = Decimal('0.000')  # Set default initial value
        return field

    def unit_display(self, obj):
        return obj.stock_item.unit if obj.stock_item else 'N/A'
    unit_display.short_description = 'Unit'

    def ingredient_cost_display(self, obj):
        try:
            cost = obj.ingredient_cost
            return f"${cost:.2f}"
        except (AttributeError, TypeError):
            return f"$0.00"
    ingredient_cost_display.short_description = 'Ingredient Cost'

    def restaurant(self, obj):
        if obj.menu_item and obj.menu_item.category:
            return obj.menu_item.category.restaurant
        return 'N/A'
    restaurant.short_description = 'Restaurant'


class InventoryReportAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'report_type', 'title', 'start_date', 'end_date',
                    'generated_by', 'restaurant', 'branch']
    list_filter = ['report_type', 'created_at', 'restaurant', 'branch']
    search_fields = ['title', 'summary']
    readonly_fields = ['created_at', 'data', 'summary']

    fieldsets = (
        ('Report Information', {
            'fields': ('report_type', 'title', 'summary')
        }),
        ('Date Range', {
            'fields': ('start_date', 'end_date')
        }),
        ('Report Data', {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
        ('Generation Info', {
            'fields': ('generated_by', 'restaurant', 'branch')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )


admin.site.register(StockItem, StockItemAdmin)
admin.site.register(StockTransaction, StockTransactionAdmin)
admin.site.register(StockAlert, StockAlertAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(InventoryReport, InventoryReportAdmin)
