# profit_intelligence/business_logic.py
import logging
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from datetime import timedelta, datetime
from django.db import transaction

logger = logging.getLogger(__name__)


class ProfitCalculator:
    """
    Core profit calculation engine
    """

    @staticmethod
    def calculate_daily_profit(date, restaurant, branch=None):
        """
        Calculate profit for a specific date
        Returns: dictionary with profit metrics
        """
        try:
            from tables.models import Order, OrderItem
            from menu.models import MenuItem
            from .waste_integration import get_waste_costs_for_date
            from .models import ProfitAggregation

            logger.info(
                f"Calculating daily profit for {date} - Restaurant: {restaurant.name}, Branch: {branch.name if branch else 'All'}")

            # Get all completed orders for the date
            orders = Order.objects.filter(
                completed_at__date=date,
                is_paid=True,
                table__branch__restaurant=restaurant
            )

            if branch:
                orders = orders.filter(table__branch=branch)

            order_count = orders.count()
            logger.info(f"Found {order_count} completed orders for {date}")

            # Calculate total revenue
            total_revenue = orders.aggregate(total=Sum('total_amount'))[
                'total'] or Decimal('0.00')
            logger.info(f"Total revenue: ${total_revenue:.2f}")

            # Calculate total ingredient cost from all order items
            total_ingredient_cost = Decimal('0.00')
            ingredient_details = []

            for order in orders:
                for order_item in order.order_items.all():
                    if order_item.menu_item and order_item.menu_item.cost_price:
                        item_cost = order_item.menu_item.cost_price * order_item.quantity
                        total_ingredient_cost += item_cost

                        ingredient_details.append({
                            'menu_item': order_item.menu_item.name,
                            'quantity': order_item.quantity,
                            'cost_per_unit': float(order_item.menu_item.cost_price),
                            'total_cost': float(item_cost)
                        })

            logger.info(f"Total ingredient cost: ${total_ingredient_cost:.2f}")

            # Get waste costs from waste tracker
            waste_data = get_waste_costs_for_date(date, restaurant, branch)
            waste_cost = Decimal(str(waste_data['total_cost']))

            logger.info(f"Waste cost from waste tracker: ${waste_cost:.2f}")
            logger.info(f"Waste records found: {waste_data['record_count']}")

            # Calculate net profit
            net_profit = total_revenue - total_ingredient_cost - waste_cost

            # Calculate margins
            profit_margin = (net_profit / total_revenue *
                             100) if total_revenue > 0 else Decimal('0.00')
            waste_percentage = (waste_cost / total_ingredient_cost *
                                100) if total_ingredient_cost > 0 else Decimal('0.00')

            logger.info(f"Net profit: ${net_profit:.2f}")
            logger.info(f"Profit margin: {profit_margin:.2f}%")
            logger.info(f"Waste percentage: {waste_percentage:.2f}%")

            # Create or update ProfitAggregation
            aggregation_data = {
                'revenue': total_revenue,
                'cost_of_goods': total_ingredient_cost,
                'waste_cost': waste_cost,
                'net_profit': net_profit,
                'profit_margin': profit_margin,
                'waste_percentage': waste_percentage,
                'order_count': order_count,
                'average_order_value': total_revenue / order_count if order_count > 0 else Decimal('0.00'),
                'calculated_at': timezone.now()
            }

            # Save to database
            with transaction.atomic():
                aggregation, created = ProfitAggregation.objects.update_or_create(
                    date=date,
                    restaurant=restaurant,
                    branch=branch,
                    defaults=aggregation_data
                )

                logger.info(
                    f"Profit aggregation {'created' if created else 'updated'}: {aggregation.id}")

            # Update menu item performances for this date
            ProfitCalculator._update_menu_item_performances(
                date, restaurant, branch)

            return {
                'success': True,
                'date': date,
                'revenue': float(total_revenue),
                'ingredient_cost': float(total_ingredient_cost),
                'waste_cost': float(waste_cost),
                'net_profit': float(net_profit),
                'profit_margin': float(profit_margin),
                'waste_percentage': float(waste_percentage),
                'order_count': order_count,
                'average_order_value': float(total_revenue / order_count) if order_count > 0 else 0,
                'ingredient_details': ingredient_details[:10],  # Top 10 items
                # Top 10 waste items
                'waste_details': waste_data['details'][:10]
            }

        except Exception as e:
            logger.error(
                f"Error calculating daily profit for {date}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'date': date,
                'revenue': 0.0,
                'ingredient_cost': 0.0,
                'waste_cost': 0.0,
                'net_profit': 0.0,
                'profit_margin': 0.0,
                'waste_percentage': 0.0,
                'order_count': 0,
                'average_order_value': 0.0
            }

    @staticmethod
    def _update_menu_item_performances(date, restaurant, branch=None):
        """
        Update menu item performance records for a date
        """
        try:
            from tables.models import Order, OrderItem
            from menu.models import MenuItem
            from .models import MenuItemPerformance

            logger.info(f"Updating menu item performances for {date}")

            # Get orders for the date
            orders = Order.objects.filter(
                completed_at__date=date,
                is_paid=True,
                table__branch__restaurant=restaurant
            )

            if branch:
                orders = orders.filter(table__branch=branch)

            # Group order items by menu item
            from django.db.models import Sum
            menu_item_stats = OrderItem.objects.filter(
                order__in=orders
            ).values(
                'menu_item__id',
                'menu_item__name',
                'menu_item__category__name',
                'menu_item__price',
                'menu_item__cost_price'
            ).annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('unit_price'))
            )

            # Update performance records
            for stat in menu_item_stats:
                menu_item_id = stat['menu_item__id']
                if not menu_item_id:
                    continue

                try:
                    menu_item = MenuItem.objects.get(id=menu_item_id)

                    # Calculate costs
                    quantity = stat['total_quantity'] or 0
                    revenue = stat['total_revenue'] or Decimal('0.00')
                    ingredient_cost = (
                        menu_item.cost_price or Decimal('0.00')) * quantity

                    # Labor cost estimation (20% of ingredient cost)
                    labor_cost_share = ingredient_cost * Decimal('0.20')
                    total_cost = ingredient_cost + labor_cost_share

                    # Calculate profits
                    gross_profit = revenue - ingredient_cost
                    net_profit = revenue - total_cost
                    profit_margin = (net_profit / revenue *
                                     100) if revenue > 0 else Decimal('0.00')

                    # Create or update performance record
                    performance, created = MenuItemPerformance.objects.update_or_create(
                        date=date,
                        menu_item=menu_item,
                        restaurant=restaurant,
                        branch=branch,
                        defaults={
                            'quantity_sold': quantity,
                            'revenue': revenue,
                            'ingredient_cost': ingredient_cost,
                            'labor_cost_share': labor_cost_share,
                            'total_cost': total_cost,
                            'gross_profit': gross_profit,
                            'net_profit': net_profit,
                            'profit_margin': profit_margin,
                            'calculated_at': timezone.now()
                        }
                    )

                    if created:
                        logger.info(
                            f"Created performance record for {menu_item.name}")
                    else:
                        logger.info(
                            f"Updated performance record for {menu_item.name}")

                except MenuItem.DoesNotExist:
                    logger.warning(f"Menu item {menu_item_id} not found")
                    continue

        except Exception as e:
            logger.error(
                f"Error updating menu item performances: {str(e)}", exc_info=True)

    @staticmethod
    def calculate_profit_trend(days, restaurant, branch=None):
        """
        Calculate profit trend over a number of days
        """
        try:
            from .models import ProfitAggregation

            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days-1)

            logger.info(
                f"Calculating profit trend from {start_date} to {end_date} ({days} days)")

            # Get aggregations for the period
            aggregations = ProfitAggregation.objects.filter(
                date__gte=start_date,
                date__lte=end_date,
                restaurant=restaurant
            )

            if branch:
                aggregations = aggregations.filter(branch=branch)

            # If no aggregations exist, create them
            if not aggregations.exists():
                logger.info("No profit aggregations found, creating them...")

                current_date = start_date
                while current_date <= end_date:
                    ProfitCalculator.calculate_daily_profit(
                        date=current_date,
                        restaurant=restaurant,
                        branch=branch
                    )
                    current_date += timedelta(days=1)

                # Re-fetch aggregations
                aggregations = ProfitAggregation.objects.filter(
                    date__gte=start_date,
                    date__lte=end_date,
                    restaurant=restaurant
                )

                if branch:
                    aggregations = aggregations.filter(branch=branch)

            # Build daily data
            daily_data = []
            total_revenue = Decimal('0.00')
            total_profit = Decimal('0.00')

            # Create a dict for quick lookup
            aggregation_dict = {agg.date: agg for agg in aggregations}

            current_date = start_date
            while current_date <= end_date:
                agg = aggregation_dict.get(current_date)

                if agg:
                    daily_data.append({
                        'date': current_date.isoformat(),
                        'day_name': current_date.strftime('%a'),
                        'revenue': float(agg.revenue),
                        'cost': float(agg.cost_of_goods),
                        'waste': float(agg.waste_cost),
                        'profit': float(agg.net_profit),
                        'margin': float(agg.profit_margin),
                        'orders': agg.order_count
                    })

                    total_revenue += agg.revenue
                    total_profit += agg.net_profit
                else:
                    # Fill gaps with zeros
                    daily_data.append({
                        'date': current_date.isoformat(),
                        'day_name': current_date.strftime('%a'),
                        'revenue': 0.0,
                        'cost': 0.0,
                        'waste': 0.0,
                        'profit': 0.0,
                        'margin': 0.0,
                        'orders': 0
                    })

                current_date += timedelta(days=1)

            # Calculate summary
            avg_daily_revenue = total_revenue / days
            avg_daily_profit = total_profit / days
            avg_margin = (total_profit / total_revenue *
                          100) if total_revenue > 0 else Decimal('0.00')

            # Find best and worst days
            best_day = max(
                daily_data, key=lambda x: x['profit']) if daily_data else None
            worst_day = min(
                daily_data, key=lambda x: x['profit']) if daily_data else None

            # Calculate trend (comparing first half to second half)
            half_point = len(daily_data) // 2
            first_half_profit = sum(day['profit']
                                    for day in daily_data[:half_point])
            second_half_profit = sum(
                day['profit'] for day in daily_data[half_point:]) if half_point > 0 else 0

            trend_direction = 'up' if second_half_profit > first_half_profit else 'down' if second_half_profit < first_half_profit else 'stable'
            trend_percentage = abs((second_half_profit - first_half_profit) /
                                   first_half_profit * 100) if first_half_profit > 0 else 0

            return {
                'success': True,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'daily_data': daily_data,
                'summary': {
                    'total_revenue': float(total_revenue),
                    'total_profit': float(total_profit),
                    'average_daily_revenue': float(avg_daily_revenue),
                    'average_daily_profit': float(avg_daily_profit),
                    'average_margin': float(avg_margin),
                    'best_day': best_day,
                    'worst_day': worst_day,
                    'trend_direction': trend_direction,
                    'trend_percentage': float(trend_percentage)
                }
            }

        except Exception as e:
            logger.error(
                f"Error calculating profit trend: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'daily_data': [],
                'summary': {}
            }

    @staticmethod
    def analyze_profit_issues(restaurant, branch=None):
        """
        Analyze profit issues and generate suggestions
        """
        try:
            from .models import MenuItemPerformance
            from menu.models import MenuItem

            logger.info(f"Analyzing profit issues for {restaurant.name}")

            # Get recent performance data (last 30 days)
            thirty_days_ago = timezone.now().date() - timedelta(days=30)

            performances = MenuItemPerformance.objects.filter(
                date__gte=thirty_days_ago,
                restaurant=restaurant
            )

            if branch:
                performances = performances.filter(branch=branch)

            # Aggregate by menu item
            from django.db.models import Avg, Count, Sum
            item_stats = performances.values(
                'menu_item__id',
                'menu_item__name',
                'menu_item__price',
                'menu_item__cost_price',
                'menu_item__category__name'
            ).annotate(
                avg_margin=Avg('profit_margin'),
                total_quantity=Sum('quantity_sold'),
                total_revenue=Sum('revenue'),
                days_sold=Count('id')
            )

            # Analyze issues
            loss_makers = []
            low_margin_items = []
            price_suggestions = []

            for stat in item_stats:
                avg_margin = stat['avg_margin'] or 0
                current_price = stat['menu_item__price'] or Decimal('0.00')
                cost_price = stat['menu_item__cost_price'] or Decimal('0.00')

                # Loss makers (negative margin)
                if avg_margin < 0:
                    loss_makers.append({
                        'id': stat['menu_item__id'],
                        'name': stat['menu_item__name'],
                        'category': stat['menu_item__category__name'],
                        'current_price': float(current_price),
                        'cost_price': float(cost_price),
                        'margin': float(avg_margin),
                        'quantity_sold': stat['total_quantity'],
                        'revenue': float(stat['total_revenue']),
                        'days_sold': stat['days_sold']
                    })

                # Low margin items (0-15%)
                elif avg_margin < 15:
                    low_margin_items.append({
                        'id': stat['menu_item__id'],
                        'name': stat['menu_item__name'],
                        'category': stat['menu_item__category__name'],
                        'current_price': float(current_price),
                        'cost_price': float(cost_price),
                        'margin': float(avg_margin),
                        'quantity_sold': stat['total_quantity'],
                        'revenue': float(stat['total_revenue']),
                        'days_sold': stat['days_sold']
                    })

                # Generate price suggestions for items with data
                if stat['total_quantity'] > 0 and cost_price > 0:
                    # Target 40% profit margin
                    target_price = cost_price * Decimal('1.67')  # 40% margin

                    # More than 10% below target
                    if current_price < target_price * Decimal('0.9'):
                        price_suggestions.append({
                            'menu_item_id': stat['menu_item__id'],
                            'menu_item_name': stat['menu_item__name'],
                            'category': stat['menu_item__category__name'],
                            'current_price': float(current_price),
                            'suggested_price': float(target_price),
                            'price_increase': float(target_price - current_price),
                            'percentage_increase': float((target_price - current_price) / current_price * 100),
                            'expected_margin_impact': 40.0 - float(avg_margin),
                            'current_margin': float(avg_margin),
                            'quantity_sold': stat['total_quantity'],
                            'revenue_impact': float((target_price - current_price) * stat['total_quantity'])
                        })

            # Sort results
            loss_makers.sort(key=lambda x: x['margin'])
            low_margin_items.sort(key=lambda x: x['margin'])
            price_suggestions.sort(
                key=lambda x: x['revenue_impact'], reverse=True)

            return {
                'success': True,
                'loss_makers': loss_makers[:10],  # Top 10 loss makers
                # Top 10 low margin items
                'low_margin_items': low_margin_items[:10],
                # Top 10 suggestions
                'price_suggestions': price_suggestions[:10],
                'summary': {
                    'total_items_analyzed': len(item_stats),
                    'loss_makers_count': len(loss_makers),
                    'low_margin_count': len(low_margin_items),
                    'suggestions_count': len(price_suggestions)
                }
            }

        except Exception as e:
            logger.error(
                f"Error analyzing profit issues: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'loss_makers': [],
                'low_margin_items': [],
                'price_suggestions': []
            }


