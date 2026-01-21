# profit_intelligence/admin.py - CORRECTED VERSION
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ProfitAggregation, MenuItemPerformance,
    ProfitAlert, PriceOptimization, ProfitReport
)


@admin.register(ProfitAggregation)
class ProfitAggregationAdmin(admin.ModelAdmin):
    list_display = ('date', 'restaurant', 'branch', 'revenue',
                    'net_profit', 'profit_margin_display')
    list_filter = ('date', 'restaurant', 'branch', 'level')
    search_fields = ('restaurant__name', 'branch__name')
    readonly_fields = ('calculated_at', 'created_at')

    def profit_margin_display(self, obj):
        """Display profit margin with color coding"""
        # Ensure we have a float value
        try:
            margin = float(obj.profit_margin)
        except (TypeError, ValueError):
            margin = 0.0

        if margin >= 40:
            color = 'green'
        elif margin >= 20:
            color = 'blue'
        elif margin >= 10:
            color = 'orange'
        elif margin > 0:
            color = 'red'
        else:
            color = 'darkred'

        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, margin
        )
    profit_margin_display.short_description = 'Margin'


@admin.register(MenuItemPerformance)
class MenuItemPerformanceAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'date', 'quantity_sold',
                    'revenue_display', 'profit_margin_display', 'status_badge')
    list_filter = ('date', 'restaurant', 'branch', 'menu_item__category')
    search_fields = ('menu_item__name',)
    readonly_fields = ('calculated_at', 'created_at')

    def revenue_display(self, obj):
        """Display revenue formatted"""
        try:
            revenue = float(obj.revenue)
            return f"${revenue:.2f}"
        except (TypeError, ValueError):
            return "$0.00"
    revenue_display.short_description = 'Revenue'

    def profit_margin_display(self, obj):
        """Display profit margin with color coding"""
        # Ensure we have a float value
        try:
            margin = float(obj.profit_margin)
        except (TypeError, ValueError):
            margin = 0.0

        if margin >= 40:
            color = 'green'
        elif margin >= 20:
            color = 'blue'
        elif margin >= 10:
            color = 'orange'
        elif margin > 0:
            color = 'red'
        else:
            color = 'darkred'

        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, margin
        )
    profit_margin_display.short_description = 'Margin'

    def status_badge(self, obj):
        """Display performance status badge"""
        try:
            margin = float(obj.profit_margin)
        except (TypeError, ValueError):
            margin = 0.0

        if margin >= 40:
            color = 'green'
            text = 'High Profit'
        elif margin >= 20:
            color = 'blue'
            text = 'Good Profit'
        elif margin >= 10:
            color = 'orange'
            text = 'Low Profit'
        elif margin > 0:
            color = 'red'
            text = 'Problem'
        else:
            color = 'darkred'
            text = 'Loss Maker'

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            color, text
        )
    status_badge.short_description = 'Status'


@admin.register(ProfitAlert)
class ProfitAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'alert_type', 'severity_badge',
                    'is_resolved', 'created_at')
    list_filter = ('alert_type', 'severity', 'is_resolved', 'created_at')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at', 'updated_at')

    def severity_badge(self, obj):
        """Display severity with color-coded badge"""
        color_map = {
            'critical': 'darkred',
            'high': 'red',
            'medium': 'orange',
            'low': 'blue',
            'info': 'gray'
        }

        color = color_map.get(obj.severity, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            color, obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'


@admin.register(PriceOptimization)
class PriceOptimizationAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'status_badge', 'current_price_display',
                    'suggested_price_display', 'confidence_score_display')
    list_filter = ('status', 'restaurant')
    search_fields = ('menu_item__name', 'reason')
    readonly_fields = ('created_at', 'updated_at')

    def current_price_display(self, obj):
        """Display current price formatted"""
        try:
            price = float(obj.current_price)
            return f"${price:.2f}"
        except (TypeError, ValueError):
            return "$0.00"
    current_price_display.short_description = 'Current Price'

    def suggested_price_display(self, obj):
        """Display suggested price formatted"""
        try:
            price = float(obj.suggested_price)
            return f"${price:.2f}"
        except (TypeError, ValueError):
            return "$0.00"
    suggested_price_display.short_description = 'Suggested Price'

    def status_badge(self, obj):
        """Display status with badge"""
        color_map = {
            'pending': 'gray',
            'approved': 'blue',
            'rejected': 'red',
            'implemented': 'green',
            'expired': 'orange'
        }

        color = color_map.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def confidence_score_display(self, obj):
        """Display confidence score with color"""
        try:
            score = float(obj.confidence_score)
        except (TypeError, ValueError):
            score = 0.0

        if score >= 0.8:
            color = 'green'
        elif score >= 0.6:
            color = 'blue'
        elif score >= 0.4:
            color = 'orange'
        else:
            color = 'red'

        return format_html(
            '<span style="color: {};">{:.1f}</span>',
            color, score
        )
    confidence_score_display.short_description = 'Confidence'


@admin.register(ProfitReport)
class ProfitReportAdmin(admin.ModelAdmin):
    list_display = ('date', 'restaurant', 'branch',
                    'report_type', 'generated_at')
    list_filter = ('report_type', 'date', 'restaurant')
    readonly_fields = ('generated_at',)
