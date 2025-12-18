# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import AuditLog, SystemSetting
import json


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model"""
    list_display = [
        'action_badge',
        'user_display',
        'model_name',
        'object_id_display',
        'ip_address',
        'created_at_time'
    ]

    list_filter = ['action', 'model_name', 'created_at']
    search_fields = [
        'user__username',
        'user__email',
        'model_name',
        'object_id',
        'details'
    ]

    readonly_fields = [
        'user',
        'action',
        'model_name',
        'object_id',
        'details_formatted',
        'ip_address',
        'user_agent',
        'created_at'
    ]

    fieldsets = (
        ('Action Details', {
            'fields': ('user', 'action', 'model_name', 'object_id')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Data Details', {
            'fields': ('details_formatted',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['clear_old_logs']

    # Disable add permission
    def has_add_permission(self, request):
        return False

    # Disable change permission
    def has_change_permission(self, request, obj=None):
        return False

    # Custom display methods
    def action_badge(self, obj):
        color_map = {
            'CREATE': 'green',
            'UPDATE': 'blue',
            'DELETE': 'red',
            'LOGIN': 'purple',
            'LOGOUT': 'gray',
            'PAYMENT': 'orange',
            'ORDER': 'teal'
        }

        color = color_map.get(obj.action, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = 'Action'

    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.username} ({obj.user.role})"
        return "System"
    user_display.short_description = 'User'

    def object_id_display(self, obj):
        if obj.object_id:
            return format_html(
                '<code style="background-color: #f0f0f0; padding: 2px 5px;">{}</code>',
                obj.object_id
            )
        return "-"
    object_id_display.short_description = 'Object ID'

    def created_at_time(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_time.short_description = 'Timestamp'

    def details_formatted(self, obj):
        """Display JSON details in formatted way"""
        if obj.details:
            formatted = json.dumps(obj.details, indent=2, ensure_ascii=False)
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>', formatted)
        return "-"
    details_formatted.short_description = 'Details'

    # Custom action
    def clear_old_logs(self, request, queryset):
        """Clear logs older than 30 days"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=30)

        # Delete logs older than 30 days
        old_logs = AuditLog.objects.filter(created_at__lt=cutoff_date)
        count = old_logs.count()
        old_logs.delete()

        self.message_user(request, f"Deleted {count} logs older than 30 days.")
    clear_old_logs.short_description = "Clear logs older than 30 days"


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    """Admin interface for SystemSetting model"""
    list_display = [
        'key',
        'value_preview',
        'description_short',
        'is_active',
        'updated_at_time'
    ]

    list_filter = ['is_active']
    search_fields = ['key', 'description', 'value']
    list_editable = ['is_active']

    fieldsets = (
        ('Setting Information', {
            'fields': ('key', 'value_formatted', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['updated_at', 'value_formatted']

    actions = ['activate_settings', 'deactivate_settings']

    # Custom display methods
    def value_preview(self, obj):
        """Display a preview of the value"""
        value_str = str(obj.value)
        if len(value_str) > 50:
            return value_str[:50] + '...'
        return value_str
    value_preview.short_description = 'Value'

    def description_short(self, obj):
        """Display shortened description"""
        if obj.description:
            if len(obj.description) > 50:
                return obj.description[:50] + '...'
            return obj.description
        return "-"
    description_short.short_description = 'Description'

    def updated_at_time(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    updated_at_time.short_description = 'Last Updated'

    def value_formatted(self, obj):
        """Display JSON value in formatted way"""
        formatted = json.dumps(obj.value, indent=2, ensure_ascii=False)
        return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>', formatted)
    value_formatted.short_description = 'Value (Formatted)'

    # Custom actions
    def activate_settings(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} settings.")
    activate_settings.short_description = "Activate selected settings"

    def deactivate_settings(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} settings.")
    deactivate_settings.short_description = "Deactivate selected settings"

    # Custom save method
    def save_model(self, request, obj, form, change):
        # Ensure value is valid JSON
        if isinstance(obj.value, str):
            try:
                obj.value = json.loads(obj.value)
            except json.JSONDecodeError:
                pass  # Keep as string if not valid JSON
        super().save_model(request, obj, form, change)