class ProfitDashboardAPI:
    """
    API for profit dashboard data
    """

    @staticmethod
    def get_dashboard_data(user, view_level='branch', branch_id=None):
        """
        Get comprehensive dashboard data
        """
        try:
            logger.info(
                f"Getting dashboard data for user: {user.username}, view_level: {view_level}")

            # Get restaurant and branch
            restaurant = user.restaurant
            branch = None

            if view_level == 'branch':
                if branch_id:
                    from restaurants.models import Branch
                    try:
                        branch = Branch.objects.get(
                            id=branch_id, restaurant=restaurant)
                    except Branch.DoesNotExist:
                        logger.warning(
                            f"Branch {branch_id} not found for restaurant {restaurant.id}")
                elif user.branch:
                    branch = user.branch

            # Get today's data
            today = timezone.now().date()
            today_data = ProfitCalculator.calculate_daily_profit(
                today, restaurant, branch)

            # Get 30-day trend
            trend_data = ProfitCalculator.calculate_profit_trend(
                30, restaurant, branch)

            # Get profit issues
            issues_data = ProfitCalculator.analyze_profit_issues(
                restaurant, branch)

            # Get waste summary from waste tracker
            waste_summary = ProfitDashboardAPI._get_waste_summary(
                restaurant, branch)

            # Calculate key metrics
            metrics = {
                'today': {
                    'revenue': today_data.get('revenue', 0),
                    'profit': today_data.get('net_profit', 0),
                    'margin': today_data.get('profit_margin', 0),
                    'orders': today_data.get('order_count', 0),
                    'waste_cost': today_data.get('waste_cost', 0),
                    'waste_percentage': today_data.get('waste_percentage', 0)
                },
                'trend': {
                    'total_revenue': trend_data.get('summary', {}).get('total_revenue', 0),
                    'total_profit': trend_data.get('summary', {}).get('total_profit', 0),
                    'average_margin': trend_data.get('summary', {}).get('average_margin', 0),
                    'trend_direction': trend_data.get('summary', {}).get('trend_direction', 'stable'),
                    'trend_percentage': trend_data.get('summary', {}).get('trend_percentage', 0)
                },
                'issues': {
                    'loss_makers': len(issues_data.get('loss_makers', [])),
                    'low_margin_items': len(issues_data.get('low_margin_items', [])),
                    'price_suggestions': len(issues_data.get('price_suggestions', []))
                },
                'waste': waste_summary
            }

            return {
                'success': True,
                'timestamp': timezone.now().isoformat(),
                'view': {
                    'level': view_level,
                    'restaurant': {
                        'id': restaurant.id,
                        'name': restaurant.name
                    },
                    'branch': {
                        'id': branch.id if branch else None,
                        'name': branch.name if branch else None
                    } if branch else None
                },
                'today': metrics['today'],
                'trend': metrics['trend'],
                'issues': metrics['issues'],
                'waste': metrics['waste'],
                # Last 7 days for chart
                'daily_trend': trend_data.get('daily_data', [])[-7:],
                # Top 5 issues
                'recent_issues': issues_data.get('loss_makers', [])[:5]
            }

        except Exception as e:
            logger.error(
                f"Error getting dashboard data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
                'view': {
                    'level': view_level,
                    'restaurant': None,
                    'branch': None
                },
                'today': {
                    'revenue': 0,
                    'profit': 0,
                    'margin': 0,
                    'orders': 0,
                    'waste_cost': 0,
                    'waste_percentage': 0
                },
                'trend': {
                    'total_revenue': 0,
                    'total_profit': 0,
                    'average_margin': 0,
                    'trend_direction': 'stable',
                    'trend_percentage': 0
                },
                'issues': {
                    'loss_makers': 0,
                    'low_margin_items': 0,
                    'price_suggestions': 0
                },
                'waste': {
                    'today_cost': 0,
                    'week_cost': 0,
                    'reduction_potential': 0
                },
                'daily_trend': [],
                'recent_issues': []
            }

    @staticmethod
    def _get_waste_summary(restaurant, branch=None):
        """
        Get waste summary from waste tracker
        """
        try:
            from waste_tracker.models import WasteRecord
            from datetime import timedelta

            today = timezone.now().date()
            week_ago = today - timedelta(days=7)

            # Today's waste
            today_waste = WasteRecord.objects.filter(
                status='approved',
                recorded_at__date=today,
                branch__restaurant=restaurant
            )

            if branch:
                today_waste = today_waste.filter(branch=branch)

            today_cost = sum(
                (record.stock_transaction.total_cost if record.stock_transaction else 0)
                for record in today_waste
            )

            # Week's waste
            week_waste = WasteRecord.objects.filter(
                status='approved',
                recorded_at__date__gte=week_ago,
                branch__restaurant=restaurant
            )

            if branch:
                week_waste = week_waste.filter(branch=branch)

            week_cost = sum(
                (record.stock_transaction.total_cost if record.stock_transaction else 0)
                for record in week_waste
            )

            # Calculate reduction potential (assume 30% reduction possible)
            reduction_potential = week_cost * Decimal('0.30')

            return {
                'today_cost': float(today_cost),
                'week_cost': float(week_cost),
                'reduction_potential': float(reduction_potential),
                'today_count': today_waste.count(),
                'week_count': week_waste.count()
            }

        except Exception as e:
            logger.error(f"Error getting waste summary: {str(e)}")
            return {
                'today_cost': 0.0,
                'week_cost': 0.0,
                'reduction_potential': 0.0,
                'today_count': 0,
                'week_count': 0
            }
