# menu/business_logic.py
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Avg, F, Q
from decimal import Decimal


class MenuBusinessLogic:
    @staticmethod
    def get_best_sellers(restaurant_id, days=30, limit=10):
        """Get top selling menu items for a restaurant"""
        from .models import MenuItem

        cutoff_date = timezone.now() - timedelta(days=days)

        return MenuItem.objects.filter(
            category__restaurant_id=restaurant_id,
            orderitem__order__completed_at__gte=cutoff_date
        ).annotate(
            recent_sales=Sum('orderitem__quantity'),
            recent_revenue=Sum('orderitem__total_price'),
            recent_profit=Sum(F('orderitem__total_price') -
                              (F('cost_price') * F('orderitem__quantity')))
        ).order_by('-recent_sales')[:limit]

    @staticmethod
    def calculate_daily_profit(restaurant_id, date=None):
        """Calculate daily profit for restaurant"""
        from ..tables.models import Order, OrderItem

        if not date:
            date = timezone.now().date()

        orders = Order.objects.filter(
            table__branch__restaurant_id=restaurant_id,
            status='completed',
            completed_at__date=date
        )

        total_revenue = Decimal('0')
        total_cost = Decimal('0')

        for order in orders:
            for item in order.items.all():
                total_revenue += item.total_price
                if item.menu_item.cost_price:
                    total_cost += item.menu_item.cost_price * item.quantity

        return {
            'date': date,
            'total_orders': orders.count(),
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_profit': total_revenue - total_cost,
            'profit_margin': ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0
        }

    @staticmethod
    def get_profit_by_item(restaurant_id, days=7):
        """Get profit breakdown by menu item"""
        from .models import MenuItem

        cutoff_date = timezone.now() - timedelta(days=days)

        items = MenuItem.objects.filter(
            category__restaurant_id=restaurant_id,
            orderitem__order__completed_at__gte=cutoff_date
        ).annotate(
            units_sold=Sum('orderitem__quantity'),
            revenue=Sum('orderitem__total_price'),
            cost=Sum(F('cost_price') * F('orderitem__quantity')),
            profit=Sum(F('orderitem__total_price') -
                       (F('cost_price') * F('orderitem__quantity')))
        ).filter(units_sold__gt=0).order_by('-profit')

        return items

    @staticmethod
    def get_low_profit_items(restaurant_id, threshold=20):
        """Get items with profit margin below threshold"""
        from .models import MenuItem

        return MenuItem.objects.filter(
            category__restaurant_id=restaurant_id,
            profit_margin__lt=threshold,
            is_available=True
        ).order_by('profit_margin')

    @staticmethod
    def update_all_profit_margins(restaurant_id):
        """Update profit margins for all menu items"""
        from .models import MenuItem

        items = MenuItem.objects.filter(category__restaurant_id=restaurant_id)
        for item in items:
            if item.price > 0 and item.cost_price >= 0:
                profit_amount = item.price - item.cost_price
                item.profit_margin = (profit_amount / item.price) * 100
                item.save(update_fields=['profit_margin', 'updated_at'])

        return items.count()
