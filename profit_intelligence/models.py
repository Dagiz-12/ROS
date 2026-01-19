# profit_intelligence/models.py - CORRECTED VERSION
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

# Helper function to generate UUIDs


def generate_uuid():
    return str(uuid.uuid4())


class ProfitAggregation(models.Model):
    """Core aggregated profit data for fast queries"""
    class AggregationLevel(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'

    # Identification - FIXED: Add null=True for migration
    aggregation_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, null=True, blank=True)
    level = models.CharField(
        max_length=20, choices=AggregationLevel.choices, default='daily')
    # For daily: date, for weekly: Monday date, for monthly: 1st day of month
    date = models.DateField()

    # Restaurant scope
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)
    branch = models.ForeignKey(
        'restaurants.Branch', on_delete=models.SET_NULL, null=True, blank=True)

    # ============ FINANCIAL METRICS ============
    # Revenue
    revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Costs
    cost_of_goods = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    labor_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    overhead_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Profit
    gross_profit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0)
    net_profit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0)
    profit_margin = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)  # percentage

    # ============ OPERATIONAL METRICS ============
    order_count = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])
    customer_count = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])
    average_order_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    table_turnover = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)  # times per day

    # ============ WASTE METRICS ============
    waste_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    waste_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)  # % of cost_of_goods
    top_wasted_items = models.JSONField(
        default=dict, blank=True)  # JSON: {item_name: cost}

    # ============ PERFORMANCE FLAGS ============
    is_above_target = models.BooleanField(default=False)
    has_issues = models.BooleanField(default=False)
    data_quality_score = models.DecimalField(
        max_digits=3, decimal_places=2, default=1.0)  # 0-1

    # ============ TIMESTAMPS ============
    calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profit Aggregation"
        verbose_name_plural = "Profit Aggregations"
        unique_together = ['level', 'date', 'restaurant', 'branch']
        indexes = [
            models.Index(fields=['date', 'restaurant']),
            models.Index(fields=['restaurant', 'branch', 'level', 'date']),
            models.Index(fields=['profit_margin']),
            models.Index(fields=['has_issues']),
        ]
        ordering = ['-date', '-level']

    def __str__(self):
        branch_info = f" - {self.branch.name}" if self.branch else ""
        return f"{self.get_level_display()} Profit - {self.date} - {self.restaurant.name}{branch_info}"

    def save(self, *args, **kwargs):
        # Auto-calculate derived fields
        self.total_cost = self.cost_of_goods + self.labor_cost + self.overhead_cost
        self.gross_profit = self.revenue - self.cost_of_goods
        self.net_profit = self.revenue - self.total_cost

        # Calculate profit margin (avoid division by zero)
        if self.revenue > 0:
            self.profit_margin = (
                self.net_profit / self.revenue) * Decimal('100')

        # Calculate waste percentage
        if self.cost_of_goods > 0:
            self.waste_percentage = (
                self.waste_cost / self.cost_of_goods) * Decimal('100')

        # Calculate average order value
        if self.order_count > 0:
            self.average_order_value = self.revenue / self.order_count

        super().save(*args, **kwargs)

    @property
    def profit_per_order(self):
        """Average profit per order"""
        if self.order_count > 0:
            return self.net_profit / self.order_count
        return Decimal('0.00')

    @property
    def waste_cost_per_order(self):
        """Average waste cost per order"""
        if self.order_count > 0:
            return self.waste_cost / self.order_count
        return Decimal('0.00')


