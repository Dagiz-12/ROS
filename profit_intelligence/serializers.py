# profit_intelligence/serializers.py
from rest_framework import serializers
from .models import ProfitAggregation, MenuItemPerformance, ProfitAlert, PriceOptimization


class ProfitAggregationSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(
        source='restaurant.name', read_only=True)
    branch_name = serializers.CharField(
        source='branch.name', read_only=True, allow_null=True)

    # Calculated properties
    profit_per_order = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    waste_cost_per_order = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ProfitAggregation
        fields = [
            'aggregation_id', 'level', 'date',
            'restaurant', 'restaurant_name', 'branch', 'branch_name',
            'revenue', 'cost_of_goods', 'labor_cost', 'overhead_cost', 'total_cost',
            'waste_cost', 'waste_percentage',
            'gross_profit', 'net_profit', 'profit_margin',
            'order_count', 'customer_count', 'average_order_value', 'table_turnover',
            'profit_per_order', 'waste_cost_per_order',
            'is_above_target', 'has_issues', 'data_quality_score',
            'calculated_at', 'created_at'
        ]
        read_only_fields = ['aggregation_id', 'calculated_at', 'created_at']


class MenuItemPerformanceSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(
        source='menu_item.name', read_only=True)
    menu_item_price = serializers.DecimalField(
        source='menu_item.price', read_only=True, max_digits=10, decimal_places=2)
    menu_item_category = serializers.CharField(
        source='menu_item.category.name', read_only=True, allow_null=True)
    restaurant_name = serializers.CharField(
        source='restaurant.name', read_only=True)
    branch_name = serializers.CharField(
        source='branch.name', read_only=True, allow_null=True)

    # Calculated properties
    profit_per_unit = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = MenuItemPerformance
        fields = [
            'performance_id', 'date',
            'menu_item', 'menu_item_name', 'menu_item_price', 'menu_item_category',
            'restaurant', 'restaurant_name', 'branch', 'branch_name',
            'quantity_sold', 'revenue', 'ingredient_cost', 'labor_cost_share', 'total_cost',
            'gross_profit', 'net_profit', 'profit_margin', 'profit_per_unit',
            'revenue_rank', 'profit_rank', 'margin_rank',
            'previous_day_quantity', 'quantity_change', 'trend',
            'calculated_at', 'created_at'
        ]
        read_only_fields = ['performance_id', 'calculated_at', 'created_at']


class ProfitAlertSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(
        source='menu_item.name', read_only=True, allow_null=True)
    menu_item_price = serializers.DecimalField(
        source='menu_item.price', read_only=True, max_digits=10, decimal_places=2, allow_null=True)
    stock_item_name = serializers.CharField(
        source='stock_item.name', read_only=True, allow_null=True)
    order_number = serializers.CharField(
        source='order.order_number', read_only=True, allow_null=True)
    restaurant_name = serializers.CharField(
        source='restaurant.name', read_only=True)
    branch_name = serializers.CharField(
        source='branch.name', read_only=True, allow_null=True)
    resolved_by_name = serializers.CharField(
        source='resolved_by.username', read_only=True, allow_null=True)
    acknowledged_by_name = serializers.CharField(
        source='acknowledged_by.username', read_only=True, allow_null=True)

    # Status flags
    is_acknowledged = serializers.BooleanField(read_only=True)
    age_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProfitAlert
        fields = [
            'alert_id', 'alert_type', 'severity',
            'title', 'message', 'details',
            'menu_item', 'menu_item_name', 'menu_item_price',
            'stock_item', 'stock_item_name',
            'order', 'order_number',
            'current_value', 'threshold', 'deviation',
            'is_resolved', 'resolved_at', 'resolved_by', 'resolved_by_name', 'resolution_notes',
            'is_acknowledged', 'acknowledged_at', 'acknowledged_by', 'acknowledged_by_name',
            'auto_resolve', 'auto_resolve_condition',
            'restaurant', 'restaurant_name', 'branch', 'branch_name',
            'created_at', 'updated_at', 'age_days'
        ]
        read_only_fields = ['alert_id', 'created_at', 'updated_at']


class PriceOptimizationSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(
        source='menu_item.name', read_only=True)
    menu_item_category = serializers.CharField(
        source='menu_item.category.name', read_only=True, allow_null=True)
    restaurant_name = serializers.CharField(
        source='restaurant.name', read_only=True)
    applied_by_name = serializers.CharField(
        source='applied_by.username', read_only=True, allow_null=True)

    # Calculated properties
    is_expired = serializers.BooleanField(read_only=True)
    expected_profit_increase_per_day = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    price_change_amount = serializers.SerializerMethodField()

    class Meta:
        model = PriceOptimization
        fields = [
            'optimization_id', 'status',
            'menu_item', 'menu_item_name', 'menu_item_category',
            'restaurant', 'restaurant_name',
            'current_price', 'current_cost', 'current_margin', 'current_demand',
            'suggested_price', 'projected_margin', 'price_change_percent', 'price_change_amount',
            'confidence_score', 'algorithm_version', 'features_used',
            'reason', 'key_factors',
            'projected_demand_change', 'projected_revenue_change', 'projected_profit_change', 'projected_roi',
            'expected_profit_increase_per_day',
            'competitor_price', 'market_average_price',
            'is_applied', 'applied_at', 'applied_by', 'applied_by_name',
            'applied_actual_price', 'actual_margin_after', 'actual_demand_after', 'actual_profit_change',
            'created_at', 'updated_at', 'valid_until', 'is_expired'
        ]
        read_only_fields = ['optimization_id', 'created_at', 'updated_at']

    def get_price_change_amount(self, obj):
        return obj.suggested_price - obj.current_price


class ProfitDashboardSerializer(serializers.Serializer):
    """Serializer for profit dashboard data"""

    # View information
    view = serializers.DictField()

    # Today's profit
    today = serializers.DictField()

    # Daily change
    daily_change = serializers.DictField()

    # Trend data
    trend = serializers.DictField()

    # Issues
    issues = serializers.DictField()

    # KPIs
    kpis = serializers.DictField()

    # Status
    success = serializers.BooleanField()
    timestamp = serializers.DateTimeField()


class MenuItemProfitAnalysisSerializer(serializers.Serializer):
    """Serializer for menu item profit analysis"""

    items = MenuItemPerformanceSerializer(many=True)

    period = serializers.DictField()
    summary = serializers.DictField()

    success = serializers.BooleanField()


class ProfitIssuesSerializer(serializers.Serializer):
    """Serializer for profit issues"""

    loss_makers = serializers.ListField()
    low_margin_items = serializers.ListField()
    high_waste_items = serializers.ListField()
    price_suggestions = serializers.ListField()

    summary = serializers.DictField()

    success = serializers.BooleanField()


class ProfitAlertsSummarySerializer(serializers.Serializer):
    """Serializer for profit alerts summary"""

    alerts = ProfitAlertSerializer(many=True)

    counts = serializers.DictField()

    success = serializers.BooleanField()
