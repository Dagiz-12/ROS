from rest_framework import serializers
from .models import AuditLog, SystemSetting


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'username', 'user_role', 'action',
            'model_name', 'object_id', 'details', 'ip_address',
            'user_agent', 'created_at'
        ]
        read_only_fields = fields


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ['id', 'key', 'value',
                  'description', 'is_active', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    database = serializers.CharField()
    cache = serializers.CharField()
