# waste_tracker/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Sum, Avg
import uuid

from inventory.models import StockItem, StockTransaction
from restaurants.models import Restaurant, Branch

User = get_user_model()


class WasteCategory(models.Model):
    """Categories of waste (spoilage, preparation, customer_return, etc.)"""

    WASTE_CATEGORY_TYPES = [
        ('spoilage', 'Spoilage/Expired'),
        ('preparation', 'Preparation Waste'),
        ('overproduction', 'Overproduction'),
        ('customer_return', 'Customer Return'),
        ('damaged', 'Damaged Goods'),
        ('theft', 'Theft/Suspected Theft'),
        ('portion_control', 'Portion Control Issue'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100)
    category_type = models.CharField(
        max_length=50, choices=WASTE_CATEGORY_TYPES, default='other')
    description = models.TextField(blank=True)
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name='waste_categories')
    color_code = models.CharField(max_length=7, default='#666666')
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Waste Categories"
        ordering = ['sort_order', 'name']
        unique_together = ['restaurant', 'name']

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

    def total_waste_cost(self, days=30):
        """Calculate total waste cost for this category in last N days"""
        from django.utils.timezone import now
        from datetime import timedelta

        cutoff_date = now() - timedelta(days=days)
        total = WasteRecord.objects.filter(
            waste_reason__category=self,
            recorded_at__gte=cutoff_date,
            status='approved'
        ).aggregate(total=Sum('total_cost'))['total']

        return total or 0


