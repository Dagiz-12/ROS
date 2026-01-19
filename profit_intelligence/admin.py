# profit_intelligence/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import ProfitAggregation, MenuItemPerformance, ProfitAlert, PriceOptimization


@admin.register(ProfitAggregation)
class ProfitAggregationAdmin(admin.ModelAdmin):
    list_display = ('date', 'restaurant', 'branch', 'revenue',
                    'net_profit', 'profit_margin')
    list_filter = ('date', 'restaurant', 'branch')
    search_fields = ('restaurant__name', 'branch__name')
    readonly_fields = ('calculated_at', 'created_at')
    ordering = ('-date',)

    def profit_margin_display(self, obj):
        color = 'green' if obj.profit_margin >= 20 else 'orange' if obj.profit_margin >= 10 else 'red'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, obj.profit_margin)
    profit_margin_display.short_description = 'Profit Margin'

    fieldsets = (
        ('Identification', {
            'fields': ('level', 'date', 'restaurant', 'branch')
        }),
        ('Financial Metrics', {
            'fields': ('revenue', 'cost_of_goods', 'waste_cost', 'gross_profit', 'net_profit', 'profit_margin')
        }),
        ('Operational Metrics', {
            'fields': ('order_count', 'average_order_value', 'waste_percentage')
        }),
        ('Status', {
            'fields': ('is_above_target', 'has_issues', 'data_quality_score')
        }),
        ('Timestamps', {
            'fields': ('calculated_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MenuItemPerformance)
class MenuItemPerformanceAdmin(admin.ModelAdmin):
    list_display = ('date', 'menu_item', 'quantity_sold',
                    'revenue', 'net_profit', 'margin_display')
    list_filter = ('date', 'restaurant', 'branch')
    search_fields = ('menu_item__name',)
    readonly_fields = ('calculated_at', 'created_at')
    ordering = ('-date',)

    def margin_display(self, obj):
        color = 'green' if obj.profit_margin >= 40 else 'orange' if obj.profit_margin >= 20 else 'red'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, obj.profit_margin)
    margin_display.short_description = 'Margin'


@admin.register(ProfitAlert)
class ProfitAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'alert_type', 'severity_display',
                    'menu_item', 'is_resolved', 'created_at')
    list_filter = ('alert_type', 'severity', 'is_resolved',
                   'restaurant', 'branch', 'created_at')
    search_fields = ('title', 'message', 'menu_item__name')
    readonly_fields = ('created_at', 'updated_at',
                       'resolved_at', 'acknowledged_at')
    actions = ['mark_as_resolved', 'mark_as_acknowledged']

    def severity_display(self, obj):
        colors = {
            'critical': 'red',
            'high': 'orange',
            'medium': 'yellow',
            'low': 'blue',
            'info': 'gray'
        }
        color = colors.get(obj.severity, 'gray')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_severity_display())
    severity_display.short_description = 'Severity'

    def mark_as_resolved(self, request, queryset):
        for alert in queryset:
            alert.resolve(request.user)
        self.message_user(
            request, f"{queryset.count()} alerts marked as resolved.")
    mark_as_resolved.short_description = "Mark selected alerts as resolved"

    def mark_as_acknowledged(self, request, queryset):
        for alert in queryset:
            alert.acknowledge(request.user)
        self.message_user(
            request, f"{queryset.count()} alerts marked as acknowledged.")
    mark_as_acknowledged.short_description = "Mark selected alerts as acknowledged"


@admin.register(PriceOptimization)
class PriceOptimizationAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'current_price', 'suggested_price',
                    'price_change_percent', 'confidence_score', 'status')
    list_filter = ('status', 'restaurant', 'created_at')
    search_fields = ('menu_item__name', 'reason')
    readonly_fields = ('created_at', 'updated_at', 'applied_at')
    actions = ['approve_optimization', 'reject_optimization']

    def price_change_percent(self, obj):
        color = 'green' if obj.price_change_percent > 0 else 'red'
        symbol = '+' if obj.price_change_percent > 0 else ''
        return format_html('<span style="color: {};">{}{:.1f}%</span>', color, symbol, obj.price_change_percent)
    price_change_percent.short_description = 'Price Change'

    def approve_optimization(self, request, queryset):
        for optimization in queryset:
            optimization.status = 'approved'
            optimization.save()
        self.message_user(
            request, f"{queryset.count()} optimizations approved.")
    approve_optimization.short_description = "Approve selected optimizations"

    def reject_optimization(self, request, queryset):
        for optimization in queryset:
            optimization.status = 'rejected'
            optimization.save()
        self.message_user(
            request, f"{queryset.count()} optimizations rejected.")
    reject_optimization.short_description = "Reject selected optimizations"
