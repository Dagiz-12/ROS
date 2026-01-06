# inventory/business_logic.py
from django.db.models import Sum, Count, Avg, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import StockItem, StockTransaction, Recipe, StockAlert
from menu.models import MenuItem, Category
from tables.models import Order, OrderItem


class ProfitCalculator:
    """
    Core profit calculation engine
    """

    @staticmethod
    def calculate_menu_item_profit(menu_item_id=None):
        """
        Calculate profit for a specific menu item or all items
        """
        if menu_item_id:
            items = MenuItem.objects.filter(id=menu_item_id)
        else:
            items = MenuItem.objects.all()

        profit_data = []

        for item in items:
            # Get ingredient cost from recipes
            recipes = Recipe.objects.filter(menu_item=item)
            ingredient_cost = sum(recipe.ingredient_cost for recipe in recipes)

            # Calculate profit metrics
            revenue = item.total_revenue
            cost_of_goods = ingredient_cost * item.sold_count if item.sold_count > 0 else 0
            gross_profit = revenue - cost_of_goods
            profit_margin = (gross_profit / revenue *
                             100) if revenue > 0 else 0

            # Get recent sales trend (last 7 days)
            week_ago = timezone.now() - timedelta(days=7)
            recent_orders = OrderItem.objects.filter(
                menu_item=item,
                order__completed_at__gte=week_ago,
                order__status='completed'
            )
            recent_sales = recent_orders.aggregate(
                total=Sum('quantity'))['total'] or 0

            profit_data.append({
                'id': item.id,
                'name': item.name,
                'category': item.category.name,
                'price': float(item.price),
                'cost_price': float(item.cost_price),
                'ingredient_cost': float(ingredient_cost),
                'sold_count': item.sold_count,
                'revenue': float(revenue),
                'gross_profit': float(gross_profit),
                'profit_margin': float(profit_margin),
                'recent_sales': recent_sales,
                'status': 'high_profit' if profit_margin >= 50 else
                'good_profit' if profit_margin >= 30 else
                'low_profit' if profit_margin >= 10 else
                'problem' if profit_margin > 0 else 'loss'
            })

        return sorted(profit_data, key=lambda x: x['profit_margin'], reverse=True)

    @staticmethod
    def calculate_daily_profit(date=None):
        """
        Calculate profit for a specific date or today
        """
        if not date:
            date = timezone.now().date()

        # Get completed orders for the date
        orders = Order.objects.filter(
            status='completed',
            completed_at__date=date
        )

        total_revenue = orders.aggregate(total=Sum('total_amount'))[
            'total'] or Decimal('0.00')
        order_count = orders.count()

        # Calculate ingredient costs for these orders
        ingredient_cost = Decimal('0.00')
        for order in orders:
            for order_item in order.items.all():
                recipes = Recipe.objects.filter(menu_item=order_item.menu_item)
                item_ingredient_cost = sum(
                    recipe.ingredient_cost for recipe in recipes)
                ingredient_cost += item_ingredient_cost * order_item.quantity

        gross_profit = total_revenue - ingredient_cost
        profit_margin = (gross_profit / total_revenue *
                         100) if total_revenue > 0 else 0

        # Get top selling items for the day
        order_items = OrderItem.objects.filter(
            order__status='completed',
            order__completed_at__date=date
        )

        top_items = order_items.values(
            'menu_item__name',
            'menu_item__category__name'
        ).annotate(
            quantity_sold=Sum('quantity'),
            revenue=Sum(F('unit_price') * F('quantity'),
                        output_field=DecimalField()),
            avg_price=Avg('unit_price')
        ).order_by('-quantity_sold')[:5]

        return {
            'date': date,
            'summary': {
                'total_revenue': float(total_revenue),
                'ingredient_cost': float(ingredient_cost),
                'gross_profit': float(gross_profit),
                'profit_margin': float(profit_margin),
                'order_count': order_count,
                'average_order_value': float(total_revenue / order_count) if order_count > 0 else 0
            },
            'top_items': list(top_items)
        }

    @staticmethod
    def calculate_profit_trend(days=30):
        """
        Calculate profit trend over a period
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        daily_data = []

        current_date = start_date
        while current_date <= end_date:
            daily_profit = ProfitCalculator.calculate_daily_profit(
                current_date)
            daily_data.append({
                'date': current_date,
                'revenue': daily_profit['summary']['total_revenue'],
                'cost': daily_profit['summary']['ingredient_cost'],
                'profit': daily_profit['summary']['gross_profit'],
                'margin': daily_profit['summary']['profit_margin'],
                'orders': daily_profit['summary']['order_count']
            })
            current_date += timedelta(days=1)

        # Calculate weekly aggregates
        weekly_data = []
        for i in range(0, len(daily_data), 7):
            week_slice = daily_data[i:i+7]
            if week_slice:
                weekly_data.append({
                    'week_start': week_slice[0]['date'],
                    'week_end': week_slice[-1]['date'],
                    'revenue': sum(day['revenue'] for day in week_slice),
                    'cost': sum(day['cost'] for day in week_slice),
                    'profit': sum(day['profit'] for day in week_slice),
                    'avg_margin': sum(day['margin'] for day in week_slice) / len(week_slice) if week_slice else 0,
                    'total_orders': sum(day['orders'] for day in week_slice)
                })

        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days
            },
            'daily_data': daily_data,
            'weekly_data': weekly_data,
            'summary': {
                'total_revenue': sum(day['revenue'] for day in daily_data),
                'total_cost': sum(day['cost'] for day in daily_data),
                'total_profit': sum(day['profit'] for day in daily_data),
                'avg_daily_profit': sum(day['profit'] for day in daily_data) / len(daily_data) if daily_data else 0,
                'avg_margin': sum(day['margin'] for day in daily_data) / len(daily_data) if daily_data else 0
            }
        }

    @staticmethod
    def identify_profit_issues():
        """
        Identify menu items with profit issues
        """
        all_items = ProfitCalculator.calculate_menu_item_profit()

        issues = {
            'loss_makers': [item for item in all_items if item['profit_margin'] <= 0],
            'low_margin': [item for item in all_items if 0 < item['profit_margin'] < 15],
            'high_cost_items': sorted(all_items, key=lambda x: x['ingredient_cost'], reverse=True)[:5],
            'best_performers': sorted(all_items, key=lambda x: x['gross_profit'], reverse=True)[:5],
            'worst_performers': sorted(all_items, key=lambda x: x['gross_profit'])[:5]
        }

        # Calculate suggested price adjustments
        suggestions = []
        for item in issues['low_margin'] + issues['loss_makers']:
            if item['profit_margin'] < 20:
                suggested_price = item['ingredient_cost'] * \
                    Decimal('1.5')  # 50% margin
                suggestions.append({
                    'item_id': item['id'],
                    'item_name': item['name'],
                    'current_price': item['price'],
                    'suggested_price': float(suggested_price),
                    'current_margin': item['profit_margin'],
                    'projected_margin': 50.0,
                    'reason': 'Low profit margin' if item['profit_margin'] > 0 else 'Selling at loss'
                })

        return {
            'issues': issues,
            'suggestions': suggestions,
            'summary': {
                'total_items': len(all_items),
                'loss_makers_count': len(issues['loss_makers']),
                'low_margin_count': len(issues['low_margin']),
                'high_margin_count': len([i for i in all_items if i['profit_margin'] >= 40])
            }
        }


class WasteAnalyzer:
    """
    Analyze waste patterns and costs
    """

    @staticmethod
    def analyze_waste_period(days=30):
        """
        Analyze waste over a period
        """
        start_date = timezone.now() - timedelta(days=days)

        waste_transactions = StockTransaction.objects.filter(
            transaction_type='waste',
            created_at__gte=start_date
        )

        total_waste_cost = waste_transactions.aggregate(
            total=Sum('total_cost')
        )['total'] or Decimal('0.00')

        total_waste_quantity = waste_transactions.aggregate(
            total=Sum('quantity')
        )['total'] or Decimal('0.00')

        # Waste by category
        waste_by_category = waste_transactions.values(
            'stock_item__category'
        ).annotate(
            total_cost=Sum('total_cost'),
            total_quantity=Sum('quantity'),
            transaction_count=Count('id')
        ).order_by('-total_cost')

        # Waste reasons analysis
        waste_reasons = {}
        for transaction in waste_transactions.exclude(reason=''):
            reason = transaction.reason.lower()
            key = 'other'

            if 'spoiled' in reason or 'expired' in reason:
                key = 'spoilage'
            elif 'overcooked' in reason or 'burnt' in reason:
                key = 'preparation_error'
            elif 'spilled' in reason or 'dropped' in reason:
                key = 'accident'
            elif 'customer' in reason or 'return' in reason:
                key = 'customer_return'
            elif 'excess' in reason or 'too much' in reason:
                key = 'over_preparation'
            else:
                key = 'other'

            if key not in waste_reasons:
                waste_reasons[key] = {
                    'count': 0,
                    'total_cost': Decimal('0.00')
                }

            waste_reasons[key]['count'] += 1
            waste_reasons[key]['total_cost'] += transaction.total_cost

        # Calculate waste percentage of total cost
        total_usage_cost = StockTransaction.objects.filter(
            transaction_type='usage',
            created_at__gte=start_date
        ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

        waste_percentage = (total_waste_cost / (total_usage_cost +
                            total_waste_cost) * 100) if total_usage_cost > 0 else 0

        return {
            'period': {
                'days': days,
                'start_date': start_date.date(),
                'end_date': timezone.now().date()
            },
            'summary': {
                'total_waste_cost': float(total_waste_cost),
                'total_waste_quantity': float(total_waste_quantity),
                'waste_percentage': float(waste_percentage),
                'avg_daily_waste': float(total_waste_cost / days),
                'transaction_count': waste_transactions.count()
            },
            'by_category': list(waste_by_category),
            'by_reason': waste_reasons,
            'reduction_target': {
                'current': float(waste_percentage),
                'target': 5.0,  # Industry standard target
                # 50% reduction possible
                'savings_potential': float(total_waste_cost * Decimal('0.5'))
            }
        }


class BusinessIntelligenceAPI:
    """
    API wrapper for business intelligence functions
    """

    @staticmethod
    def get_profit_dashboard():
        """
        Get comprehensive profit dashboard data
        """
        # Today's profit
        today_profit = ProfitCalculator.calculate_daily_profit()

        # Yesterday for comparison
        yesterday = timezone.now().date() - timedelta(days=1)
        yesterday_profit = ProfitCalculator.calculate_daily_profit(yesterday)

        # 30-day trend
        trend = ProfitCalculator.calculate_profit_trend(30)

        # Menu item analysis
        menu_items = ProfitCalculator.calculate_menu_item_profit()
        top_5_profitable = sorted(
            menu_items, key=lambda x: x['gross_profit'], reverse=True)[:5]
        bottom_5_profitable = sorted(
            menu_items, key=lambda x: x['profit_margin'])[:5]

        # Profit issues
        issues = ProfitCalculator.identify_profit_issues()

        # Waste analysis
        waste = WasteAnalyzer.analyze_waste_period(30)

        return {
            'success': True,
            'timestamp': timezone.now(),
            'today': today_profit,
            'yesterday': yesterday_profit,
            'daily_change': {
                'revenue': today_profit['summary']['total_revenue'] - yesterday_profit['summary']['total_revenue'],
                'profit': today_profit['summary']['gross_profit'] - yesterday_profit['summary']['gross_profit'],
                'margin': today_profit['summary']['profit_margin'] - yesterday_profit['summary']['profit_margin']
            },
            'trend': trend,
            'menu_analysis': {
                'total_items': len(menu_items),
                'top_profitable': top_5_profitable,
                'bottom_profitable': bottom_5_profitable,
                'avg_profit_margin': sum(item['profit_margin'] for item in menu_items) / len(menu_items) if menu_items else 0
            },
            'issues': issues,
            'waste': waste,
            'kpis': {
                'daily_profit': today_profit['summary']['gross_profit'],
                'profit_margin': today_profit['summary']['profit_margin'],
                'waste_percentage': waste['summary']['waste_percentage'],
                'avg_order_value': today_profit['summary']['average_order_value'],
                'items_with_issues': issues['summary']['loss_makers_count'] + issues['summary']['low_margin_count']
            }
        }
