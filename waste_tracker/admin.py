# waste_tracker/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import WasteCategory, WasteReason, WasteRecord, WasteTarget, WasteAlert


class WasteCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'restaurant', 'is_active',
                    'requires_approval', 'waste_count_display', 'total_cost_display')
    list_filter = ('category_type', 'is_active',
                   'requires_approval', 'restaurant')
    search_fields = ('name', 'description')
    list_per_page = 20
    ordering = ('sort_order', 'name')

    def waste_count_display(self, obj):
        count = obj.reasons.aggregate(
            count=models.Count('records'))['count'] or 0
        color = 'red' if count > 10 else 'orange' if count > 5 else 'green'
        return format_html('<span style="color: {};">{}</span>', color, count)
    waste_count_display.short_description = 'Waste Count'

    def total_cost_display(self, obj):
        total = obj.total_waste_cost(days=30)
        return format_html('<strong>${:,.2f}</strong>', total)
    total_cost_display.short_description = '30-Day Cost'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category_type', 'description', 'restaurant')
        }),
        ('Display Settings', {
            'fields': ('color_code', 'sort_order')
        }),
        ('Workflow Settings', {
            'fields': ('requires_approval', 'is_active')
        }),
    )


class WasteReasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'controllability', 'is_active',
                    'alert_threshold_daily', 'requires_explanation', 'requires_photo')
    list_filter = ('category', 'controllability', 'is_active',
                   'requires_explanation', 'requires_photo')
    search_fields = ('name', 'description')
    list_per_page = 20

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'controllability')
        }),
        ('Requirements', {
            'fields': ('requires_explanation', 'requires_photo')
        }),
        ('Alert Thresholds', {
            'fields': ('alert_threshold_daily', 'alert_threshold_weekly'),
            'description': 'Set thresholds for automatic alerts'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


class WasteRecordAdmin(admin.ModelAdmin):
    list_display = ('display_id', 'stock_item_display', 'quantity_display', 'total_cost_display',
                    'waste_reason', 'status_badge', 'recorded_by', 'branch', 'created_at')
    list_filter = ('status', 'priority', 'branch',
                   'waste_reason__category', 'created_at', 'station')
    search_fields = ('notes', 'batch_number',
                     'stock_transaction__stock_item__name')
    list_per_page = 25
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at',
                       'reviewed_at', 'total_cost', 'waste_id')

    def display_id(self, obj):
        return format_html('<code>{}</code>', obj.waste_id)
    display_id.short_description = 'Waste ID'

    def stock_item_display(self, obj):
        if obj.stock_transaction and obj.stock_transaction.stock_item:
            url = reverse('admin:inventory_stockitem_change', args=[
                          obj.stock_transaction.stock_item.id])
            return format_html('<a href="{}">{}</a>', url, obj.stock_transaction.stock_item.name)
        return 'N/A'
    stock_item_display.short_description = 'Stock Item'

    def quantity_display(self, obj):
        if obj.stock_transaction:
            return f"{obj.stock_transaction.quantity} {obj.stock_transaction.stock_item.unit}"
        return 'N/A'
    quantity_display.short_description = 'Quantity'

    def total_cost_display(self, obj):
        if obj.stock_transaction:
            color = 'red' if obj.stock_transaction.total_cost > 50 else 'orange' if obj.stock_transaction.total_cost > 20 else 'green'
            return format_html('<strong style="color: {};">${:,.2f}</strong>', color, obj.stock_transaction.total_cost)
        return '$0.00'
    total_cost_display.short_description = 'Cost'

    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'investigating': 'info',
            'requires_correction': 'secondary'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    fieldsets = (
        ('Identification', {
            'fields': ('waste_id', 'waste_reason', 'priority', 'status')
        }),
        ('Item Details', {
            'fields': ('stock_transaction', 'batch_number', 'expiry_date')
        }),
        ('Location & Context', {
            'fields': ('branch', 'station', 'shift', 'waste_source')
        }),
        ('People Involved', {
            'fields': ('recorded_by', 'reviewed_by', 'corrected_by')
        }),
        ('Evidence & Documentation', {
            'fields': ('notes', 'corrective_action', 'photo')
        }),
        ('System Information', {
            'fields': ('is_recurring_issue', 'requires_followup', 'followup_date', 'inventory_adjusted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'recorded_at', 'reviewed_at', 'corrected_at', 'waste_occurred_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_selected', 'reject_selected', 'mark_as_investigating']

    def approve_selected(self, request, queryset):
        updated = queryset.update(
            status='approved', reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f'{updated} waste records approved.')
    approve_selected.short_description = 'Approve selected waste records'

    def reject_selected(self, request, queryset):
        updated = queryset.update(
            status='rejected', reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f'{updated} waste records rejected.')
    reject_selected.short_description = 'Reject selected waste records'

    def mark_as_investigating(self, request, queryset):
        updated = queryset.update(status='investigating')
        self.message_user(
            request, f'{updated} waste records marked for investigation.')
    mark_as_investigating.short_description = 'Mark selected for investigation'


class WasteTargetAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'branch', 'target_type', 'target_value',
                    'current_value', 'progress_bar', 'is_active', 'days_remaining')
    list_filter = ('target_type', 'period',
                   'is_active', 'restaurant', 'branch')
    search_fields = ('name', 'description')
    list_per_page = 20

    def progress_bar(self, obj):
        progress = obj.progress_percentage
        color = 'success' if progress <= 100 else 'warning' if progress <= 150 else 'danger'
        width = min(progress, 100)
        return format_html(
            '<div class="progress" style="height: 20px; width: 100px;">'
            '<div class="progress-bar bg-{}" style="width: {}%">{:.1f}%</div>'
            '</div>',
            color, width, progress
        )
    progress_bar.short_description = 'Progress'

    def days_remaining(self, obj):
        if obj.end_date and obj.is_active:
            days = (obj.end_date - timezone.now().date()).days
            color = 'red' if days < 7 else 'orange' if days < 30 else 'green'
            return format_html('<span style="color: {};">{} days</span>', color, days)
        return 'N/A'
    days_remaining.short_description = 'Days Remaining'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'restaurant', 'branch')
        }),
        ('Target Metrics', {
            'fields': ('target_type', 'target_value', 'period', 'waste_categories')
        }),
        ('Date Range', {
            'fields': ('start_date', 'end_date')
        }),
        ('Progress Tracking', {
            'fields': ('current_value',),
            'description': 'Current value is calculated automatically'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # New target
            obj.restaurant = request.user.restaurant
        super().save_model(request, obj, form, change)


class WasteAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'alert_type_badge', 'branch',
                    'is_resolved', 'is_read', 'created_at', 'resolved_by')
    list_filter = ('alert_type', 'is_resolved',
                   'is_read', 'branch', 'created_at')
    search_fields = ('title', 'message', 'resolution_notes')
    list_per_page = 25
    readonly_fields = ('created_at', 'resolved_at')

    def alert_type_badge(self, obj):
        colors = {
            'threshold_exceeded': 'danger',
            'recurring_issue': 'warning',
            'approval_needed': 'info',
            'target_at_risk': 'secondary',
            'unusual_pattern': 'primary'
        }
        color = colors.get(obj.alert_type, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_alert_type_display()
        )
    alert_type_badge.short_description = 'Type'

    fieldsets = (
        ('Alert Details', {
            'fields': ('alert_type', 'title', 'message', 'triggered_by')
        }),
        ('Related Objects', {
            'fields': ('waste_record', 'waste_reason', 'branch')
        }),
        ('Resolution', {
            'fields': ('is_resolved', 'resolved_by', 'resolved_at', 'resolution_notes')
        }),
        ('Read Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_resolved', 'mark_as_read', 'mark_as_unread']

    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(
            is_resolved=True, resolved_by=request.user, resolved_at=timezone.now())
        self.message_user(request, f'{updated} alerts marked as resolved.')
    mark_as_resolved.short_description = 'Mark selected alerts as resolved'

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} alerts marked as read.')
    mark_as_read.short_description = 'Mark selected alerts as read'

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} alerts marked as unread.')
    mark_as_unread.short_description = 'Mark selected alerts as unread'


# Register models
admin.site.register(WasteCategory, WasteCategoryAdmin)
admin.site.register(WasteReason, WasteReasonAdmin)
admin.site.register(WasteRecord, WasteRecordAdmin)
admin.site.register(WasteTarget, WasteTargetAdmin)
admin.site.register(WasteAlert, WasteAlertAdmin)