class WasteReason(models.Model):
    """Specific reasons for waste within categories"""

    CONTROLLABILITY_CHOICES = [
        ('controllable', 'Controllable'),
        ('uncontrollable', 'Uncontrollable'),
        ('partially_controllable', 'Partially Controllable'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        WasteCategory, on_delete=models.CASCADE, related_name='reasons')
    controllability = models.CharField(
        max_length=30, choices=CONTROLLABILITY_CHOICES, default='controllable')
    requires_explanation = models.BooleanField(default=False)
    requires_photo = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Threshold for alerts
    alert_threshold_daily = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    alert_threshold_weekly = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        unique_together = ['category', 'name']

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class WasteRecord(models.Model):
    """
    Enhanced waste recording that LINKS TO existing StockTransaction
    This provides detailed waste tracking while reusing inventory infrastructure
    """

    WASTE_STATUS_CHOICES = [
        ('pending', '⏳ Pending Review'),
        ('approved', '✅ Approved'),
        ('rejected', '❌ Rejected'),
        ('investigating', '🔍 Under Investigation'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    # Link to existing inventory system
    stock_transaction = models.OneToOneField(
        StockTransaction,
        on_delete=models.CASCADE,
        related_name='waste_detail',
        null=True,  # Can be created before transaction
        blank=True
    )

    # Waste classification
    waste_reason = models.ForeignKey(
        WasteReason, on_delete=models.CASCADE, related_name='records')
    waste_source = models.CharField(max_length=100, blank=True)

    # People involved
    recorded_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='waste_records_recorded')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='waste_records_reviewed')

    # Status and workflow
    status = models.CharField(
        max_length=30, choices=WASTE_STATUS_CHOICES, default='pending')
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default='medium')

    # Location/context
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name='waste_records')
    station = models.CharField(max_length=100, blank=True)
    shift = models.CharField(max_length=50, blank=True)

    # Additional details
    notes = models.TextField(blank=True)
    corrective_action = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to='waste_photos/%Y/%m/%d/', null=True, blank=True)

    # For tracking
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(null=True, blank=True)

    # System fields
    is_recurring_issue = models.BooleanField(default=False)
    recurrence_id = models.UUIDField(null=True, blank=True)
    requires_followup = models.BooleanField(default=False)
    followup_date = models.DateField(null=True, blank=True)

    # Additional timestamps
    recorded_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    corrected_at = models.DateTimeField(null=True, blank=True)
    waste_occurred_at = models.DateTimeField(null=True, blank=True)

    # Unique waste identifier
    waste_id = models.UUIDField(default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['branch', 'created_at']),
            models.Index(fields=['waste_reason', 'created_at']),
        ]

    def __str__(self):
        if self.stock_transaction:
            return f"Waste Detail: {self.stock_transaction}"
        return f"Waste Record #{self.id}"

    def save(self, *args, **kwargs):
        # Auto-create linked StockTransaction if not exists
        if not self.stock_transaction and hasattr(self, '_stock_item') and hasattr(self, '_quantity'):
            self._create_stock_transaction()

        # Set priority based on cost if transaction exists
        if self.stock_transaction and self.stock_transaction.total_cost:
            cost = self.stock_transaction.total_cost
            if cost > 100:
                self.priority = 'critical'
            elif cost > 50:
                self.priority = 'high'
            elif cost > 20:
                self.priority = 'medium'
            else:
                self.priority = 'low'

        super().save(*args, **kwargs)

    def _create_stock_transaction(self):
        """Create linked StockTransaction for this waste"""
        if hasattr(self, '_stock_item') and hasattr(self, '_quantity'):
            self.stock_transaction = StockTransaction.objects.create(
                stock_item=self._stock_item,
                transaction_type='waste',
                quantity=self._quantity,
                unit_cost=self._stock_item.cost_per_unit,
                total_cost=self._quantity * self._stock_item.cost_per_unit,
                reason=f"Waste: {self.waste_reason.name}",
                user=self.recorded_by,
                restaurant=self.branch.restaurant,
                branch=self.branch
            )

    def approve(self, reviewer, notes=""):
        """Approve waste record"""
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        if notes:
            self.notes = f"{self.notes}\n\nApproval Notes: {notes}"
        self.save()

    def reject(self, reviewer, reason):
        """Reject waste record"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.notes = f"{self.notes}\n\nRejection Reason: {reason}"

        # Optionally delete the linked transaction if rejected
        if self.stock_transaction:
            self.stock_transaction.delete()

        self.save()

    @property
    def stock_item(self):
        """Get stock item from linked transaction"""
        if self.stock_transaction:
            return self.stock_transaction.stock_item
        return None

    @property
    def quantity(self):
        """Get quantity from linked transaction"""
        if self.stock_transaction:
            return self.stock_transaction.quantity
        return None

    @property
    def total_cost(self):
        """Get total cost from linked transaction"""
        if self.stock_transaction:
            return self.stock_transaction.total_cost
        return 0

    def _detect_recurring_issue(self):
        """
        Detect if this waste appears to be a recurring issue
        """
        if not self.stock_item or not self.waste_reason:
            return False

        from django.utils import timezone
        from datetime import timedelta
        import uuid

        # Look for similar waste records in the last 7 days
        seven_days_ago = timezone.now() - timedelta(days=7)

        similar_records = WasteRecord.objects.filter(
            stock_transaction__stock_item=self.stock_item,
            waste_reason=self.waste_reason,
            status__in=['approved', 'pending'],
            recorded_at__gte=seven_days_ago
        ).exclude(id=self.id)

        if similar_records.exists():
            # This is a recurring issue
            self.is_recurring_issue = True

            # Use the first similar record's recurrence_id or generate new one
            first_similar = similar_records.first()
            if first_similar and first_similar.recurrence_id:
                self.recurrence_id = first_similar.recurrence_id
            else:
                self.recurrence_id = uuid.uuid4()

            return True

        return False


class WasteTarget(models.Model):
    """Waste reduction targets"""

    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    name = models.CharField(max_length=200)
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name='waste_targets')
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, null=True, blank=True)

    target_type = models.CharField(max_length=50, choices=[
        ('cost', 'Cost Target ($)'),
        ('percentage', 'Percentage of Sales (%)'),
        ('quantity', 'Quantity Target'),
    ])
    target_value = models.DecimalField(max_digits=10, decimal_places=2)
    period = models.CharField(
        max_length=20, choices=PERIOD_CHOICES, default='monthly')

    waste_categories = models.ManyToManyField(WasteCategory, blank=True)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    current_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', 'name']

    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"

    def calculate_current_value(self):
        """Calculate current waste against target"""
        from datetime import timedelta

        end_date = timezone.now().date()
        if self.period == 'daily':
            start_date = end_date
        elif self.period == 'weekly':
            start_date = end_date - timedelta(days=7)
        else:  # monthly
            start_date = end_date - timedelta(days=30)

        # Calculate waste for period
        waste_records = WasteRecord.objects.filter(
            branch=self.branch if self.branch else self.restaurant.branches.all(),
            waste_reason__category__in=self.waste_categories.all(),
            status='approved',
            recorded_at__date__gte=start_date,
            recorded_at__date__lte=end_date
        )

        if self.target_type == 'cost':
            total_cost = 0
            for record in waste_records:
                if record.stock_transaction:
                    total_cost += record.stock_transaction.total_cost
            self.current_value = total_cost
        elif self.target_type == 'quantity':
            self.current_value = waste_records.count()

        self.save(update_fields=['current_value', 'last_updated'])
        return self.current_value


class WasteAlert(models.Model):
    """Alerts for waste-related issues"""

    ALERT_TYPES = [
        ('threshold_exceeded', 'Threshold Exceeded'),
        ('recurring_issue', 'Recurring Issue'),
        ('approval_needed', 'Approval Needed'),
        ('target_at_risk', 'Target at Risk'),
    ]

    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()

    waste_record = models.ForeignKey(
        WasteRecord, on_delete=models.CASCADE, null=True, blank=True)
    waste_reason = models.ForeignKey(
        WasteReason, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
