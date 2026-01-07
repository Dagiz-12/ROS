# waste_tracker/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .models import WasteCategory, WasteReason, WasteRecord, WasteTarget, WasteAlert
from inventory.models import StockItem, StockTransaction
from restaurants.models import Restaurant, Branch

User = get_user_model()


class WasteCategorySerializer(serializers.ModelSerializer):
    """Serializer for waste categories"""

    restaurant_name = serializers.CharField(
        source='restaurant.name', read_only=True)
    waste_count = serializers.SerializerMethodField()
    total_waste_cost = serializers.SerializerMethodField()

    class Meta:
        model = WasteCategory
        fields = [
            'id', 'name', 'category_type', 'description', 'restaurant', 'restaurant_name',
            'color_code', 'sort_order', 'is_active', 'requires_approval',
            'waste_count', 'total_waste_cost', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_waste_count(self, obj):
        """Get count of waste records in this category (last 30 days)"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return obj.reasons.filter(
            records__status='approved',
            records__created_at__gte=thirty_days_ago
        ).count()

    def get_total_waste_cost(self, obj):
        """Get total waste cost for this category (last 30 days)"""
        return obj.total_waste_cost(days=30)


class WasteReasonSerializer(serializers.ModelSerializer):
    """Serializer for waste reasons"""

    category_name = serializers.CharField(
        source='category.name', read_only=True)
    category_type = serializers.CharField(
        source='category.category_type', read_only=True)
    record_count = serializers.SerializerMethodField()

    class Meta:
        model = WasteReason
        fields = [
            'id', 'name', 'description', 'category', 'category_name', 'category_type',
            'controllability', 'requires_explanation', 'requires_photo', 'is_active',
            'alert_threshold_daily', 'alert_threshold_weekly', 'record_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_record_count(self, obj):
        """Get count of waste records with this reason (last 30 days)"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return obj.records.filter(
            status='approved',
            created_at__gte=thirty_days_ago
        ).count()


class StockItemSimpleSerializer(serializers.ModelSerializer):
    """Simplified serializer for stock items in waste records"""

    class Meta:
        model = StockItem
        fields = ['id', 'name', 'unit', 'category', 'cost_per_unit']


class WasteRecordSerializer(serializers.ModelSerializer):
    """Serializer for waste records with detailed information"""

    # Related object details
    waste_reason_details = WasteReasonSerializer(
        source='waste_reason', read_only=True)
    recorded_by_details = serializers.SerializerMethodField()
    reviewed_by_details = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    # Stock transaction details
    stock_item_details = serializers.SerializerMethodField()
    stock_item_id = serializers.PrimaryKeyRelatedField(
        queryset=StockItem.objects.all(),
        write_only=True,
        source='_stock_item'  # Custom source for temporary storage
    )
    quantity = serializers.DecimalField(
        max_digits=10, decimal_places=3,
        write_only=True,
        source='_quantity'  # Custom source for temporary storage
    )

    # Calculated fields
    total_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    age_in_hours = serializers.FloatField(read_only=True)
    is_high_priority = serializers.BooleanField(read_only=True)

    class Meta:
        model = WasteRecord
        fields = [
            # Core fields
            'id', 'waste_reason', 'waste_reason_details', 'waste_source',
            'status', 'priority', 'notes', 'corrective_action',
            'photo', 'station', 'shift', 'batch_number', 'expiry_date',

            # Related objects
            'recorded_by', 'recorded_by_details', 'reviewed_by', 'reviewed_by_details',
            'branch', 'branch_name',

            # Stock information
            'stock_transaction', 'stock_item_details', 'stock_item_id', 'quantity',

            # Calculated fields
            'total_cost', 'age_in_hours', 'is_high_priority',
            'is_recurring_issue', 'requires_followup', 'followup_date',

            # Timestamps
            'recorded_at', 'reviewed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'stock_transaction', 'total_cost', 'age_in_hours', 'is_high_priority',
            'recorded_at', 'reviewed_at', 'created_at', 'updated_at'
        ]

    def get_recorded_by_details(self, obj):
        """Get simplified user details for recorded_by"""
        if obj.recorded_by:
            return {
                'id': obj.recorded_by.id,
                'username': obj.recorded_by.username,
                'full_name': obj.recorded_by.get_full_name(),
                'role': obj.recorded_by.role
            }
        return None

    def get_reviewed_by_details(self, obj):
        """Get simplified user details for reviewed_by"""
        if obj.reviewed_by:
            return {
                'id': obj.reviewed_by.id,
                'username': obj.reviewed_by.username,
                'full_name': obj.reviewed_by.get_full_name(),
                'role': obj.reviewed_by.role
            }
        return None

    def get_stock_item_details(self, obj):
        """Get stock item details from linked transaction"""
        if obj.stock_transaction and obj.stock_transaction.stock_item:
            return StockItemSimpleSerializer(obj.stock_transaction.stock_item).data
        return None

    def create(self, validated_data):
        """Create waste record with linked stock transaction"""
        # Extract temporary fields
        stock_item = validated_data.pop('_stock_item', None)
        quantity = validated_data.pop('_quantity', None)

        # Create the waste record
        waste_record = WasteRecord.objects.create(**validated_data)

        # Store stock item and quantity for auto-creation in save()
        if stock_item and quantity:
            waste_record._stock_item = stock_item
            waste_record._quantity = quantity

        waste_record.save()
        return waste_record

    def validate(self, data):
        """Validate waste record data"""
        # Check if explanation is required but not provided
        waste_reason = data.get('waste_reason')
        if waste_reason and waste_reason.requires_explanation:
            if not data.get('notes') or len(data.get('notes', '').strip()) < 10:
                raise serializers.ValidationError(
                    "Explanation is required for this waste reason. Please provide detailed notes."
                )

        # Check if photo is required but not provided
        if waste_reason and waste_reason.requires_photo:
            if not self.initial_data.get('photo'):
                raise serializers.ValidationError(
                    "Photo evidence is required for this waste reason."
                )

        return data


class WasteRecordCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating waste records (employee interface)"""

    stock_item_id = serializers.PrimaryKeyRelatedField(
        queryset=StockItem.objects.all(),
        source='_stock_item'
    )
    quantity = serializers.DecimalField(
        max_digits=10, decimal_places=3,
        source='_quantity'
    )
    unit = serializers.CharField(read_only=True, source='_stock_item.unit')

    class Meta:
        model = WasteRecord
        fields = [
            'waste_reason', 'stock_item_id', 'quantity', 'unit',
            'waste_source', 'station', 'shift', 'notes',
            'batch_number', 'expiry_date'
        ]

    def to_representation(self, instance):
        """Convert to representation with additional info"""
        rep = super().to_representation(instance)

        # Add stock item name for confirmation
        if instance.stock_transaction and instance.stock_transaction.stock_item:
            rep['stock_item_name'] = instance.stock_transaction.stock_item.name
            rep['unit_cost'] = instance.stock_transaction.stock_item.cost_per_unit
            rep['total_cost'] = instance.stock_transaction.total_cost

        return rep


class WasteTargetSerializer(serializers.ModelSerializer):
    """Serializer for waste reduction targets"""

    restaurant_name = serializers.CharField(
        source='restaurant.name', read_only=True)
    branch_name = serializers.CharField(
        source='branch.name', read_only=True, allow_null=True)
    progress_percentage = serializers.FloatField(read_only=True)
    is_on_track = serializers.BooleanField(read_only=True)
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = WasteTarget
        fields = [
            'id', 'name', 'restaurant', 'restaurant_name', 'branch', 'branch_name',
            'target_type', 'target_value', 'period', 'waste_categories',
            'start_date', 'end_date', 'is_active', 'current_value',
            'progress_percentage', 'is_on_track', 'days_remaining',
            'last_updated', 'created_at', 'updated_at'
        ]
        read_only_fields = ['current_value',
                            'last_updated', 'created_at', 'updated_at']

    def get_days_remaining(self, obj):
        """Calculate days remaining for active targets"""
        if obj.is_active and obj.end_date:
            from datetime import date
            today = date.today()
            if obj.end_date >= today:
                return (obj.end_date - today).days
        return 0

    def validate(self, data):
        """Validate target data"""
        # Ensure end_date is after start_date
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] <= data['start_date']:
                raise serializers.ValidationError(
                    "End date must be after start date."
                )

        # For percentage targets, ensure value is between 0 and 100
        if data.get('target_type') == 'percentage':
            if not (0 <= data.get('target_value', 0) <= 100):
                raise serializers.ValidationError(
                    "Percentage target must be between 0 and 100."
                )

        return data


class WasteAlertSerializer(serializers.ModelSerializer):
    """Serializer for waste alerts"""

    branch_name = serializers.CharField(source='branch.name', read_only=True)
    waste_record_id = serializers.PrimaryKeyRelatedField(
        source='waste_record',
        queryset=WasteRecord.objects.all(),
        allow_null=True
    )
    waste_reason_name = serializers.CharField(
        source='waste_reason.name', read_only=True, allow_null=True)

    class Meta:
        model = WasteAlert
        fields = [
            'id', 'alert_type', 'title', 'message',
            'waste_record', 'waste_record_id', 'waste_reason', 'waste_reason_name',
            'branch', 'branch_name',
            'is_read', 'is_resolved', 'resolved_by', 'resolved_at',
            'created_at'
        ]
        read_only_fields = ['is_read', 'is_resolved',
                            'resolved_by', 'resolved_at', 'created_at']


class WasteDashboardSerializer(serializers.Serializer):
    """Serializer for waste dashboard data"""

    # Summary stats
    total_waste_cost_today = serializers.DecimalField(
        max_digits=10, decimal_places=2)
    total_waste_cost_week = serializers.DecimalField(
        max_digits=10, decimal_places=2)
    total_waste_cost_month = serializers.DecimalField(
        max_digits=10, decimal_places=2)
    pending_reviews = serializers.IntegerField()
    recurring_issues = serializers.IntegerField()

    # Waste by category
    waste_by_category = serializers.ListField()

    # Recent waste
    recent_waste = serializers.ListField()

    # Alerts
    active_alerts = serializers.ListField()

    # Targets progress
    targets_progress = serializers.ListField()


class WasteAnalyticsSerializer(serializers.Serializer):
    """Serializer for waste analytics data"""

    period = serializers.DictField()
    summary = serializers.DictField()
    by_category = serializers.ListField()
    by_reason = serializers.ListField()
    by_station = serializers.ListField()
    by_staff = serializers.ListField()
    daily_trend = serializers.ListField()
    top_items = serializers.ListField()
