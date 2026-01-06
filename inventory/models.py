# inventory/models.py
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class StockItem(models.Model):
    """
    Represents an ingredient or item in inventory
    """
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('l', 'Liter'),
        ('ml', 'Milliliter'),
        ('unit', 'Unit'),
        ('pack', 'Pack'),
        ('dozen', 'Dozen'),
        ('bottle', 'Bottle'),
        ('can', 'Can'),
    ]

    CATEGORY_CHOICES = [
        ('meat', 'Meat & Poultry'),
        ('seafood', 'Seafood'),
        ('vegetable', 'Vegetables'),
        ('fruit', 'Fruits'),
        ('dairy', 'Dairy'),
        ('dry_goods', 'Dry Goods'),
        ('spices', 'Spices & Herbs'),
        ('beverage', 'Beverages'),
        ('cleaning', 'Cleaning Supplies'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default='other')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)

    # Stock tracking
    current_quantity = models.DecimalField(
        max_digits=10, decimal_places=3, default=0)
    minimum_quantity = models.DecimalField(
        max_digits=10, decimal_places=3, default=0)
    reorder_quantity = models.DecimalField(
        max_digits=10, decimal_places=3, default=0)

    # Cost tracking
    cost_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    last_purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)

    # Supplier info
    supplier = models.CharField(max_length=200, blank=True)
    supplier_code = models.CharField(max_length=100, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Restaurant relationship
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)
    branch = models.ForeignKey(
        'restaurants.Branch', on_delete=models.CASCADE, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'restaurant', 'branch']

    def __str__(self):
        branch_info = f" ({self.branch.name})" if self.branch else ""
        return f"{self.name} - {self.current_quantity} {self.unit}{branch_info}"

    @property
    def is_low_stock(self):
        """Check if stock is below minimum level"""
        return self.current_quantity <= self.minimum_quantity

    @property
    def stock_value(self):
        """Calculate total value of current stock"""
        return self.current_quantity * self.cost_per_unit

    @property
    def needs_reorder(self):
        """Check if reorder is needed"""
        return self.current_quantity <= self.reorder_quantity and self.is_active

    def consume(self, quantity, reason="", user=None):
        """
        Consume a quantity from stock
        """
        if quantity > self.current_quantity:
            raise ValueError(
                f"Insufficient stock. Available: {self.current_quantity}, Requested: {quantity}")

        self.current_quantity -= quantity
        self.save()

        # Create transaction record
        StockTransaction.objects.create(
            stock_item=self,
            transaction_type='usage',
            quantity=quantity,
            unit_cost=self.cost_per_unit,
            total_cost=quantity * self.cost_per_unit,
            reason=reason,
            user=user,
            restaurant=self.restaurant,
            branch=self.branch
        )

        # Check if low stock alert needed
        if self.is_low_stock:
            StockAlert.objects.get_or_create(
                stock_item=self,
                alert_type='low_stock',
                defaults={
                    'message': f'{self.name} is low on stock ({self.current_quantity} {self.unit} remaining)',
                    'resolved': False,
                    'restaurant': self.restaurant,
                    'branch': self.branch
                }
            )

        return self


class StockTransaction(models.Model):
    """
    Tracks all inventory movements
    """
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('usage', 'Usage'),
        ('adjustment', 'Adjustment'),
        ('waste', 'Waste'),
        ('transfer', 'Transfer'),
    ]

    stock_item = models.ForeignKey(
        StockItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPES)

    # Quantity details
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)

    # Reference information
    # Invoice, order number, etc.
    reference_number = models.CharField(max_length=100, blank=True)
    reason = models.TextField(blank=True)

    # User who performed the transaction
    user = models.ForeignKey('accounts.CustomUser',
                             on_delete=models.SET_NULL, null=True, blank=True)

    # Related models
    order = models.ForeignKey(
        'tables.Order', on_delete=models.SET_NULL, null=True, blank=True)
    menu_item = models.ForeignKey(
        'menu.MenuItem', on_delete=models.SET_NULL, null=True, blank=True)

    # Restaurant relationship
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)
    branch = models.ForeignKey(
        'restaurants.Branch', on_delete=models.CASCADE, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    transaction_date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.stock_item.name} - {self.quantity} {self.stock_item.unit}"


class StockAlert(models.Model):
    """
    Alerts for inventory issues
    """
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('expiring_soon', 'Expiring Soon'),
        ('overstock', 'Overstock'),
        ('zero_stock', 'Zero Stock'),
        ('price_change', 'Price Change'),
    ]

    stock_item = models.ForeignKey(
        StockItem, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)

    message = models.TextField()
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)

    # Additional data
    # For storing extra data like old/new prices
    metadata = models.JSONField(default=dict, blank=True)

    # Restaurant relationship
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)
    branch = models.ForeignKey(
        'restaurants.Branch', on_delete=models.CASCADE, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.stock_item.name}"

    def resolve(self, user=None):
        """Mark alert as resolved"""
        self.resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.save()


# Update the Recipe model in inventory/models.py to match your MenuItem model
class Recipe(models.Model):
    """
    Connects menu items to ingredients with quantities
    """
    menu_item = models.ForeignKey(
        'menu.MenuItem', on_delete=models.CASCADE, related_name='recipes')
    stock_item = models.ForeignKey(
        StockItem, on_delete=models.CASCADE, related_name='used_in_recipes')

    # Quantity required for one serving (in the unit of the stock item)
    quantity_required = models.DecimalField(max_digits=10, decimal_places=3)

    # Optional: Waste factor or preparation loss (percentage)
    waste_factor = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                       help_text="Percentage of ingredient lost during preparation (0-100)")

    # Notes
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['menu_item', 'stock_item']
        ordering = ['stock_item__name']

    def __str__(self):
        return f"{self.menu_item.name} - {self.stock_item.name} ({self.quantity_required} {self.stock_item.unit})"

    @property
    def adjusted_quantity(self):
        """Calculate quantity including waste factor"""
        from decimal import Decimal
        waste_multiplier = Decimal('1') + (self.waste_factor / Decimal('100'))
        return self.quantity_required * waste_multiplier

    @property
    def ingredient_cost(self):
        """Calculate cost of this ingredient for one serving"""
        from decimal import Decimal
        return self.adjusted_quantity * self.stock_item.cost_per_unit

    def update_menu_item_cost(self):
        """Update the menu item's cost_price based on this recipe"""
        # Calculate total cost from all recipes for this menu item
        all_recipes = Recipe.objects.filter(menu_item=self.menu_item)
        total_cost = sum(recipe.ingredient_cost for recipe in all_recipes)

        # Update menu item cost_price
        self.menu_item.cost_price = total_cost
        self.menu_item.save(update_fields=['cost_price'])

        return total_cost


class InventoryReport(models.Model):
    """
    Stores generated inventory reports
    """
    REPORT_TYPES = [
        ('daily', 'Daily Stock'),
        ('weekly', 'Weekly Summary'),
        ('monthly', 'Monthly Analysis'),
        ('waste', 'Waste Analysis'),
        ('valuation', 'Stock Valuation'),
    ]

    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)

    # Report data
    data = models.JSONField()  # Store report data as JSON
    summary = models.TextField()

    # Date range
    start_date = models.DateField()
    end_date = models.DateField()

    # Generated by
    generated_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True)

    # Restaurant relationship
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)
    branch = models.ForeignKey(
        'restaurants.Branch', on_delete=models.CASCADE, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report_type} Report - {self.title} - {self.created_at.date()}"
