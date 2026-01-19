# profit_intelligence/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='tables.Order')
def update_profit_on_order_completion(sender, instance, created, **kwargs):
    """
    Update profit calculations when order is completed
    """
    from .business_logic import ProfitCalculator

    try:
        # Only update when order is marked as completed
        if instance.status == 'completed' and instance.completed_at:
            logger.info(
                f"Order {instance.order_number} completed, updating profit calculations")

            # Calculate profit for this date
            ProfitCalculator.calculate_daily_profit(
                date=instance.completed_at.date(),
                restaurant=instance.table.branch.restaurant,
                branch=instance.table.branch
            )

    except Exception as e:
        logger.error(
            f"Error updating profit on order completion: {str(e)}", exc_info=True)


@receiver(post_save, sender='inventory.StockTransaction')
def update_profit_on_waste(sender, instance, created, **kwargs):
    """
    Update profit calculations when waste is recorded
    """
    from .business_logic import ProfitCalculator

    try:
        # Only update for waste transactions
        if instance.transaction_type == 'waste' and instance.transaction_date:
            logger.info(
                f"Waste recorded for {instance.stock_item.name}, updating profit")

            # Calculate profit for this date
            ProfitCalculator.calculate_daily_profit(
                date=instance.transaction_date,
                restaurant=instance.restaurant,
                branch=instance.branch
            )

    except Exception as e:
        logger.error(
            f"Error updating profit on waste: {str(e)}", exc_info=True)


@receiver(post_save, sender='menu.MenuItem')
def update_profit_on_price_change(sender, instance, created, **kwargs):
    """
    Update profit calculations when menu item price changes
    """
    from .business_logic import ProfitCalculator
    from .models import MenuItemPerformance

    try:
        # Only if price changed (not on creation)
        if not created and hasattr(instance, '_old_price'):
            old_price = instance._old_price
            new_price = instance.price

            if old_price != new_price:
                logger.info(
                    f"Menu item {instance.name} price changed from {old_price} to {new_price}")

                # Update recent performance records (last 7 days)
                week_ago = timezone.now().date() - timedelta(days=7)
                performances = MenuItemPerformance.objects.filter(
                    menu_item=instance,
                    date__gte=week_ago
                )

                for performance in performances:
                    # Recalculate profit margin with new price
                    if performance.quantity_sold > 0:
                        revenue = new_price * performance.quantity_sold
                        gross_profit = revenue - performance.ingredient_cost
                        net_profit = revenue - performance.total_cost

                        if revenue > 0:
                            profit_margin = (net_profit / revenue) * 100

                            performance.revenue = revenue
                            performance.gross_profit = gross_profit
                            performance.net_profit = net_profit
                            performance.profit_margin = profit_margin
                            performance.save(update_fields=[
                                'revenue', 'gross_profit', 'net_profit',
                                'profit_margin', 'calculated_at'
                            ])

    except Exception as e:
        logger.error(
            f"Error updating profit on price change: {str(e)}", exc_info=True)


@receiver(pre_save, sender='menu.MenuItem')
def store_old_price(sender, instance, **kwargs):
    """
    Store old price before save to detect changes
    """
    try:
        if instance.pk:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_price = old_instance.price
        else:
            instance._old_price = None
    except sender.DoesNotExist:
        instance._old_price = None


@receiver(post_save, sender='inventory.Recipe')
def update_profit_on_recipe_change(sender, instance, created, **kwargs):
    """
    Update profit calculations when recipe changes
    """
    from .business_logic import ProfitCalculator
    from .models import MenuItemPerformance

    try:
        menu_item = instance.menu_item
        logger.info(
            f"Recipe changed for {menu_item.name}, updating profit calculations")

        # Update recent performance records (last 7 days)
        week_ago = timezone.now().date() - timedelta(days=7)
        performances = MenuItemPerformance.objects.filter(
            menu_item=menu_item,
            date__gte=week_ago
        )

        for performance in performances:
            # Recalculate with updated cost
            if performance.quantity_sold > 0:
                # Get updated ingredient cost from menu item
                ingredient_cost = menu_item.cost_price * performance.quantity_sold

                performance.ingredient_cost = ingredient_cost
                performance.total_cost = ingredient_cost + performance.labor_cost_share
                performance.gross_profit = performance.revenue - ingredient_cost
                performance.net_profit = performance.revenue - performance.total_cost

                if performance.revenue > 0:
                    performance.profit_margin = (
                        performance.net_profit / performance.revenue) * 100

                performance.save(update_fields=[
                    'ingredient_cost', 'total_cost', 'gross_profit',
                    'net_profit', 'profit_margin', 'calculated_at'
                ])

        # Also update profit aggregations for affected dates
        dates_to_update = performances.values_list(
            'date', flat=True).distinct()

        for date in dates_to_update:
            ProfitCalculator.calculate_daily_profit(
                date=date,
                restaurant=menu_item.category.restaurant,
                branch=None  # Will update for all branches
            )

    except Exception as e:
        logger.error(
            f"Error updating profit on recipe change: {str(e)}", exc_info=True)


@receiver(post_save, sender='waste_tracker.WasteRecord')
def update_profit_on_waste_record(sender, instance, created, **kwargs):
    """
    Update profit calculations when waste is recorded
    """
    from .business_logic import ProfitCalculator

    try:
        if instance.status == 'approved' and instance.created_at:
            logger.info(f"Waste record approved, updating profit")

            # Calculate profit for this date
            ProfitCalculator.calculate_daily_profit(
                date=instance.created_at.date(),
                restaurant=instance.restaurant,
                branch=instance.branch
            )

    except Exception as e:
        logger.error(
            f"Error updating profit on waste record: {str(e)}", exc_info=True)
