# restaurants/admin.py
from django.contrib import admin
from .models import Restaurant, Branch


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone', 'email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'logo', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('address', 'phone', 'email')
        }),
        ('Configuration', {
            'fields': ('config_json',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'location', 'is_active')
    list_filter = ('restaurant', 'is_active')
    search_fields = ('name', 'location', 'phone')
    autocomplete_fields = ['restaurant']
