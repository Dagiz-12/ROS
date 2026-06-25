# accounts/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import models
from django.utils import timezone
from decimal import Decimal
from .models import CustomUser
from tables.models import Order


@receiver(post_save, sender=Order)
def update_staff_performance(sender, instance, created, **kwargs):
    """
    Update staff performance metrics when order status changes.
    Triggers on: order completion, preparation start, ready status
    """
    # Only process if order is completed and paid
    if instance.status == 'completed' and instance.is_paid:
        update_waiter_performance(instance)
        update_cashier_performance(instance)

    # Track chef performance when order is marked ready
    if instance.status == 'ready' and instance.chef:
        update_chef_performance(instance)


def update_waiter_performance(order):
    """Update waiter performance metrics"""
    if not order.waiter:
        return

    waiter = order.waiter
    if waiter.role != 'waiter':
        return

    # Count orders handled
    waiter.orders_handled = Order.objects.filter(
        waiter=waiter,
        status='completed',
        is_paid=True
    ).count()

    # Calculate total sales
    sales = Order.objects.filter(
        waiter=waiter,
        status='completed',
        is_paid=True
    ).aggregate(total=models.Sum('total_amount'))['total'] or 0
    waiter.sales_value = Decimal(str(sales))

    # Calculate performance score
    # 50% from orders handled (50 orders = 50 points)
    order_score = min((waiter.orders_handled / 50) * 50, 50)
    # 50% from sales value ($1000 = 50 points)
    sales_score = min((float(waiter.sales_value) / 1000) * 50, 50)
    waiter.performance_score = order_score + sales_score

    # Update performance history
    waiter.performance_history = waiter.performance_history or []
    waiter.performance_history.append({
        'date': timezone.now().isoformat(),
        'orders_handled': waiter.orders_handled,
        'sales_value': float(waiter.sales_value),
        'performance_score': waiter.performance_score
    })
    # Keep last 30 entries
    waiter.performance_history = waiter.performance_history[-30:]

    waiter.save(update_fields=[
        'orders_handled', 'sales_value',
        'performance_score', 'performance_history'
    ])


def update_cashier_performance(order):
    """Update cashier performance metrics"""
    # This would track cashier who processed the payment
    # You'd need to add a cashier field to Order or Payment model
    # For now, this is a placeholder
    pass


def update_chef_performance(order):
    """Update chef performance metrics when order is ready"""
    if not order.chef:
        return

    chef = order.chef
    if chef.role != 'chef':
        return

    # Count orders prepared
    chef.orders_prepared = Order.objects.filter(
        chef=chef,
        status__in=['ready', 'served', 'completed']
    ).count()

    # Calculate average prep time
    prep_times = Order.objects.filter(
        chef=chef,
        status__in=['ready', 'served', 'completed'],
        preparation_started_at__isnull=False,
        ready_at__isnull=False
    )

    if prep_times.exists():
        total_seconds = 0
        count = 0
        for order in prep_times:
            if order.ready_at and order.preparation_started_at:
                seconds = (order.ready_at -
                           order.preparation_started_at).total_seconds()
                total_seconds += seconds
                count += 1
        if count > 0:
            chef.avg_prep_time = int(
                total_seconds / count / 60)  # Convert to minutes

    # Calculate performance score for chefs
    # 50% from orders prepared (50 orders = 50 points)
    order_score = min((chef.orders_prepared / 50) * 50, 50)
    # 50% from speed (faster = higher score)
    speed_score = 0
    if chef.avg_prep_time > 0:
        # 30 min = 25 points, 15 min = 50 points, 45 min = 10 points
        speed_score = max(0, min(50, (50 - (chef.avg_prep_time - 10) * 1.5)))
    chef.performance_score = order_score + speed_score

    # Update performance history
    chef.performance_history = chef.performance_history or []
    chef.performance_history.append({
        'date': timezone.now().isoformat(),
        'orders_prepared': chef.orders_prepared,
        'avg_prep_time': chef.avg_prep_time,
        'performance_score': chef.performance_score
    })
    chef.performance_history = chef.performance_history[-30:]

    chef.save(update_fields=[
        'orders_prepared', 'avg_prep_time',
        'performance_score', 'performance_history'
    ])


@receiver(pre_save, sender=Order)
def track_order_status_changes(sender, instance, **kwargs):
    """
    Track when order status changes to trigger performance updates.
    This is a pre-save hook to detect status changes.
    """
    if not instance.pk:
        return  # New order, skip

    try:
        old = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    # If order is marked as ready, track chef
    if old.status != 'ready' and instance.status == 'ready':
        # Chef should be set before saving
        pass

    # If order is marked as completed, performance will be updated
    # in the post_save signal
