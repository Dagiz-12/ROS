# inventory/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from tables.models import Order, OrderItem
from .models import StockItem, StockTransaction, Recipe, StockAlert
from decimal import Decimal


@receiver(post_save, sender=Order)
def update_inventory_on_order_status_change(sender, instance, created, **kwargs):
    """
    Automatically deduct inventory when an order status changes to 'completed'
    Only deduct once per order (check inventory_deducted flag)
    """
    if instance.status == 'completed' and not instance.inventory_deducted:
        deduct_inventory_from_order(instance)


def deduct_inventory_from_order(order):
    """
    Deduct inventory for all items in an order
    """
    try:
        order_items = order.items.all()
        deductions_made = False

        for order_item in order_items:
            # Get recipes for this menu item
            recipes = Recipe.objects.filter(menu_item=order_item.menu_item)

            for recipe in recipes:
                # Calculate total quantity needed (including waste factor)
                total_quantity_needed = recipe.adjusted_quantity * order_item.quantity

                # Deduct from stock
                stock_item = recipe.stock_item
                if stock_item.current_quantity >= total_quantity_needed:
                    # Use the consume method which handles transactions and alerts
                    stock_item.consume(
                        quantity=total_quantity_needed,
                        reason=f'Order #{order.order_number} - {order_item.menu_item.name} (x{order_item.quantity})',
                        user=order.waiter
                    )
                    deductions_made = True
                else:
                    # Create alert for insufficient stock
                    StockAlert.objects.create(
                        stock_item=stock_item,
                        alert_type='low_stock',
                        message=f'Insufficient {stock_item.name} for Order #{order.order_number}. '
                        f'Needed: {total_quantity_needed:.3f} {stock_item.unit}, '
                        f'Available: {stock_item.current_quantity:.3f} {stock_item.unit}',
                        restaurant=order.table.branch.restaurant,
                        branch=order.table.branch
                    )

        if deductions_made:
            # Mark order as inventory deducted
            order.inventory_deducted = True
            order.save(update_fields=['inventory_deducted'])

    except Exception as e:
        # Log error but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deducting inventory for order {order.id}: {e}")


@receiver(post_save, sender=OrderItem)
def update_menu_item_sales_on_order_completion(sender, instance, created, **kwargs):
    """
    When an order item is saved and its order is completed,
    update the menu item sales statistics
    """
    if instance.order.status == 'completed':
        instance.menu_item.update_sales(instance.quantity)


@receiver(post_save, sender=Recipe)
def update_menu_item_cost_on_recipe_change(sender, instance, created, **kwargs):
    """
    When a recipe is created or updated, update the menu item's cost_price
    """
    instance.update_menu_item_cost()
