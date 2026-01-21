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
from restaurants.models import Branch


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
            ingredient_cost = Decimal('0.00')
            for recipe in recipes:
                # Handle None ingredient_cost
                recipe_cost = recipe.ingredient_cost or Decimal('0.00')
                ingredient_cost += recipe_cost

            # Calculate profit metrics
            revenue = item.total_revenue or Decimal('0.00')
            sold_count = item.sold_count or 0
            cost_of_goods = ingredient_cost * Decimal(str(sold_count))
            gross_profit = revenue - cost_of_goods
            profit_margin = (gross_profit / revenue *
                             100) if revenue > 0 else Decimal('0.00')

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
                'category': item.category.name if item.category else 'Uncategorized',
                'price': float(item.price or Decimal('0.00')),
                'cost_price': float(item.cost_price or Decimal('0.00')),
                'ingredient_cost': float(ingredient_cost),
                'sold_count': sold_count,
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

    @staticmethod
    def get_profit_dashboard(user=None, view_level='branch', branch_id=None):
        """
        Get profit dashboard with scope awareness

        Parameters:
        - user: Authenticated user
        - view_level: 'branch' | 'restaurant' (what data to show)
        - branch_id: Specific branch for detailed view (optional)
        """

        if not user or not hasattr(user, 'restaurant') or not user.restaurant:
            return {
                'success': False,
                'error': 'User not assigned to a restaurant'
            }

        # Determine which branches to include
        accessible_branches = user.get_accessible_branches()

        if not accessible_branches.exists():
            return {
                'success': True,
                'message': 'No branches accessible',
                'view': {
                    'level': view_level,
                    'restaurant': user.restaurant.name,
                    'branch': 'No access',
                    'label': 'No accessible branches'
                },
                'today': BusinessIntelligenceAPI._create_empty_daily_profit(),
                'yesterday': BusinessIntelligenceAPI._create_empty_daily_profit(),
                'daily_change': BusinessIntelligenceAPI._create_empty_daily_change(),
                'trend': BusinessIntelligenceAPI._create_empty_trend(),
                'menu_analysis': BusinessIntelligenceAPI._create_empty_menu_analysis(),
                'issues': BusinessIntelligenceAPI._create_empty_issues(),
                'waste': BusinessIntelligenceAPI._create_empty_waste(),
                'kpis': BusinessIntelligenceAPI._create_empty_kpis()
            }

        # Handle specific branch request
        if view_level == 'branch' and branch_id:
            # Verify user can access this specific branch
            try:
                branch = Branch.objects.get(id=branch_id)
                if not user.can_access_branch(branch):
                    return {
                        'success': False,
                        'error': 'Access denied to this branch'
                    }
                restaurant_filter = {'restaurant': user.restaurant}
                branch_filter = {'branch': branch}
                view_label = f"{branch.name}"

            except Branch.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Branch not found'
                }

        elif view_level == 'branch':
            # Default to user's branch or first accessible branch
            if user.branch and user.can_access_branch(user.branch):
                branch = user.branch
            else:
                branch = accessible_branches.first()

            restaurant_filter = {'restaurant': user.restaurant}
            branch_filter = {'branch': branch}
            view_label = f"{branch.name}"

        elif view_level == 'restaurant':
            # Show aggregated data for all accessible branches
            if user.role == 'manager' and user.manager_scope == 'selected':
                # Show only selected branches
                branch_ids = list(
                    accessible_branches.values_list('id', flat=True))
                restaurant_filter = {'restaurant': user.restaurant}
                branch_filter = {'branch__id__in': branch_ids}
                branch_count = accessible_branches.count()
                view_label = f"{branch_count} Selected Branches"
            else:
                # Show all branches in restaurant
                restaurant_filter = {'restaurant': user.restaurant}
                branch_filter = {}  # No branch filter = all branches
                branch_count = accessible_branches.count()
                view_label = f"All {user.restaurant.name} Branches"

        else:
            return {
                'success': False,
                'error': f'Invalid view level: {view_level}'
            }

        view_info = {
            'level': view_level,
            'restaurant': user.restaurant.name,
            'branch': branch.name if view_level == 'branch' and branch else 'Multiple',
            'label': view_label,
            'accessible_branch_count': accessible_branches.count(),
            'user_scope': user.effective_scope if hasattr(user, 'effective_scope') else 'branch'
        }

        # Continue with existing calculations using filters...
        # ... [rest of your existing code with filters applied]

        # Get data with appropriate filters
        today_profit = BusinessIntelligenceAPI._get_daily_profit_with_filters(
            timezone.now().date(), restaurant_filter, branch_filter
        )

        yesterday_profit = BusinessIntelligenceAPI._get_daily_profit_with_filters(
            timezone.now().date() - timedelta(days=1), restaurant_filter, branch_filter
        )

        # 30-day trend with filters
        trend = BusinessIntelligenceAPI._get_profit_trend_with_filters(
            30, restaurant_filter, branch_filter
        )

        # Menu item analysis
        menu_items = BusinessIntelligenceAPI._get_menu_items_with_filters(
            restaurant_filter, branch_filter, view_level
        )

        top_5_profitable = sorted(
            menu_items, key=lambda x: x['gross_profit'], reverse=True)[:5]
        bottom_5_profitable = sorted(
            menu_items, key=lambda x: x['profit_margin'])[:5]

        # Profit issues
        issues = BusinessIntelligenceAPI._identify_profit_issues_with_filters(
            menu_items
        )

        # Waste analysis
        waste = BusinessIntelligenceAPI._analyze_waste_with_filters(
            30, restaurant_filter, branch_filter
        )

        # Branch breakdown (only for restaurant-level view)
        branch_breakdown = None
        if view_level == 'restaurant':
            branch_breakdown = BusinessIntelligenceAPI._get_branch_breakdown(
                user.restaurant
            )

        # Calculate KPIs
        kpis = BusinessIntelligenceAPI._calculate_kpis(
            today_profit, waste, issues, menu_items
        )

        return {
            'success': True,
            'timestamp': timezone.now().isoformat(),
            'view': view_info,
            'today': today_profit,
            'yesterday': yesterday_profit,
            'daily_change': BusinessIntelligenceAPI._calculate_daily_change(
                today_profit, yesterday_profit
            ),
            'trend': trend,
            'menu_analysis': {
                'total_items': len(menu_items),
                'top_profitable': top_5_profitable,
                'bottom_profitable': bottom_5_profitable,
                'avg_profit_margin': sum(item['profit_margin'] for item in menu_items) / len(menu_items) if menu_items else 0
            },
            'issues': issues,
            'waste': waste,
            'branch_breakdown': branch_breakdown,
            'kpis': kpis
        }

    # Add these helper methods for empty data

    def _create_empty_daily_profit():
        return {
            'date': timezone.now().date().isoformat(),
            'summary': {
                'total_revenue': 0.0,
                'ingredient_cost': 0.0,
                'gross_profit': 0.0,
                'profit_margin': 0.0,
                'order_count': 0,
                'average_order_value': 0.0
            },
            'top_items': []
        }

    def _create_empty_daily_change():
        return {
            'revenue': 0,
            'profit': 0,
            'margin': 0,
            'orders': 0,
            'percentage_change': {
                'revenue': 0,
                'profit': 0
            }
        }

    def _create_empty_trend():
        return {
            'period': {
                'start_date': (timezone.now().date() - timedelta(days=30)).isoformat(),
                'end_date': timezone.now().date().isoformat(),
                'days': 30
            },
            'daily_data': [],
            'weekly_data': [],
            'summary': {
                'total_revenue': 0,
                'total_cost': 0,
                'total_profit': 0,
                'avg_daily_profit': 0,
                'avg_margin': 0
            }
        }

    def _create_empty_menu_analysis():
        return {
            'total_items': 0,
            'top_profitable': [],
            'bottom_profitable': [],
            'avg_profit_margin': 0
        }

    def _create_empty_issues():
        return {
            'issues': {
                'loss_makers': [],
                'low_margin': [],
                'high_cost_items': [],
                'best_performers': [],
                'worst_performers': []
            },
            'suggestions': [],
            'summary': {
                'total_items': 0,
                'loss_makers_count': 0,
                'low_margin_count': 0,
                'high_margin_count': 0
            }
        }

    def _create_empty_waste():
        return {
            'period': {
                'days': 30,
                'start_date': (timezone.now().date() - timedelta(days=30)).isoformat(),
                'end_date': timezone.now().date().isoformat()
            },
            'summary': {
                'total_waste_cost': 0.0,
                'total_waste_quantity': 0.0,
                'waste_percentage': 0.0,
                'avg_daily_waste': 0.0,
                'transaction_count': 0
            },
            'reduction_target': {
                'current': 0.0,
                'target': 5.0,
                'savings_potential': 0.0
            }
        }

    def _create_empty_kpis():
        return {
            'daily_profit': 0.0,
            'profit_margin': 0.0,
            'waste_percentage': 0.0,
            'avg_order_value': 0.0,
            'items_with_issues': 0,
            'total_menu_items': 0,
            'top_seller_profit_margin': 0.0,
            'waste_cost_per_order': 0.0
        }

    @staticmethod
    def _get_daily_profit_with_filters(date, restaurant_filter, branch_filter):
        """
        Get daily profit with filters
        CORRECTED: Now uses proper table->branch->restaurant relationship
        """
        print(f"DEBUG: Getting daily profit for date: {date}")
        print(f"DEBUG: Restaurant filter: {restaurant_filter}")
        print(f"DEBUG: Branch filter: {branch_filter}")

        # Start with base query
        orders = Order.objects.filter(
            status='completed',
            completed_at__date=date,
            is_paid=True
        )

        # Apply restaurant filter through table -> branch -> restaurant
        if 'restaurant' in restaurant_filter:
            restaurant = restaurant_filter['restaurant']
            print(f"DEBUG: Filtering by restaurant: {restaurant.name}")
            orders = orders.filter(
                table__branch__restaurant=restaurant
            )

        # Apply branch filter
        if 'branch' in branch_filter:
            branch = branch_filter['branch']
            print(f"DEBUG: Filtering by branch: {branch.name}")
            orders = orders.filter(
                table__branch=branch
            )

        print(f"DEBUG: Found {orders.count()} orders")

        total_revenue = orders.aggregate(total=Sum('total_amount'))[
            'total'] or Decimal('0.00')
        order_count = orders.count()

        # Calculate ingredient costs
        ingredient_cost = Decimal('0.00')
        order_items = []

        for order in orders:
            # Get all items for this order
            items = order.items.all().select_related('menu_item')
            order_items.extend(items)

            for order_item in items:
                if order_item.menu_item:
                    # Get recipe for this menu item
                    recipes = Recipe.objects.filter(
                        menu_item=order_item.menu_item)
                    item_ingredient_cost = Decimal('0.00')

                    for recipe in recipes:
                        if recipe.stock_item and recipe.stock_item.cost_per_unit:
                            item_ingredient_cost += recipe.stock_item.cost_per_unit * \
                                recipe.quantity_required * order_item.quantity

                    ingredient_cost += item_ingredient_cost

        gross_profit = total_revenue - ingredient_cost
        profit_margin = (gross_profit / total_revenue *
                         100) if total_revenue > 0 else Decimal('0.00')

        # Get top selling items
        top_items = []
        if order_items:
            # Group by menu item
            from collections import defaultdict
            item_totals = defaultdict(
                lambda: {'quantity': 0, 'revenue': Decimal('0.00')})

            for item in order_items:
                key = (item.menu_item.name,
                       item.menu_item.category.name if item.menu_item.category else 'Uncategorized')
                item_totals[key]['quantity'] += item.quantity
                item_totals[key]['revenue'] += item.unit_price * item.quantity

            # Convert to list and sort
            top_items_list = []
            for (item_name, category_name), totals in item_totals.items():
                top_items_list.append({
                    'menu_item__name': item_name,
                    'menu_item__category__name': category_name,
                    'quantity_sold': totals['quantity'],
                    'revenue': totals['revenue'],
                    'avg_price': totals['revenue'] / totals['quantity'] if totals['quantity'] > 0 else Decimal('0.00')
                })

            # Sort by quantity sold and take top 5
            top_items_list.sort(key=lambda x: x['quantity_sold'], reverse=True)
            top_items = top_items_list[:5]

        return {
            'date': date.isoformat(),
            'summary': {
                'total_revenue': float(total_revenue),
                'ingredient_cost': float(ingredient_cost),
                'gross_profit': float(gross_profit),
                'profit_margin': float(profit_margin),
                'order_count': order_count,
                'average_order_value': float(total_revenue / order_count) if order_count > 0 else 0
            },
            'top_items': top_items
        }

    @staticmethod
    def _get_profit_trend_with_filters(days, restaurant_filter, branch_filter):
        """
        Get profit trend with filters
        """
        print(f"DEBUG: Getting profit trend for {days} days")

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        daily_data = []
        current_date = start_date

        while current_date <= end_date:
            daily_profit = BusinessIntelligenceAPI._get_daily_profit_with_filters(
                current_date, restaurant_filter, branch_filter
            )
            daily_data.append({
                'date': current_date.isoformat(),
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

        # Calculate trend summary
        if daily_data:
            total_revenue = sum(day['revenue'] for day in daily_data)
            total_cost = sum(day['cost'] for day in daily_data)
            total_profit = sum(day['profit'] for day in daily_data)
            avg_margin = sum(day['margin']
                             for day in daily_data) / len(daily_data)
        else:
            total_revenue = 0
            total_cost = 0
            total_profit = 0
            avg_margin = 0

        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'daily_data': daily_data,
            'weekly_data': weekly_data,
            'summary': {
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'avg_daily_profit': total_profit / len(daily_data) if daily_data else 0,
                'avg_margin': avg_margin
            }
        }

    @staticmethod
    def _get_menu_items_with_filters(restaurant_filter, branch_filter, view_level):
        """
        Get menu items with appropriate filters
        """
        print(f"DEBUG: Getting menu items, view level: {view_level}")

        # Start with base queryset - menu items belong to restaurant through category
        menu_items_queryset = MenuItem.objects.select_related('category').filter(
            is_available=True
        )

        # Apply restaurant filter
        if 'restaurant' in restaurant_filter:
            restaurant = restaurant_filter['restaurant']
            menu_items_queryset = menu_items_queryset.filter(
                category__restaurant=restaurant
            )

        print(f"DEBUG: Found {menu_items_queryset.count()} menu items")

        profit_data = []

        for item in menu_items_queryset:
            # Get ingredient cost from recipes
            recipes = Recipe.objects.filter(menu_item=item)
            ingredient_cost = Decimal('0.00')
            for recipe in recipes:
                if recipe.stock_item and recipe.stock_item.cost_per_unit:
                    ingredient_cost += recipe.ingredient_cost

            # For now, use the item's total revenue (this is restaurant-wide)
            # In a more advanced version, we would filter revenue by branch
            revenue = float(item.total_revenue) if item.total_revenue else 0
            sold_count = item.sold_count or 0
            cost_of_goods = float(ingredient_cost) * sold_count
            gross_profit = revenue - cost_of_goods
            profit_margin = (gross_profit / revenue *
                             100) if revenue > 0 else 0

            profit_data.append({
                'id': item.id,
                'name': item.name,
                'category': item.category.name if item.category else 'Uncategorized',
                'price': float(item.price),
                'cost_price': float(item.cost_price),
                'ingredient_cost': float(ingredient_cost),
                'sold_count': sold_count,
                'revenue': revenue,
                'gross_profit': gross_profit,
                'profit_margin': profit_margin,
                'status': 'high_profit' if profit_margin >= 50 else
                'good_profit' if profit_margin >= 30 else
                'low_profit' if profit_margin >= 10 else
                'problem' if profit_margin > 0 else 'loss'
            })

        return sorted(profit_data, key=lambda x: x['profit_margin'], reverse=True)

    @staticmethod
    def _identify_profit_issues_with_filters(menu_items):
        """
        Identify profit issues from filtered menu items
        """
        issues = {
            'loss_makers': [item for item in menu_items if item['profit_margin'] <= 0],
            'low_margin': [item for item in menu_items if 0 < item['profit_margin'] < 15],
            'high_cost_items': sorted(menu_items, key=lambda x: x['ingredient_cost'], reverse=True)[:5],
            'best_performers': sorted(menu_items, key=lambda x: x['gross_profit'], reverse=True)[:5],
            'worst_performers': sorted(menu_items, key=lambda x: x['gross_profit'])[:5]
        }

        # Calculate suggested price adjustments
        suggestions = []
        for item in issues['loss_makers'] + issues['low_margin']:
            if item['profit_margin'] < 20:
                # FIX: Convert float to Decimal for multiplication
                target_cost = Decimal(str(item['ingredient_cost']))

                # Calculate price for target 50% margin
                suggested_price = target_cost * \
                    Decimal('2.0')  # For 50% margin

                # Ensure suggested price is reasonable (at least current price if already profitable)
                current_price = Decimal(str(item['price']))
                if suggested_price < current_price and item['profit_margin'] > 0:
                    suggested_price = current_price * \
                        Decimal('1.1')  # 10% increase

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
                'total_items': len(menu_items),
                'loss_makers_count': len(issues['loss_makers']),
                'low_margin_count': len(issues['low_margin']),
                'high_margin_count': len([i for i in menu_items if i['profit_margin'] >= 40])
            }
        }

    @staticmethod
    def _analyze_waste_with_filters(days, restaurant_filter, branch_filter):
        """
        Analyze waste with filters
        """
        start_date = timezone.now() - timedelta(days=days)

        # Start with base query
        waste_transactions = StockTransaction.objects.filter(
            transaction_type='waste',
            created_at__gte=start_date
        )

        # Apply restaurant filter
        if 'restaurant' in restaurant_filter:
            restaurant = restaurant_filter['restaurant']
            waste_transactions = waste_transactions.filter(
                restaurant=restaurant
            )

        # Apply branch filter
        if 'branch' in branch_filter:
            branch = branch_filter['branch']
            waste_transactions = waste_transactions.filter(
                branch=branch
            )

        total_waste_cost = waste_transactions.aggregate(
            total=Sum('total_cost')
        )['total'] or Decimal('0.00')

        total_waste_quantity = waste_transactions.aggregate(
            total=Sum('quantity')
        )['total'] or Decimal('0.00')

        # Calculate waste percentage
        # Get usage transactions for the same filters
        usage_transactions = StockTransaction.objects.filter(
            transaction_type='usage',
            created_at__gte=start_date
        )

        if 'restaurant' in restaurant_filter:
            usage_transactions = usage_transactions.filter(
                restaurant=restaurant_filter['restaurant']
            )

        if 'branch' in branch_filter:
            usage_transactions = usage_transactions.filter(
                branch=branch_filter['branch']
            )

        total_usage_cost = usage_transactions.aggregate(
            total=Sum('total_cost')
        )['total'] or Decimal('0.00')

        total_cost = total_usage_cost + total_waste_cost
        waste_percentage = (total_waste_cost / total_cost *
                            100) if total_cost > 0 else 0

        return {
            'period': {
                'days': days,
                'start_date': start_date.date().isoformat(),
                'end_date': timezone.now().date().isoformat()
            },
            'summary': {
                'total_waste_cost': float(total_waste_cost),
                'total_waste_quantity': float(total_waste_quantity),
                'waste_percentage': float(waste_percentage),
                'avg_daily_waste': float(total_waste_cost / days),
                'transaction_count': waste_transactions.count()
            },
            'reduction_target': {
                'current': float(waste_percentage),
                'target': 5.0,
                'savings_potential': float(total_waste_cost * Decimal('0.5'))
            }
        }

    @staticmethod
    def _get_branch_breakdown(restaurant):
        """
        Get breakdown by branch for restaurant-level view
        """
        branches = restaurant.branches.all()
        branch_data = []

        for branch in branches:
            branch_filter = {'branch': branch}
            restaurant_filter = {'restaurant': restaurant}

            # Today's profit for this branch
            today_profit = BusinessIntelligenceAPI._get_daily_profit_with_filters(
                timezone.now().date(), restaurant_filter, branch_filter
            )

            # Waste for this branch (last 30 days)
            waste = BusinessIntelligenceAPI._analyze_waste_with_filters(
                30, restaurant_filter, branch_filter
            )

            branch_data.append({
                'id': branch.id,
                'name': branch.name,
                'location': branch.location,
                'performance': {
                    'revenue': today_profit['summary']['total_revenue'],
                    'profit': today_profit['summary']['gross_profit'],
                    'margin': today_profit['summary']['profit_margin'],
                    'orders': today_profit['summary']['order_count'],
                    'waste_percentage': waste['summary']['waste_percentage']
                }
            })

        return branch_data

    @staticmethod
    def _calculate_daily_change(today_data, yesterday_data):
        """
        Calculate daily change between today and yesterday
        """
        return {
            'revenue': today_data['summary']['total_revenue'] - yesterday_data['summary']['total_revenue'],
            'profit': today_data['summary']['gross_profit'] - yesterday_data['summary']['gross_profit'],
            'margin': today_data['summary']['profit_margin'] - yesterday_data['summary']['profit_margin'],
            'orders': today_data['summary']['order_count'] - yesterday_data['summary']['order_count'],
            'percentage_change': {
                'revenue': ((today_data['summary']['total_revenue'] - yesterday_data['summary']['total_revenue']) / yesterday_data['summary']['total_revenue'] * 100) if yesterday_data['summary']['total_revenue'] > 0 else 0,
                'profit': ((today_data['summary']['gross_profit'] - yesterday_data['summary']['gross_profit']) / abs(yesterday_data['summary']['gross_profit']) * 100) if yesterday_data['summary']['gross_profit'] != 0 else 0
            }
        }

    @staticmethod
    def _calculate_kpis(today_profit, waste, issues, menu_items):
        """
        Calculate Key Performance Indicators
        """
        return {
            'daily_profit': today_profit['summary']['gross_profit'],
            'profit_margin': today_profit['summary']['profit_margin'],
            'waste_percentage': waste['summary']['waste_percentage'],
            'avg_order_value': today_profit['summary']['average_order_value'],
            'items_with_issues': issues['summary']['loss_makers_count'] + issues['summary']['low_margin_count'],
            'total_menu_items': len(menu_items),
            'top_seller_profit_margin': max([item['profit_margin'] for item in menu_items]) if menu_items else 0,
            'waste_cost_per_order': waste['summary']['total_waste_cost'] / today_profit['summary']['order_count'] if today_profit['summary']['order_count'] > 0 else 0
        }