class MenuItemPerformance(models.Model):
    """Daily performance tracking for each menu item"""

    # Identification - FIXED: Add null=True temporarily
    performance_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, null=True)
    date = models.DateField()
    menu_item = models.ForeignKey(
        'menu.MenuItem', on_delete=models.CASCADE, related_name='performance_records')

    # Restaurant scope
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)
    branch = models.ForeignKey(
        'restaurants.Branch', on_delete=models.SET_NULL, null=True, blank=True)

    # ============ SALES METRICS ============
    quantity_sold = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])
    revenue = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # ============ COST METRICS ============
    ingredient_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    labor_cost_share = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # ============ PROFIT METRICS ============
    gross_profit = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    net_profit = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    profit_margin = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)  # percentage

    # ============ PERFORMANCE RANKING ============
    revenue_rank = models.IntegerField(
        default=0)  # Rank by revenue (1 = highest)
    profit_rank = models.IntegerField(default=0)   # Rank by profit
    margin_rank = models.IntegerField(default=0)   # Rank by margin

    # ============ TREND ANALYSIS ============
    previous_day_quantity = models.IntegerField(default=0)
    quantity_change = models.IntegerField(default=0)  # vs previous day
    trend = models.CharField(max_length=20, choices=[
        ('up', 'Increasing'),
        ('down', 'Decreasing'),
        ('stable', 'Stable'),
        ('new', 'New Item'),
    ], default='stable')

    # ============ TIMESTAMPS ============
    calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Menu Item Performance"
        verbose_name_plural = "Menu Item Performances"
        unique_together = ['date', 'menu_item', 'restaurant', 'branch']
        indexes = [
            models.Index(fields=['date', 'menu_item']),
            models.Index(fields=['menu_item', 'date']),
            models.Index(fields=['profit_margin']),
            models.Index(fields=['revenue_rank', 'date']),
            models.Index(fields=['profit_rank', 'date']),
        ]
        ordering = ['date', '-revenue']

    def __str__(self):
        return f"{self.menu_item.name} - {self.date} - Sold: {self.quantity_sold}"

    def save(self, *args, **kwargs):
        # Auto-calculate derived fields
        self.gross_profit = self.revenue - self.ingredient_cost
        self.total_cost = self.ingredient_cost + self.labor_cost_share

        # Calculate net profit and margin
        self.net_profit = self.revenue - self.total_cost
        if self.revenue > 0:
            self.profit_margin = (
                self.net_profit / self.revenue) * Decimal('100')

        # Calculate change from previous day
        if not self.pk:  # Only on creation
            try:
                prev_day = MenuItemPerformance.objects.filter(
                    menu_item=self.menu_item,
                    restaurant=self.restaurant,
                    branch=self.branch,
                    date=self.date - timezone.timedelta(days=1)
                ).first()
                if prev_day:
                    self.previous_day_quantity = prev_day.quantity_sold
                    self.quantity_change = self.quantity_sold - prev_day.quantity_sold

                    # Determine trend
                    if self.quantity_change > 2:
                        self.trend = 'up'
                    elif self.quantity_change < -2:
                        self.trend = 'down'
                    else:
                        self.trend = 'stable'
            except:
                pass

        super().save(*args, **kwargs)

    @property
    def profit_per_unit(self):
        """Profit per unit sold"""
        if self.quantity_sold > 0:
            return self.net_profit / self.quantity_sold
        return Decimal('0.00')


