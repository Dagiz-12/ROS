# profit_intelligence/api_views.py
from waste_tracker.models import WasteRecord
from menu.models import MenuItem
from tables.models import Order, OrderItem
from inventory.models import StockItem, StockTransaction
from .models import ProfitAggregation, MenuItemPerformance, ProfitAlert
from django.db.models import Sum, Count, Avg, Q, F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
import logging

from httpcore import Request, Response as HTTPResponse


from .business_logic import ProfitDashboardAPI, ProfitCalculator
from accounts.permissions import IsManagerOrAdmin
from django.db.models import Count


logger = logging.getLogger(__name__)


class ProfitDashboardAPIView(APIView):
    """
    Main profit dashboard API endpoint
    """
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        try:
            user = request.user

            # Check if user has restaurant
            if not hasattr(user, 'restaurant') or not user.restaurant:
                return Response({
                    'success': False,
                    'error': 'User not assigned to a restaurant',
                    'details': f'User: {user.username}, Role: {user.role}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get parameters
            view_level = request.GET.get('view_level', 'branch')
            branch_id = request.GET.get('branch_id')

            # Validate view level
            if view_level not in ['branch', 'restaurant']:
                view_level = 'branch'

            # Validate branch access if specified
            if branch_id and view_level == 'branch':
                from restaurants.models import Branch
                try:
                    branch = Branch.objects.get(id=branch_id)
                    if branch.restaurant != user.restaurant:
                        return Response({
                            'success': False,
                            'error': 'Unauthorized access to this branch'
                        }, status=status.HTTP_403_FORBIDDEN)
                except Branch.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': 'Branch not found'
                    }, status=status.HTTP_404_NOT_FOUND)

            # Get dashboard data
            data = ProfitDashboardAPI.get_dashboard_data(
                user=user,
                view_level=view_level,
                branch_id=branch_id
            )

            return Response(data)

        except Exception as e:
            logger.error(f"Profit dashboard error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to load profit dashboard',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DailyProfitAPIView(APIView):
    """
    Get daily profit for a specific date or date range
    """
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        try:
            user = request.user

            # Get date parameters
            date_str = request.GET.get('date')
            start_date_str = request.GET.get('start_date')
            end_date_str = request.GET.get('end_date')
            days = int(request.GET.get('days', 30))

            # Single date
            if date_str:
                from datetime import datetime
                date = datetime.strptime(date_str, '%Y-%m-%d').date()

                # Calculate profit for this date
                profit_data = ProfitCalculator.calculate_daily_profit(
                    date=date,
                    restaurant=user.restaurant,
                    branch=user.branch if request.GET.get(
                        'view_level', 'branch') == 'branch' else None
                )

                return Response({
                    'success': True,
                    'date': date_str,
                    'data': {
                        'revenue': float(profit_data.revenue),
                        'cost_of_goods': float(profit_data.cost_of_goods),
                        'waste_cost': float(profit_data.waste_cost),
                        'net_profit': float(profit_data.net_profit),
                        'profit_margin': float(profit_data.profit_margin),
                        'order_count': profit_data.order_count,
                        'average_order_value': float(profit_data.average_order_value)
                    }
                })

            # Date range
            elif start_date_str and end_date_str:
                from datetime import datetime
                start_date = datetime.strptime(
                    start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

                daily_data = []
                current_date = start_date

                while current_date <= end_date:
                    profit_data = ProfitCalculator.calculate_daily_profit(
                        date=current_date,
                        restaurant=user.restaurant,
                        branch=user.branch if request.GET.get(
                            'view_level', 'branch') == 'branch' else None
                    )

                    daily_data.append({
                        'date': current_date.isoformat(),
                        'revenue': float(profit_data.revenue),
                        'cost': float(profit_data.cost_of_goods),
                        'profit': float(profit_data.net_profit),
                        'margin': float(profit_data.profit_margin),
                        'orders': profit_data.order_count
                    })

                    current_date += timedelta(days=1)

                # Calculate summary
                total_revenue = sum(day['revenue'] for day in daily_data)
                total_profit = sum(day['profit'] for day in daily_data)
                total_orders = sum(day['orders'] for day in daily_data)

                return Response({
                    'success': True,
                    'range': {
                        'start_date': start_date_str,
                        'end_date': end_date_str,
                        'days': (end_date - start_date).days + 1
                    },
                    'daily_data': daily_data,
                    'summary': {
                        'total_revenue': total_revenue,
                        'total_profit': total_profit,
                        'total_orders': total_orders,
                        'average_daily_profit': total_profit / len(daily_data) if daily_data else 0,
                        'average_order_value': total_revenue / total_orders if total_orders > 0 else 0
                    }
                })

            # Default: 30-day trend
            else:
                trend_data = ProfitCalculator.calculate_profit_trend(
                    days=days,
                    restaurant=user.restaurant,
                    branch=user.branch if request.GET.get(
                        'view_level', 'branch') == 'branch' else None
                )

                return Response({
                    'success': True,
                    **trend_data
                })

        except Exception as e:
            logger.error(f"Daily profit API error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MenuItemProfitAPIView(APIView):
    """
    Get profitability analysis for menu items
    """
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        try:
            from .models import MenuItemPerformance
            from django.db.models import Sum

            user = request.user

            # Get date range
            days = int(request.GET.get('days', 30))
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)

            # Get menu item performances
            performances = MenuItemPerformance.objects.filter(
                date__gte=start_date,
                date__lte=end_date,
                restaurant=user.restaurant
            )

            if request.GET.get('view_level', 'branch') == 'branch' and user.branch:
                performances = performances.filter(branch=user.branch)

            # Aggregate by menu item
            from django.db.models import Avg, Count
            aggregated = performances.values(
                'menu_item__id',
                'menu_item__name',
                'menu_item__category__name',
                'menu_item__price'
            ).annotate(
                total_quantity=Sum('quantity_sold'),
                total_revenue=Sum('revenue'),
                total_cost=Sum('ingredient_cost'),
                avg_margin=Avg('profit_margin'),
                days_sold=Count('id')
            ).order_by('-total_revenue')

            items = []
            for agg in aggregated:
                total_profit = agg['total_revenue'] - agg['total_cost']
                avg_profit_margin = agg['avg_margin'] or 0

                items.append({
                    'id': agg['menu_item__id'],
                    'name': agg['menu_item__name'],
                    'category': agg['menu_item__category__name'],
                    'price': float(agg['menu_item__price']),
                    'quantity_sold': agg['total_quantity'],
                    'revenue': float(agg['total_revenue']),
                    'cost': float(agg['total_cost']),
                    'profit': float(total_profit),
                    'profit_margin': float(avg_profit_margin),
                    'days_sold': agg['days_sold'],
                    'status': 'high_profit' if avg_profit_margin >= 40 else
                             'good_profit' if avg_profit_margin >= 20 else
                             'low_profit' if avg_profit_margin >= 10 else
                             'problem' if avg_profit_margin > 0 else 'loss'
                             })

            # Calculate summary
            total_revenue = sum(item['revenue'] for item in items)
            total_profit = sum(item['profit'] for item in items)
            avg_margin = sum(item['profit_margin']
                             for item in items) / len(items) if items else 0

            return Response({
                'success': True,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'items': items,
                'summary': {
                    'total_items': len(items),
                    'total_revenue': total_revenue,
                    'total_profit': total_profit,
                    'average_margin': avg_margin,
                    'high_profit_count': len([i for i in items if i['profit_margin'] >= 40]),
                    'low_profit_count': len([i for i in items if i['profit_margin'] < 20]),
                    'loss_makers': len([i for i in items if i['profit_margin'] <= 0])
                }
            })

        except Exception as e:
            logger.error(
                f"Menu item profit API error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfitAlertsAPIView(APIView):
    """
    Get profit alerts
    """
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        try:
            from .models import ProfitAlert

            user = request.user

            # Get parameters
            show_resolved = request.GET.get(
                'show_resolved', 'false').lower() == 'true'
            alert_type = request.GET.get('type')
            severity = request.GET.get('severity')

            # Get alerts
            alerts = ProfitAlert.objects.filter(
                restaurant=user.restaurant
            )

            if request.GET.get('view_level', 'branch') == 'branch' and user.branch:
                alerts = alerts.filter(branch=user.branch)

            if not show_resolved:
                alerts = alerts.filter(is_resolved=False)

            if alert_type:
                alerts = alerts.filter(alert_type=alert_type)

            if severity:
                alerts = alerts.filter(severity=severity)

            alerts = alerts.order_by('-severity', '-created_at')

            # Serialize alerts
            alert_list = []
            for alert in alerts:
                alert_list.append({
                    'id': str(alert.alert_id),
                    'type': alert.alert_type,
                    'type_display': alert.get_alert_type_display(),
                    'severity': alert.severity,
                    'severity_display': alert.get_severity_display(),
                    'title': alert.title,
                    'message': alert.message,
                    'details': alert.details,
                    'menu_item': {
                        'id': alert.menu_item.id if alert.menu_item else None,
                        'name': alert.menu_item.name if alert.menu_item else None
                    } if alert.menu_item else None,
                    'current_value': float(alert.current_value) if alert.current_value else None,
                    'threshold': float(alert.threshold) if alert.threshold else None,
                    'deviation': float(alert.deviation) if alert.deviation else None,
                    'is_resolved': alert.is_resolved,
                    'is_acknowledged': alert.is_acknowledged,
                    'created_at': alert.created_at.isoformat(),
                    'age_days': alert.age_days
                })

            # Count by severity
            unresolved = ProfitAlert.objects.filter(
                restaurant=user.restaurant,
                is_resolved=False
            )

            if request.GET.get('view_level', 'branch') == 'branch' and user.branch:
                unresolved = unresolved.filter(branch=user.branch)

            severity_counts = unresolved.values(
                'severity').annotate(count=Count('id'))

            return Response({
                'success': True,
                'alerts': alert_list,
                'counts': {
                    'total': alerts.count(),
                    'unresolved': unresolved.count(),
                    'by_severity': {item['severity']: item['count'] for item in severity_counts}
                }
            })

        except Exception as e:
            logger.error(f"Profit alerts API error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfitIssuesAPIView(APIView):
    """
    Get detailed profit issues and suggestions
    """
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        try:
            user = request.user

            # Analyze profit issues
            issues = ProfitCalculator.analyze_profit_issues(
                restaurant=user.restaurant,
                branch=user.branch if request.GET.get(
                    'view_level', 'branch') == 'branch' else None
            )

            return Response({
                'success': True,
                'issues': issues,
                'summary': {
                    'total_items_with_issues': len(issues['loss_makers']) + len(issues['low_margin_items']),
                    'loss_makers_count': len(issues['loss_makers']),
                    'low_margin_count': len(issues['low_margin_items']),
                    'suggestions_count': len(issues['price_suggestions'])
                }
            })

        except Exception as e:
            logger.error(f"Profit issues API error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# new api views

# profit_intelligence/api_views.py - ADD THESE VIEWS


logger = logging.getLogger(__name__)

# ADD THESE NEW VIEWS TO YOUR EXISTING api_views.py


class ProfitTableAPIView(APIView):
    """
    Profit table data for dashboard
    """
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        try:
            user = request.user
            period = request.GET.get('period', 'today')

            # Get data for the period
            if period == 'today':
                date = timezone.now().date()
                data = self._get_daily_profit_table(user, date)
            elif period == 'week':
                data = self._get_weekly_profit_table(user)
            elif period == 'month':
                data = self._get_monthly_profit_table(user)
            else:
                # Custom days
                days = int(period) if period.isdigit() else 7
                data = self._get_custom_period_profit_table(user, days)

            # Normalize response: admin frontend expects 'items' to be an array.
            # If the helper returned a dict (summary), return it under 'summary'
            # and provide an empty items array to avoid JS `.map` errors.
            if isinstance(data, dict) and not isinstance(data, list):
                return Response({
                    'success': True,
                    'period': period,
                    'items': [],
                    'summary': data
                })

            return Response({
                'success': True,
                'period': period,
                'items': data
            })

        except Exception as e:
            logger.error(f"Profit table API error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_daily_profit_table(self, user, date):
        """Get daily profit table data"""
        # Get today's orders
        orders = Order.objects.filter(
            completed_at__date=date,
            is_paid=True,
            table__branch__restaurant=user.restaurant
        )

        if user.branch and self.request.GET.get('view_level', 'branch') == 'branch':
            orders = orders.filter(table__branch=user.branch)

        # Get today's waste
        waste_records = WasteRecord.objects.filter(
            status='approved',
            recorded_at__date=date,
            branch__restaurant=user.restaurant
        )

        if user.branch and self.request.GET.get('view_level', 'branch') == 'branch':
            waste_records = waste_records.filter(branch=user.branch)

        # Calculate totals
        total_revenue = orders.aggregate(
            total=Sum('total_amount'))['total'] or 0
        total_waste_cost = sum(
            (record.stock_transaction.total_cost if record.stock_transaction else 0)
            for record in waste_records
        )

        # Get ingredient costs from recipes
        total_ingredient_cost = 0
        for order in orders:
            for order_item in order.items.all():
                if getattr(order_item.menu_item, 'cost_price', None):
                    total_ingredient_cost += order_item.menu_item.cost_price * order_item.quantity

        # Calculate profit
        net_profit = total_revenue - total_ingredient_cost - total_waste_cost
        profit_margin = (net_profit / total_revenue *
                         100) if total_revenue > 0 else 0

        return {
            'revenue': float(total_revenue),
            'ingredient_cost': float(total_ingredient_cost),
            'waste_cost': float(total_waste_cost),
            'net_profit': float(net_profit),
            'profit_margin': float(profit_margin),
            'order_count': orders.count(),
            'waste_count': waste_records.count()
        }

    def _get_weekly_profit_table(self, user):
        """Get weekly profit table data"""
        week_ago = timezone.now().date() - timedelta(days=7)

        # Get profit aggregations for the week
        aggregations = ProfitAggregation.objects.filter(
            date__gte=week_ago,
            restaurant=user.restaurant
        )

        if user.branch and self.request.GET.get('view_level', 'branch') == 'branch':
            aggregations = aggregations.filter(branch=user.branch)

        # Aggregate data
        data = aggregations.aggregate(
            total_revenue=Sum('revenue'),
            total_cost=Sum('cost_of_goods'),
            total_waste=Sum('waste_cost'),
            total_net_profit=Sum('net_profit'),
            avg_margin=Avg('profit_margin'),
            total_orders=Sum('order_count')
        )

        return {
            'revenue': float(data['total_revenue'] or 0),
            'ingredient_cost': float(data['total_cost'] or 0),
            'waste_cost': float(data['total_waste'] or 0),
            'net_profit': float(data['total_net_profit'] or 0),
            'profit_margin': float(data['avg_margin'] or 0),
            'order_count': data['total_orders'] or 0,
            'period_days': 7
        }

    def _get_monthly_profit_table(self, user):
        """Get monthly profit table data"""
        month_ago = timezone.now().date() - timedelta(days=30)

        aggregations = ProfitAggregation.objects.filter(
            date__gte=month_ago,
            restaurant=user.restaurant
        )

        # use self.request (ensure this method is on a view that has .request)
        if user.branch and self.request.GET.get('view_level', 'branch') == 'branch':
            aggregations = aggregations.filter(branch=user.branch)

        data = aggregations.aggregate(
            total_revenue=Sum('revenue'),
            total_cost=Sum('cost_of_goods'),
            total_waste=Sum('waste_cost'),
            total_net_profit=Sum('net_profit'),
            avg_margin=Avg('profit_margin'),
            total_orders=Sum('order_count')
        )

        return {
            'revenue': float(data['total_revenue'] or 0),
            'ingredient_cost': float(data['total_cost'] or 0),
            'waste_cost': float(data['total_waste'] or 0),
            'net_profit': float(data['total_net_profit'] or 0),
            'profit_margin': float(data['avg_margin'] or 0),
            'order_count': data['total_orders'] or 0,
            'period_days': 30
        }

    def _get_custom_period_profit_table(self, user, days):
        """Get custom period profit table data"""
        start_date = timezone.now().date() - timedelta(days=days)

        aggregations = ProfitAggregation.objects.filter(
            date__gte=start_date,
            restaurant=user.restaurant
        )

        if user.branch and self.request.GET.get('view_level', 'branch') == 'branch':
            aggregations = aggregations.filter(branch=user.branch)

        data = aggregations.aggregate(
            total_revenue=Sum('revenue'),
            total_cost=Sum('cost_of_goods'),
            total_waste=Sum('waste_cost'),
            total_net_profit=Sum('net_profit'),
            avg_margin=Avg('profit_margin'),
            total_orders=Sum('order_count')
        )

        return {
            'revenue': float(data['total_revenue'] or 0),
            'ingredient_cost': float(data['total_cost'] or 0),
            'waste_cost': float(data['total_waste'] or 0),
            'net_profit': float(data['total_net_profit'] or 0),
            'profit_margin': float(data['avg_margin'] or 0),
            'order_count': data['total_orders'] or 0,
            'period_days': days
        }


class BusinessMetricsAPIView(APIView):
    """
    Business metrics for admin panel
    """
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        try:
            user = request.user
            period = request.GET.get('period', 'today')

            # Calculate metrics based on period
            if period == 'today':
                metrics = self._get_today_metrics(user)
            elif period == 'week':
                metrics = self._get_week_metrics(user)
            elif period == 'month':
                metrics = self._get_month_metrics(user)
            else:
                metrics = self._get_today_metrics(user)

            # Get waste data from waste tracker
            waste_data = self._get_waste_data(user, period)

            # Get profit data
            profit_data = self._get_profit_data(user, period)

            return Response({
                'success': True,
                'period': period,
                'metrics': metrics,
                'waste': waste_data,
                'profit': profit_data,
                'date_range': {
                    'start': (timezone.now() - timedelta(days=1)).date().isoformat(),
                    'end': timezone.now().date().isoformat()
                }
            })

        except Exception as e:
            logger.error(
                f"Business metrics API error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_today_metrics(self, user):
        """Get today's business metrics"""
        today = timezone.now().date()

        # Today's orders
        orders = Order.objects.filter(
            completed_at__date=today,
            is_paid=True,
            table__branch__restaurant=user.restaurant
        )

        if user.branch:
            orders = orders.filter(table__branch=user.branch)

        total_revenue = orders.aggregate(
            total=Sum('total_amount'))['total'] or 0
        order_count = orders.count()

        # Yesterday for comparison
        yesterday = today - timedelta(days=1)
        yesterday_orders = Order.objects.filter(
            completed_at__date=yesterday,
            is_paid=True,
            table__branch__restaurant=user.restaurant
        )

        if user.branch:
            yesterday_orders = yesterday_orders.filter(
                table__branch=user.branch)

        yesterday_revenue = yesterday_orders.aggregate(
            total=Sum('total_amount'))['total'] or 0

        # Calculate changes
        revenue_change = 0
        if yesterday_revenue > 0:
            revenue_change = (
                (total_revenue - yesterday_revenue) / yesterday_revenue) * 100

        orders_change = 0
        yesterday_order_count = yesterday_orders.count()
        if yesterday_order_count > 0:
            orders_change = (
                (order_count - yesterday_order_count) / yesterday_order_count) * 100

        # Average order value
        avg_order_value = total_revenue / order_count if order_count > 0 else 0

        return {
            'total_revenue': float(total_revenue),
            'total_orders': order_count,
            'revenue_change': float(revenue_change),
            'orders_change': float(orders_change),
            'average_order_value': float(avg_order_value)
        }

    def _get_waste_data(self, user, period):
        """Get waste data from waste tracker"""
        try:
            from waste_tracker.models import WasteRecord

            if period == 'today':
                start_date = timezone.now().date()
            elif period == 'week':
                start_date = timezone.now().date() - timedelta(days=7)
            elif period == 'month':
                start_date = timezone.now().date() - timedelta(days=30)
            else:
                start_date = timezone.now().date()

            waste_records = WasteRecord.objects.filter(
                status='approved',
                recorded_at__date__gte=start_date,
                branch__restaurant=user.restaurant
            )

            if user.branch:
                waste_records = waste_records.filter(branch=user.branch)

            total_waste_cost = sum(
                (record.stock_transaction.total_cost if record.stock_transaction else 0)
                for record in waste_records
            )

            # Find best seller (item with least waste)
            waste_by_item = {}
            for record in waste_records:
                if record.stock_item:
                    item_id = record.stock_item.id
                    if item_id not in waste_by_item:
                        waste_by_item[item_id] = {
                            'item': record.stock_item,
                            'cost': 0,
                            'count': 0
                        }
                    waste_by_item[item_id]['cost'] += record.stock_transaction.total_cost if record.stock_transaction else 0
                    waste_by_item[item_id]['count'] += 1

            # Sort by cost (ascending - least waste is best)
            sorted_items = sorted(waste_by_item.values(),
                                  key=lambda x: x['cost'])
            best_seller = sorted_items[0] if sorted_items else None

            return {
                'total_waste_cost': float(total_waste_cost),
                'waste_record_count': waste_records.count(),
                'best_seller': {
                    'name': best_seller['item'].name if best_seller else None,
                    'cost': float(best_seller['cost']) if best_seller else 0,
                    'count': best_seller['count'] if best_seller else 0
                } if best_seller else None
            }

        except Exception as e:
            logger.error(f"Error getting waste data: {str(e)}")
            return {
                'total_waste_cost': 0.0,
                'waste_record_count': 0,
                'best_seller': None
            }

    def _get_profit_data(self, user, period):
        """Get profit data"""
        try:
            # Get profit aggregation for the period
            if period == 'today':
                date = timezone.now().date()
                aggregation = ProfitAggregation.objects.filter(
                    date=date,
                    restaurant=user.restaurant
                ).first()

                if user.branch:
                    aggregation = ProfitAggregation.objects.filter(
                        date=date,
                        restaurant=user.restaurant,
                        branch=user.branch
                    ).first()

                if aggregation:
                    return {
                        'total_profit': float(aggregation.net_profit),
                        'profit_margin': float(aggregation.profit_margin),
                        'waste_percentage': float(aggregation.waste_percentage)
                    }

            # If no aggregation found, calculate manually
            return {
                'total_profit': 0.0,
                'profit_margin': 0.0,
                'waste_percentage': 0.0
            }

        except Exception as e:
            logger.error(f"Error getting profit data: {str(e)}")
            return {
                'total_profit': 0.0,
                'profit_margin': 0.0,
                'waste_percentage': 0.0
            }


class SalesDataAPIView(APIView):
    """
    Sales data for charts
    """
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        try:
            user = request.user
            days = int(request.GET.get('days', 7))

            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)

            # Get sales data for each day
            sales_data = []
            current_date = start_date

            while current_date <= end_date:
                # Get orders for this day
                orders = Order.objects.filter(
                    completed_at__date=current_date,
                    is_paid=True,
                    table__branch__restaurant=user.restaurant
                )

                if user.branch and request.GET.get('view_level', 'branch') == 'branch':
                    orders = orders.filter(table__branch=user.branch)

                total_sales = orders.aggregate(
                    total=Sum('total_amount'))['total'] or 0
                order_count = orders.count()

                sales_data.append({
                    'date': current_date.isoformat(),
                    'day_name': current_date.strftime('%a'),
                    'total': float(total_sales),
                    'orders': order_count,
                    'avg_order_value': float(total_sales / order_count) if order_count > 0 else 0
                })

                current_date += timedelta(days=1)

            return Response({
                'success': True,
                'days': days,
                'data': sales_data
            })

        except Exception as e:
            logger.error(f"Sales data API error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PopularItemsAPIView(APIView):
    """
    Popular menu items
    """
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        try:
            user = request.user
            days = int(request.GET.get('days', 7))

            start_date = timezone.now().date() - timedelta(days=days)

            # Get popular items from order items
            from tables.models import OrderItem
            from menu.models import MenuItem

            popular_items = OrderItem.objects.filter(
                order__completed_at__date__gte=start_date,
                order__is_paid=True,
                order__table__branch__restaurant=user.restaurant
            ).values(
                'menu_item__id',
                'menu_item__name',
                'menu_item__category__name',
                'menu_item__price',
                'menu_item__image'
            ).annotate(
                total_sold=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('unit_price'))
            ).order_by('-total_sold')[:10]

            items = []
            for item in popular_items:
                items.append({
                    'id': item['menu_item__id'],
                    'name': item['menu_item__name'],
                    'category': item['menu_item__category__name'],
                    'price': float(item['menu_item__price']),
                    'image': item['menu_item__image'] if item['menu_item__image'] else None,
                    'sold': item['total_sold'],
                    'revenue': float(item['total_revenue'])
                })

            return Response({
                'success': True,
                'days': days,
                'items': items
            })

        except Exception as e:
            logger.error(f"Popular items API error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RecentActivityAPIView(APIView):
    """
    Recent system activity
    """
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        try:
            user = request.user
            limit = int(request.GET.get('limit', 10))

            activities = []

            # Get recent orders
            recent_orders = Order.objects.filter(
                table__branch__restaurant=user.restaurant,
                completed_at__isnull=False
            ).order_by('-completed_at')[:5]

            for order in recent_orders:
                activities.append({
                    'type': 'order',
                    'icon': 'shopping-cart',
                    'title': f'Order #{order.order_number} Completed',
                    'description': f'Table {order.table.table_number if order.table else "Unknown"} - ${order.total_amount:.2f}',
                    'time': order.completed_at,
                    'amount': float(order.total_amount)
                })

            # Get recent waste records
            from waste_tracker.models import WasteRecord
            recent_waste = WasteRecord.objects.filter(
                branch__restaurant=user.restaurant,
                status='approved'
            ).order_by('-recorded_at')[:5]

            for waste in recent_waste:
                activities.append({
                    'type': 'waste',
                    'icon': 'trash',
                    'title': f'Waste Recorded',
                    'description': f'{waste.stock_item.name if waste.stock_item else "Unknown Item"} - {waste.waste_reason.name}',
                    'time': waste.recorded_at,
                    'amount': -float(waste.total_cost) if waste.total_cost else 0
                })

            # Sort by time and limit
            activities.sort(key=lambda x: x['time'], reverse=True)
            activities = activities[:limit]

            # Format times for display
            for activity in activities:
                activity['time'] = self._format_time_difference(
                    activity['time'])

            return Response({
                'success': True,
                'activities': activities
            })

        except Exception as e:
            logger.error(f"Recent activity API error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _format_time_difference(self, dt):
        """Format datetime as time difference string"""
        if not dt:
            return "Unknown"

        now = timezone.now()
        diff = now - dt

        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
