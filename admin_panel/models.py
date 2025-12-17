"""
Extended models for admin panel functionality
"""

from django.db import models
from django.contrib.auth import get_user_model
from restaurants.models import Restaurant, Branch
from menu.models import Category, MenuItem

User = get_user_model()


class RestaurantAnalytics(models.Model):
    """Store analytics data for restaurants"""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    date = models.DateField()
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    average_order_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    most_popular_item = models.ForeignKey(
        MenuItem, null=True, on_delete=models.SET_NULL)
    peak_hour = models.TimeField(null=True)

    class Meta:
        unique_together = ['restaurant', 'date']
        verbose_name_plural = 'Restaurant Analytics'


class StaffPerformance(models.Model):
    """Track staff performance metrics"""
    staff = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={
                              'role__in': ['waiter', 'chef']})
    date = models.DateField()
    orders_served = models.IntegerField(default=0)  # For waiters
    orders_prepared = models.IntegerField(default=0)  # For chefs
    average_preparation_time = models.IntegerField(
        default=0)  # In minutes, for chefs
    total_sales = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)  # For waiters

    class Meta:
        unique_together = ['staff', 'date']
        verbose_name_plural = 'Staff Performance'


class InventoryAlert(models.Model):
    """Inventory alerts for restaurant owners"""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=200)
    current_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    alert_type = models.CharField(max_length=20, choices=[
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('expiring_soon', 'Expiring Soon'),
    ])
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.item_name} - {self.alert_type}"


class DailyReport(models.Model):
    """Daily reports for restaurant owners"""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    report_date = models.DateField()
    report_type = models.CharField(max_length=20, choices=[
        ('sales', 'Sales Report'),
        ('inventory', 'Inventory Report'),
        ('staff', 'Staff Performance'),
        ('customers', 'Customer Analytics'),
    ])
    data = models.JSONField()  # Store report data in JSON format
    generated_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['restaurant', 'report_date', 'report_type']