class ProfitAlert(models.Model):
    """Intelligent alerts for profit-related issues"""

    class AlertType(models.TextChoices):
        LOW_MARGIN = 'low_margin', 'Low Profit Margin (< 15%)'
        LOSS_MAKER = 'loss_maker', 'Selling at Loss'
        PRICE_ADJUSTMENT = 'price_adjustment', 'Price Adjustment Suggested'
        WASTE_SPIKE = 'waste_spike', 'Waste Cost Spike (> 10%)'
        DEMAND_DROP = 'demand_drop', 'Significant Demand Drop'
        COST_INCREASE = 'cost_increase', 'Ingredient Cost Increased'
        PERFORMANCE_DROP = 'performance_drop', 'Performance Drop'
        INVENTORY_SHORTAGE = 'inventory_shortage', 'Inventory Affecting Sales'

    class AlertSeverity(models.TextChoices):
        CRITICAL = 'critical', 'Critical (Immediate Action)'
        HIGH = 'high', 'High (Address Today)'
        MEDIUM = 'medium', 'Medium (Address This Week)'
        LOW = 'low', 'Low (Monitor)'
        INFO = 'info', 'Informational'

    # Identification - FIXED: Add null=True
    alert_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, null=True)
    alert_type = models.CharField(max_length=30, choices=AlertType.choices)
    severity = models.CharField(
        max_length=20, choices=AlertSeverity.choices, default='MEDIUM')

    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)  # Additional data

    # Related items
    menu_item = models.ForeignKey(
        'menu.MenuItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='profit_alerts')
    stock_item = models.ForeignKey(
        'inventory.StockItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='profit_alerts')
    order = models.ForeignKey('tables.Order', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='profit_alerts')

    # Metrics
    current_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    threshold = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    deviation = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)  # How far from normal

    # Status
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    resolution_notes = models.TextField(blank=True)

    # Automatic resolution
    auto_resolve = models.BooleanField(default=False)
    auto_resolve_condition = models.JSONField(
        default=dict, blank=True)  # When to auto-resolve

    # Restaurant scope
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)
    branch = models.ForeignKey(
        'restaurants.Branch', on_delete=models.SET_NULL, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')

    class Meta:
        verbose_name = "Profit Alert"
        verbose_name_plural = "Profit Alerts"
        indexes = [
            models.Index(fields=['alert_type', 'is_resolved']),
            models.Index(fields=['severity', 'created_at']),
            models.Index(fields=['menu_item', 'is_resolved']),
            models.Index(fields=['restaurant', 'branch', 'is_resolved']),
        ]
        ordering = ['-severity', '-created_at']

    def __str__(self):
        return f"{self.get_severity_display()}: {self.title}"

    def acknowledge(self, user):
        """Mark alert as acknowledged"""
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        self.save(update_fields=['acknowledged_at',
                  'acknowledged_by', 'updated_at'])

    def resolve(self, user, notes=""):
        """Mark alert as resolved"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.resolution_notes = notes
        self.save(update_fields=['is_resolved', 'resolved_at',
                  'resolved_by', 'resolution_notes', 'updated_at'])

    @property
    def is_acknowledged(self):
        return self.acknowledged_at is not None

    @property
    def age_days(self):
        """How many days old is this alert"""
        return (timezone.now() - self.created_at).days


class PriceOptimization(models.Model):
    """AI-powered price optimization suggestions"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved for Implementation'
        REJECTED = 'rejected', 'Rejected'
        IMPLEMENTED = 'implemented', 'Implemented'
        EXPIRED = 'expired', 'Expired (Market Changed)'

    # Identification - FIXED: Add null=True
    optimization_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, null=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default='pending')

    # Menu item
    menu_item = models.ForeignKey(
        'menu.MenuItem', on_delete=models.CASCADE, related_name='price_optimizations')
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)

    # Current metrics
    current_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    current_cost = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    current_margin = models.DecimalField(
        max_digits=5, decimal_places=2)  # percentage
    current_demand = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)  # units sold per day

    # Suggested changes
    suggested_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    projected_margin = models.DecimalField(
        max_digits=5, decimal_places=2)  # percentage
    price_change_percent = models.DecimalField(
        max_digits=5, decimal_places=2)  # % change

    # AI/ML metrics
    confidence_score = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.5)  # 0-1 confidence
    algorithm_version = models.CharField(max_length=50, default='v1.0')
    features_used = models.JSONField(
        default=list, blank=True)  # Features considered

    # Reasoning
    reason = models.TextField()  # AI-generated explanation
    # Main factors influencing decision
    key_factors = models.JSONField(default=list, blank=True)

    # Impact projections
    projected_demand_change = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)  # % change in demand
    projected_revenue_change = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)  # $ change
    projected_profit_change = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)  # $ change
    projected_roi = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)  # Return on investment

    # Competitive analysis
    competitor_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    market_average_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)

    # Status tracking
    is_applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='applied_optimizations')

    applied_actual_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    actual_margin_after = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    actual_demand_after = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    actual_profit_change = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    valid_until = models.DateTimeField(
        null=True, blank=True)  # When suggestion expires

    class Meta:
        verbose_name = "Price Optimization"
        verbose_name_plural = "Price Optimizations"
        indexes = [
            models.Index(fields=['menu_item', 'status']),
            models.Index(fields=['restaurant', 'created_at']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['projected_profit_change']),
        ]
        ordering = ['-confidence_score', '-projected_profit_change']

    def __str__(self):
        return f"Price Opt: {self.menu_item.name} ${self.current_price} → ${self.suggested_price}"

    def apply(self, user, actual_price=None):
        """Apply this price optimization"""
        if actual_price is None:
            actual_price = self.suggested_price

        self.status = 'implemented'
        self.is_applied = True
        self.applied_at = timezone.now()
        self.applied_by = user
        self.applied_actual_price = actual_price

        # Update menu item price
        self.menu_item.price = actual_price
        self.menu_item.save(update_fields=['price', 'updated_at'])

        self.save(update_fields=[
            'status', 'is_applied', 'applied_at', 'applied_by',
            'applied_actual_price', 'updated_at'
        ])

    def reject(self, user, reason=""):
        """Reject this optimization"""
        self.status = 'rejected'
        self.reason = f"{self.reason}\n\nRejected: {reason}"
        self.save(update_fields=['status', 'reason', 'updated_at'])

    @property
    def is_expired(self):
        """Check if suggestion is expired"""
        if self.valid_until:
            return timezone.now() > self.valid_until
        return False

    @property
    def expected_profit_increase_per_day(self):
        """Expected daily profit increase"""
        return self.projected_profit_change * self.current_demand


class ProfitReport(models.Model):
    """Generated profit reports"""
    # Identification - FIXED: Add null=True
    report_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, null=True, blank=True)
    date = models.DateField()

    # Restaurant scope
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)
    branch = models.ForeignKey(
        'restaurants.Branch', on_delete=models.SET_NULL, null=True, blank=True)

    # Report data
    report_type = models.CharField(
        max_length=50, default='daily')  # daily, weekly, monthly
    data = models.JSONField()  # Full report data
    summary = models.TextField(blank=True)

    # Generation info
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)

    # Distribution
    emailed_to = models.JSONField(
        default=list, blank=True)  # List of email addresses
    emailed_at = models.DateTimeField(null=True, blank=True)

    # Status
    is_archived = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Profit Report"
        verbose_name_plural = "Profit Reports"
        indexes = [
            models.Index(fields=['date', 'restaurant']),
            models.Index(fields=['restaurant', 'branch', 'report_type']),
        ]
        ordering = ['-date', '-generated_at']

    def __str__(self):
        branch_info = f" - {self.branch.name}" if self.branch else ""
        return f"Profit Report - {self.date} - {self.restaurant.name}{branch_info}"
