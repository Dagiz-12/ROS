# menu/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.core.files.storage import default_storage
from .models import Category, MenuItem
import os


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for Category model"""
    list_display = [
        'name',
        'restaurant_display',
        'order_index',
        'item_count',
        'is_active',
        'created_at'
    ]

    list_filter = ['is_active', 'restaurant', 'created_at']
    search_fields = ['name', 'description', 'restaurant__name']
    list_editable = ['order_index', 'is_active']

    fieldsets = (
        ('Basic Information', {
            'fields': ('restaurant', 'name', 'description')
        }),
        ('Display Settings', {
            'fields': ('order_index', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at']

    actions = ['activate_categories', 'deactivate_categories']

    # Custom display methods
    def restaurant_display(self, obj):
        return obj.restaurant.name
    restaurant_display.short_description = 'Restaurant'
    restaurant_display.admin_order_field = 'restaurant__name'

    def item_count(self, obj):
        count = obj.items.count()
        return format_html(
            '<span style="background-color: #4CAF50; color: white; '
            'padding: 2px 8px; border-radius: 10px;">{}</span>',
            count
        )
    item_count.short_description = 'Items'

    # Custom actions
    def activate_categories(self, request, queryset):
        """Activate selected categories"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} categories.")
    # FIX: Remove % formatting
    activate_categories.short_description = "Activate selected categories"

    def deactivate_categories(self, request, queryset):
        """Deactivate selected categories"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} categories.")
    # FIX: Remove % formatting
    deactivate_categories.short_description = "Deactivate selected categories"


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin interface for MenuItem model"""
    list_display = [
        'name',
        'category_display',
        'price_display',
        'image_preview',
        'preparation_time',
        'is_available',
        'created_at'
    ]

    list_filter = [
        'is_available',
        'category__restaurant',
        'category',
        'created_at'
    ]

    search_fields = [
        'name',
        'description',
        'category__name',
        'category__restaurant__name'
    ]

    list_editable = ['preparation_time', 'is_available']

    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'description')
        }),
        ('Pricing & Image', {
            'fields': ('price', 'image', 'image_preview')
        }),
        ('Details', {
            'fields': ('preparation_time', 'is_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'image_preview']

    actions = [
        'mark_as_available',
        'mark_as_unavailable',
        'increase_price_10',
        'decrease_price_10'
    ]

    # Custom display methods
    def category_display(self, obj):
        return f"{obj.category.name} ({obj.category.restaurant.name})"
    category_display.short_description = 'Category'
    category_display.admin_order_field = 'category__name'

    def price_display(self, obj):
        return f"${obj.price:.2f}"
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price'

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 5px;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = 'Preview'

    def availability_status(self, obj):
        if obj.is_available:
            return format_html(
                '<span style="background-color: #4CAF50; color: white; '
                'padding: 2px 8px; border-radius: 10px;">Available</span>'
            )
        return format_html(
            '<span style="background-color: #f44336; color: white; '
            'padding: 2px 8px; border-radius: 10px;">Unavailable</span>'
        )
    availability_status.short_description = 'Status'

    # Custom actions

    def mark_as_available(self, request, queryset):
        """Mark selected items as available"""
        updated = queryset.update(is_available=True)
        self.message_user(request, f"Marked {updated} items as available.")
    # FIX: Remove % formatting from short_description
    mark_as_available.short_description = "Mark selected items as available"

    def mark_as_unavailable(self, request, queryset):
        """Mark selected items as unavailable"""
        updated = queryset.update(is_available=False)
        self.message_user(request, f"Marked {updated} items as unavailable.")
    # FIX: Remove % formatting from short_description
    mark_as_unavailable.short_description = "Mark selected items as unavailable"

    def increase_price_10(self, request, queryset):
        """Increase price by 10% for selected items"""
        for item in queryset:
            item.price *= 1.10  # Increase by 10%
            item.save(update_fields=['price'])
        self.message_user(
            request, f"Increased price for {queryset.count()} items by 10%.")
    # FIX: Remove % formatting from short_description
    increase_price_10.short_description = "Increase price by 10 percent"

    def decrease_price_10(self, request, queryset):
        """Decrease price by 10% for selected items"""
        for item in queryset:
            item.price *= 0.90  # Decrease by 10%
            item.save(update_fields=['price'])
        self.message_user(
            request, f"Decreased price for {queryset.count()} items by 10%.")
    # FIX: Remove % formatting from short_description
    decrease_price_10.short_description = "Decrease price by 10 percent"

    # Custom save method to handle image cleanup
    def save_model(self, request, obj, form, change):
        if change and 'image' in form.changed_data:
            # Delete old image if new one is uploaded
            old_obj = MenuItem.objects.get(pk=obj.pk)
            if old_obj.image and old_obj.image != obj.image:
                if default_storage.exists(old_obj.image.name):
                    default_storage.delete(old_obj.image.name)

        super().save_model(request, obj, form, change)


# Custom admin site configuration
admin.site.site_header = "Restaurant Ordering System"
admin.site.site_title = "Restaurant Admin"
admin.site.index_title = "Welcome to Restaurant Ordering System"
