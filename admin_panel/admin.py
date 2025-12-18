# admin_panel/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import RestaurantAnalytics, StaffPerformance, InventoryAlert, DailyReport


@admin.register(RestaurantAnalytics)
class RestaurantAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for RestaurantAnalytics model"""
    list_display = [
        'restaurant_display',
        'date',
        'total_orders',
        'total_revenue_display',
        'average_order_value_display',
        'most_popular_item_display',
        'peak_hour_formatted'
    ]

    list_filter = ['date', 'restaurant']
    search_fields = ['restaurant__name', 'most_popular_item__name']
    date_hierarchy = 'date'

    readonly_fields = [
        'restaurant',
        'date',
        'total_orders',
        'total_revenue',
        'average_order_value',
        'most_popular_item',
        'peak_hour'
    ]

    fieldsets = (
        ('Restaurant & Date', {
            'fields': ('restaurant', 'date')
        }),
        ('Order Statistics', {
            'fields': ('total_orders', 'total_revenue', 'average_order_value')
        }),
        ('Popular Items', {
            'fields': ('most_popular_item', 'peak_hour')
        }),
    )

    # Disable add permission (should be generated automatically)
    def has_add_permission(self, request):
        return False

    # Custom display methods
    def restaurant_display(self, obj):
        return obj.restaurant.name
    restaurant_display.short_description = 'Restaurant'

    def total_revenue_display(self, obj):
        return f"${obj.total_revenue:,.2f}"
    total_revenue_display.short_description = 'Revenue'

    def average_order_value_display(self, obj):
        return f"${obj.average_order_value:.2f}"
    average_order_value_display.short_description = 'Avg Order'

    def most_popular_item_display(self, obj):
        if obj.most_popular_item:
            return obj.most_popular_item.name
        return "-"
    most_popular_item_display.short_description = 'Popular Item'

    def peak_hour_formatted(self, obj):
        if obj.peak_hour:
            return obj.peak_hour.strftime('%H:%M')
        return "-"
    peak_hour_formatted.short_description = 'Peak Hour'


@admin.register(StaffPerformance)
class StaffPerformanceAdmin(admin.ModelAdmin):
    """Admin interface for StaffPerformance model"""
    list_display = [
        'staff_display',
        'date',
        'role_display',
        'orders_count',
        'performance_score',
        'average_preparation_time_display',
        'total_sales_display'
    ]

    list_filter = ['date', 'staff__role']
    search_fields = ['staff__username', 'staff__email']
    date_hierarchy = 'date'

    readonly_fields = [
        'staff',
        'date',
        'orders_served',
        'orders_prepared',
        'average_preparation_time',
        'total_sales'
    ]

    fieldsets = (
        ('Staff & Date', {
            'fields': ('staff', 'date')
        }),
        ('Performance Metrics', {
            'fields': ('orders_served', 'orders_prepared',
                       'average_preparation_time', 'total_sales')
        }),
    )

    # Custom display methods
    def staff_display(self, obj):
        return f"{obj.staff.username} ({obj.staff.get_role_display()})"
    staff_display.short_description = 'Staff Member'

    def role_display(self, obj):
        role = obj.staff.role
        color = {
            'waiter': 'blue',
            'chef': 'green',
            'manager': 'purple'
        }.get(role, 'gray')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 10px;">{}</span>',
            color, obj.staff.get_role_display()
        )
    role_display.short_description = 'Role'

    def orders_count(self, obj):
        if obj.staff.role == 'waiter':
            count = obj.orders_served
            label = 'Served'
        else:  # chef
            count = obj.orders_prepared
            label = 'Prepared'

        return f"{count} {label}"
    orders_count.short_description = 'Orders'

    def performance_score(self, obj):
        """Calculate a simple performance score"""
        if obj.staff.role == 'waiter':
            score = min(obj.orders_served * 10, 100)
        else:  # chef
            # Lower prep time = better score
            if obj.average_preparation_time > 0:
                score = min(
                    100, max(0, 100 - (obj.average_preparation_time - 15) * 2))
            else:
                score = 0

        if score >= 80:
            color = 'green'
            emoji = '⭐'
        elif score >= 60:
            color = 'orange'
            emoji = '👍'
        else:
            color = 'red'
            emoji = '📊'

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 10px;">{} {}%</span>',
            color, emoji, int(score)
        )
    performance_score.short_description = 'Score'

    def average_preparation_time_display(self, obj):
        if obj.average_preparation_time > 0:
            return f"{obj.average_preparation_time} min"
        return "-"
    average_preparation_time_display.short_description = 'Avg Prep Time'

    def total_sales_display(self, obj):
        if obj.total_sales > 0:
            return f"${obj.total_sales:,.2f}"
        return "-"
    total_sales_display.short_description = 'Sales'


@admin.register(InventoryAlert)
class InventoryAlertAdmin(admin.ModelAdmin):
    """Admin interface for InventoryAlert model"""
    list_display = [
        'item_name',
        'restaurant_display',
        'current_quantity_display',
        'minimum_quantity_display',
        'alert_type_badge',
        'status_badge',
        'created_at_time',
        'actions_column'
    ]

    list_filter = ['alert_type', 'is_resolved', 'restaurant', 'created_at']
    search_fields = ['item_name', 'restaurant__name']

    readonly_fields = ['created_at', 'resolved_at']

    fieldsets = (
        ('Alert Information', {
            'fields': ('restaurant', 'item_name', 'alert_type')
        }),
        ('Quantity Details', {
            'fields': ('current_quantity', 'minimum_quantity')
        }),
        ('Resolution Status', {
            'fields': ('is_resolved', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_resolved', 'mark_as_unresolved']

    # Custom display methods
    def restaurant_display(self, obj):
        return obj.restaurant.name
    restaurant_display.short_description = 'Restaurant'

    def current_quantity_display(self, obj):
        return f"{obj.current_quantity}"
    current_quantity_display.short_description = 'Current'

    def minimum_quantity_display(self, obj):
        return f"{obj.minimum_quantity}"
    minimum_quantity_display.short_description = 'Minimum'

    def alert_type_badge(self, obj):
        color_map = {
            'low_stock': 'orange',
            'out_of_stock': 'red',
            'expiring_soon': 'yellow'
        }

        color = color_map.get(obj.alert_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: {}; '
            'padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            color, 'white' if color != 'yellow' else 'black',
            obj.get_alert_type_display().replace('_', ' ').title()
        )
    alert_type_badge.short_description = 'Alert Type'

    def status_badge(self, obj):
        if obj.is_resolved:
            return format_html(
                '<span style="background-color: green; color: white; '
                'padding: 2px 8px; border-radius: 10px;">Resolved</span>'
            )
        return format_html(
            '<span style="background-color: red; color: white; '
            'padding: 2px 8px; border-radius: 10px;">Active</span>'
        )
    status_badge.short_description = 'Status'

    def created_at_time(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_time.short_description = 'Created'

    def actions_column(self, obj):
        """Quick action buttons"""
        if not obj.is_resolved:
            url = reverse(
                'admin:admin_panel_inventoryalert_mark_resolved', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="background-color: #4CAF50; '
                'color: white; padding: 5px 10px; text-decoration: none; '
                'border-radius: 3px;">Mark Resolved</a>', url
            )
        return "-"
    actions_column.short_description = 'Actions'

    # Custom admin URLs for quick actions
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:alert_id>/mark-resolved/',
                 self.admin_site.admin_view(self.mark_resolved_view),
                 name='admin_panel_inventoryalert_mark_resolved'),
        ]
        return custom_urls + urls

    # Action view
    def mark_resolved_view(self, request, alert_id):
        alert = self.get_object(request, alert_id)
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        self.message_user(
            request, f"Inventory alert for '{alert.item_name}' has been resolved.")
        return self.redirect_to_alert(alert_id)

    def redirect_to_alert(self, alert_id):
        from django.urls import reverse
        from django.shortcuts import redirect
        url = reverse('admin:admin_panel_inventoryalert_change',
                      args=[alert_id])
        return redirect(url)

    # Custom actions
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(is_resolved=True, resolved_at=timezone.now())
        self.message_user(request, f"Marked {updated} alerts as resolved.")
    mark_as_resolved.short_description = "Mark as resolved"

    def mark_as_unresolved(self, request, queryset):
        updated = queryset.update(is_resolved=False, resolved_at=None)
        self.message_user(request, f"Marked {updated} alerts as unresolved.")
    mark_as_unresolved.short_description = "Mark as unresolved"


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    """Admin interface for DailyReport model"""
    list_display = [
        'restaurant_display',
        'report_date',
        'report_type_badge',
        'data_preview',
        'generated_at_time',
        'sent_status'
    ]

    list_filter = ['report_type', 'is_sent', 'report_date', 'restaurant']
    search_fields = ['restaurant__name', 'report_type']
    date_hierarchy = 'report_date'

    readonly_fields = [
        'restaurant',
        'report_date',
        'report_type',
        'data_formatted',
        'generated_at',
        'is_sent',
        'sent_at'
    ]

    fieldsets = (
        ('Report Information', {
            'fields': ('restaurant', 'report_date', 'report_type')
        }),
        ('Report Data', {
            'fields': ('data_formatted',),
            'classes': ('collapse',)
        }),
        ('Delivery Status', {
            'fields': ('is_sent', 'sent_at', 'generated_at')
        }),
    )

    actions = ['mark_as_sent', 'mark_as_unsent']

    # Custom display methods
    def restaurant_display(self, obj):
        return obj.restaurant.name
    restaurant_display.short_description = 'Restaurant'

    def report_type_badge(self, obj):
        color_map = {
            'sales': 'green',
            'inventory': 'orange',
            'staff': 'blue',
            'customers': 'purple'
        }

        color = color_map.get(obj.report_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 10px;">{}</span>',
            color, obj.get_report_type_display()
        )
    report_type_badge.short_description = 'Type'

    def data_preview(self, obj):
        import json
        data_str = json.dumps(obj.data)
        if len(data_str) > 50:
            return data_str[:50] + '...'
        return data_str
    data_preview.short_description = 'Data'

    def generated_at_time(self, obj):
        return obj.generated_at.strftime('%Y-%m-%d %H:%M')
    generated_at_time.short_description = 'Generated'

    def sent_status(self, obj):
        if obj.is_sent:
            sent_time = obj.sent_at.strftime(
                '%Y-%m-%d %H:%M') if obj.sent_at else "Unknown"
            return format_html(
                '<span style="color: green;">✓ Sent at {}</span>', sent_time
            )
        return format_html('<span style="color: orange;">✗ Not Sent</span>')
    sent_status.short_description = 'Status'

    def data_formatted(self, obj):
        """Display JSON data in formatted way"""
        import json
        formatted = json.dumps(obj.data, indent=2, ensure_ascii=False)
        return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>', formatted)
    data_formatted.short_description = 'Data (Formatted)'

    # Custom actions
    def mark_as_sent(self, request, queryset):
        updated = queryset.update(is_sent=True, sent_at=timezone.now())
        self.message_user(request, f"Marked {updated} reports as sent.")
    mark_as_sent.short_description = "Mark as sent"

    def mark_as_unsent(self, request, queryset):
        updated = queryset.update(is_sent=False, sent_at=None)
        self.message_user(request, f"Marked {updated} reports as unsent.")
    mark_as_unsent.short_description = "Mark as unsent"
