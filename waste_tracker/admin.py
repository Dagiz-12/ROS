# waste_tracker/admin.py - COMPLETE FIXED VERSION
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django import forms
from decimal import Decimal
from .models import WasteCategory, WasteReason, WasteRecord, WasteTarget, WasteAlert


class WasteCategoryAdminForm(forms.ModelForm):
    """Form for WasteCategory with custom widgets"""
    class Meta:
        model = WasteCategory
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'color_code': forms.TextInput(attrs={'type': 'color'}),
        }


class WasteCategoryAdmin(admin.ModelAdmin):
    form = WasteCategoryAdminForm
    list_display = ['name', 'category_type', 'restaurant',
                    'is_active', 'requires_approval', 'waste_count_display',
                    'total_cost_safe_display']
    list_filter = ['category_type', 'is_active', 'restaurant']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'requires_approval']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category_type', 'description', 'color_code', 'sort_order')
        }),
        ('Restaurant', {
            'fields': ('restaurant',)
        }),
        ('Settings', {
            'fields': ('is_active', 'requires_approval')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def waste_count_display(self, obj):
        """Display count of waste records for this category"""
        count = WasteRecord.objects.filter(
            waste_reason__category=obj,
            status='approved'
        ).count()
        return format_html('<span class="badge">{}</span>', count)
    waste_count_display.short_description = 'Waste Count'

    # In waste_tracker/admin.py - FIX THE total_cost_safe_display method:

    def total_cost_safe_display(self, obj):
        """Safely display total waste cost for this category"""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=30)

        # Get waste records and calculate cost through stock_transaction
        waste_records = WasteRecord.objects.filter(
            waste_reason__category=obj,
            recorded_at__gte=cutoff_date,
            status='approved'
        ).select_related('stock_transaction')

        total_cost = Decimal('0.00')
        for record in waste_records:
            if record.stock_transaction:
                total_cost += record.stock_transaction.total_cost

        if total_cost > 100:
            color = '#dc2626'  # Red
            weight = 'bold'
        elif total_cost > 50:
            color = '#f97316'  # Orange
            weight = 'bold'
        elif total_cost > 0:
            color = '#16a34a'  # Green
            weight = 'normal'
        else:
            color = '#6b7280'  # Gray
            weight = 'normal'

        # FIX: Properly format the Decimal value
        formatted_cost = "{:.2f}".format(total_cost)

        return format_html(
            '<span style="color: {}; font-weight: {};">${}</span>',
            color, weight, formatted_cost  # Pass formatted string
        )

    total_cost_safe_display.short_description = '30-Day Cost'


class WasteReasonAdminForm(forms.ModelForm):
    """Form for WasteReason with custom widgets"""
    class Meta:
        model = WasteReason
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'alert_threshold_daily': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'alert_threshold_weekly': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


class WasteReasonAdmin(admin.ModelAdmin):
    form = WasteReasonAdminForm
    list_display = ['name', 'category_link', 'controllability',
                    'requires_explanation', 'requires_photo', 'is_active',
                    'record_count_display']
    list_filter = ['category', 'controllability', 'is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'requires_explanation', 'requires_photo']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'controllability')
        }),
        ('Requirements', {
            'fields': ('requires_explanation', 'requires_photo')
        }),
        ('Alert Thresholds', {
            'fields': ('alert_threshold_daily', 'alert_threshold_weekly'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def category_link(self, obj):
        """Display category as clickable link"""
        if obj.category:
            url = reverse('admin:waste_tracker_wastecategory_change', args=[
                          obj.category.id])
            return format_html('<a href="{}">{}</a>', url, obj.category.name)
        return 'No Category'
    category_link.short_description = 'Category'

    def record_count_display(self, obj):
        """Display count of waste records for this reason"""
        count = WasteRecord.objects.filter(waste_reason=obj).count()
        return format_html('<span class="badge">{}</span>', count)
    record_count_display.short_description = 'Records'


class WasteRecordAdminForm(forms.ModelForm):
    """Form for WasteRecord with custom widgets"""
    class Meta:
        model = WasteRecord
        fields = '__all__'
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'corrective_action': forms.Textarea(attrs={'rows': 3}),
            'recorded_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'reviewed_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'corrected_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'waste_occurred_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'followup_date': forms.DateInput(attrs={'type': 'date'}),
        }


class WasteRecordAdmin(admin.ModelAdmin):
    form = WasteRecordAdminForm
    list_display = ['created_at', 'status_badge', 'stock_item_name',
                    'waste_reason_link', 'recorded_by_link', 'cost_display',
                    'branch', 'priority_badge']
    list_filter = ['status', 'priority', 'branch',
                   'waste_reason__category', 'created_at']
    search_fields = ['notes', 'batch_number', 'waste_reason__name']
    readonly_fields = ['waste_id', 'created_at',
                       'updated_at', 'cost_display_field']
    list_per_page = 50

    fieldsets = (
        ('Waste Details', {
            'fields': ('stock_transaction', 'waste_reason', 'waste_source')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('People Involved', {
            'fields': ('recorded_by', 'reviewed_by')
        }),
        ('Location & Context', {
            'fields': ('branch', 'station', 'shift')
        }),
        ('Additional Details', {
            'fields': ('notes', 'corrective_action', 'photo')
        }),
        ('Tracking Information', {
            'fields': ('batch_number', 'expiry_date'),
            'classes': ('collapse',)
        }),
        ('Recurring Issue Tracking', {
            'fields': ('is_recurring_issue', 'recurrence_id', 'requires_followup', 'followup_date'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('recorded_at', 'reviewed_at', 'corrected_at', 'waste_occurred_at')
        }),
        ('System Fields', {
            'fields': ('waste_id', 'created_at', 'updated_at', 'cost_display_field'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display status with color-coded badge"""
        colors = {
            'pending': 'bg-yellow-100 text-yellow-800',
            'approved': 'bg-green-100 text-green-800',
            'rejected': 'bg-red-100 text-red-800',
            'investigating': 'bg-blue-100 text-blue-800',
        }
        color_class = colors.get(obj.status, 'bg-gray-100 text-gray-800')

        status_display = dict(WasteRecord.WASTE_STATUS_CHOICES).get(
            obj.status, obj.status)
        return format_html(
            '<span class="px-2 py-1 text-xs font-medium rounded-full {}">{}</span>',
            color_class, status_display
        )
    status_badge.short_description = 'Status'

    def priority_badge(self, obj):
        """Display priority with color-coded badge"""
        colors = {
            'low': 'bg-gray-100 text-gray-800',
            'medium': 'bg-blue-100 text-blue-800',
            'high': 'bg-orange-100 text-orange-800',
            'critical': 'bg-red-100 text-red-800',
        }
        color_class = colors.get(obj.priority, 'bg-gray-100 text-gray-800')

        return format_html(
            '<span class="px-2 py-1 text-xs font-medium rounded-full {}">{}</span>',
            color_class, obj.priority.title()
        )
    priority_badge.short_description = 'Priority'

    def stock_item_name(self, obj):
        """Display stock item name safely"""
        if obj.stock_item:
            url = reverse('admin:inventory_stockitem_change',
                          args=[obj.stock_item.id])
            return format_html('<a href="{}">{}</a>', url, obj.stock_item.name)
        elif obj.stock_transaction and obj.stock_transaction.stock_item:
            url = reverse('admin:inventory_stockitem_change', args=[
                          obj.stock_transaction.stock_item.id])
            return format_html('<a href="{}">{}</a>', url, obj.stock_transaction.stock_item.name)
        return 'Unknown Item'
    stock_item_name.short_description = 'Item'

    def waste_reason_link(self, obj):
        """Display waste reason as clickable link"""
        if obj.waste_reason:
            url = reverse('admin:waste_tracker_wastereason_change',
                          args=[obj.waste_reason.id])
            return format_html('<a href="{}">{}</a>', url, obj.waste_reason.name)
        return 'No Reason'
    waste_reason_link.short_description = 'Reason'

    def recorded_by_link(self, obj):
        """Display recorded by user as clickable link"""
        if obj.recorded_by:
            url = reverse('admin:accounts_customuser_change',
                          args=[obj.recorded_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.recorded_by.username)
        return 'Unknown'
    recorded_by_link.short_description = 'Recorded By'

    def cost_display(self, obj):
        """Display cost safely"""
        cost = obj.total_cost  # This uses the property in the model
        if cost > 100:
            color = '#dc2626'
            weight = 'bold'
        elif cost > 50:
            color = '#f97316'
            weight = 'bold'
        elif cost > 0:
            color = '#16a34a'
            weight = 'normal'
        else:
            color = '#6b7280'
            weight = 'normal'

        return format_html(
            '<span style="color: {}; font-weight: {};">${:.2f}</span>',
            color, weight, cost
        )
    cost_display.short_description = 'Cost'

    def cost_display_field(self, obj):
        """Read-only field for cost display"""
        return self.cost_display(obj)
    cost_display_field.short_description = 'Total Cost'


class WasteTargetAdminForm(forms.ModelForm):
    """Form for WasteTarget with custom widgets"""
    class Meta:
        model = WasteTarget
        fields = '__all__'
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'target_value': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


class WasteTargetAdmin(admin.ModelAdmin):
    form = WasteTargetAdminForm
    list_display = ['name', 'restaurant', 'branch', 'target_type',
                    'target_value_display', 'current_value_display',
                    'progress_display', 'period', 'is_active']
    list_filter = ['target_type', 'period',
                   'is_active', 'restaurant', 'branch']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    readonly_fields = ['current_value',
                       'last_updated', 'created_at', 'updated_at']
    filter_horizontal = ['waste_categories']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'restaurant', 'branch')
        }),
        ('Target Details', {
            'fields': ('target_type', 'target_value', 'period', 'waste_categories')
        }),
        ('Date Range', {
            'fields': ('start_date', 'end_date')
        }),
        ('Current Status', {
            'fields': ('current_value', 'last_updated')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def target_value_display(self, obj):
        """Display target value with currency/percentage"""
        if obj.target_type == 'cost':
            return f"${obj.target_value:.2f}"
        elif obj.target_type == 'percentage':
            return f"{obj.target_value:.1f}%"
        else:
            return f"{obj.target_value}"
    target_value_display.short_description = 'Target'

    def current_value_display(self, obj):
        """Display current value"""
        if obj.target_type == 'cost':
            return f"${obj.current_value:.2f}"
        elif obj.target_type == 'percentage':
            return f"{obj.current_value:.1f}%"
        else:
            return f"{obj.current_value}"
    current_value_display.short_description = 'Current'

    def progress_display(self, obj):
        """Display progress bar"""
        if obj.target_value > 0:
            percentage = min(100, (obj.current_value / obj.target_value) * 100)
        else:
            percentage = 0

        if percentage >= 100:
            color = 'bg-red-500'
            text_color = 'text-red-700'
        elif percentage >= 80:
            color = 'bg-orange-500'
            text_color = 'text-orange-700'
        elif percentage >= 60:
            color = 'bg-yellow-500'
            text_color = 'text-yellow-700'
        else:
            color = 'bg-green-500'
            text_color = 'text-green-700'

        return format_html(
            '<div class="w-full bg-gray-200 rounded-full h-2.5">'
            '<div class="{} h-2.5 rounded-full" style="width: {}%"></div>'
            '</div><div class="text-xs {} mt-1">{:.1f}%</div>',
            color, percentage, text_color, percentage
        )
    progress_display.short_description = 'Progress'


class WasteAlertAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'alert_type_badge', 'title_short',
                    'branch', 'is_read_display', 'is_resolved_display']
    list_filter = ['alert_type', 'is_read',
                   'is_resolved', 'branch', 'created_at']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at', 'resolved_at']
    list_per_page = 50

    fieldsets = (
        ('Alert Details', {
            'fields': ('alert_type', 'title', 'message')
        }),
        ('Related Items', {
            'fields': ('waste_record', 'waste_reason', 'branch')
        }),
        ('Status', {
            'fields': ('is_read', 'is_resolved', 'resolved_by', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    def alert_type_badge(self, obj):
        """Display alert type with badge"""
        colors = {
            'threshold_exceeded': 'bg-red-100 text-red-800',
            'recurring_issue': 'bg-orange-100 text-orange-800',
            'approval_needed': 'bg-blue-100 text-blue-800',
            'target_at_risk': 'bg-yellow-100 text-yellow-800',
        }
        color_class = colors.get(obj.alert_type, 'bg-gray-100 text-gray-800')

        alert_type_display = dict(WasteAlert.ALERT_TYPES).get(
            obj.alert_type, obj.alert_type)
        return format_html(
            '<span class="px-2 py-1 text-xs font-medium rounded-full {}">{}</span>',
            color_class, alert_type_display
        )
    alert_type_badge.short_description = 'Type'

    def title_short(self, obj):
        """Shorten long titles"""
        if len(obj.title) > 50:
            return f"{obj.title[:47]}..."
        return obj.title
    title_short.short_description = 'Title'

    def is_read_display(self, obj):
        """Display read status"""
        if obj.is_read:
            return format_html('<span class="text-green-600">✓ Read</span>')
        return format_html('<span class="text-red-600">● Unread</span>')
    is_read_display.short_description = 'Read'

    def is_resolved_display(self, obj):
        """Display resolved status"""
        if obj.is_resolved:
            return format_html('<span class="text-green-600">✓ Resolved</span>')
        return format_html('<span class="text-red-600">● Active</span>')
    is_resolved_display.short_description = 'Resolved'


# Register all models
admin.site.register(WasteCategory, WasteCategoryAdmin)
admin.site.register(WasteReason, WasteReasonAdmin)
admin.site.register(WasteRecord, WasteRecordAdmin)
admin.site.register(WasteTarget, WasteTargetAdmin)
admin.site.register(WasteAlert, WasteAlertAdmin)
