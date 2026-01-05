from decimal import Decimal
from django.utils import timezone
from django.db import models
from django.core.validators import MinValueValidator


class Category(models.Model):
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order_index = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order_index', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


# menu/models.py - UPDATE


class MenuItem(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    preparation_time = models.IntegerField(
        default=15, help_text="Preparation time in minutes")

    # ✅ NEW: Business Intelligence Fields
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Ingredient cost per serving"
    )
    sold_count = models.IntegerField(default=0, help_text="Total units sold")
    last_sold = models.DateTimeField(null=True, blank=True)
    profit_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Profit margin percentage (auto-calculated)"
    )
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total revenue generated"
    )
    total_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total profit generated"
    )

    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['sold_count']),
            models.Index(fields=['profit_margin']),
            models.Index(fields=['total_revenue']),
        ]

    def __str__(self):
        return f"{self.name} - ${self.price}"

    def save(self, *args, **kwargs):
        # Auto-calculate profit margin if cost_price is set
        if self.cost_price > 0 and self.price > 0:
            profit_amount = self.price - self.cost_price
            self.profit_margin = (profit_amount / self.price) * 100
        super().save(*args, **kwargs)

    def update_sales(self, quantity=1):
        """Update sales statistics when item is sold"""
        from django.db.models import F
        self.sold_count = F('sold_count') + quantity
        self.last_sold = timezone.now()
        self.total_revenue = F('total_revenue') + (self.price * quantity)
        self.total_profit = F('total_profit') + \
            ((self.price - self.cost_price) * quantity)
        self.save(update_fields=['sold_count', 'last_sold',
                  'total_revenue', 'total_profit', 'updated_at'])
