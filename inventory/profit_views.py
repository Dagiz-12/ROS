# inventory/profit_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .business_logic import ProfitCalculator, WasteAnalyzer, BusinessIntelligenceAPI
from accounts.permissions import IsManagerOrAdmin
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def profit_dashboard(request):
    """
    Get comprehensive profit dashboard data
    Accepts ?view_level=branch (default) or ?view_level=restaurant
    """
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
        view_level = request.query_params.get('view_level', 'branch')
        branch_id = request.query_params.get('branch_id')

        # Validate view level
        if view_level not in ['branch', 'restaurant']:
            view_level = 'branch'

        # Get data with scope awareness
        data = BusinessIntelligenceAPI.get_profit_dashboard(
            user=user,
            view_level=view_level,
            branch_id=branch_id
        )

        return Response(data)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Profit Dashboard Error: {str(e)}")
        print(f"Error details: {error_details}")

        return Response({
            'success': False,
            'error': 'Failed to load profit dashboard',
            'details': str(e),
            'user_info': {
                'username': request.user.username if request.user else None,
                'restaurant': request.user.restaurant.name if hasattr(request.user, 'restaurant') and request.user.restaurant else None,
                'branch': request.user.branch.name if hasattr(request.user, 'branch') and request.user.branch else None,
                'manager_scope': request.user.manager_scope if hasattr(request.user, 'manager_scope') else None
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def menu_item_profitability(request):
    """
    Get profitability analysis for all menu items
    """
    try:
        items = ProfitCalculator.calculate_menu_item_profit()

        # Apply filters if provided
        category_id = request.query_params.get('category_id')
        min_margin = request.query_params.get('min_margin')
        max_margin = request.query_params.get('max_margin')

        filtered_items = items

        if category_id:
            filtered_items = [item for item in filtered_items
                              if item.get('category_id') == int(category_id)]

        if min_margin:
            filtered_items = [item for item in filtered_items
                              if item['profit_margin'] >= float(min_margin)]

        if max_margin:
            filtered_items = [item for item in filtered_items
                              if item['profit_margin'] <= float(max_margin)]

        # Calculate summary
        total_revenue = sum(item['revenue'] for item in filtered_items)
        total_profit = sum(item['gross_profit'] for item in filtered_items)
        avg_margin = sum(item['profit_margin'] for item in filtered_items) / \
            len(filtered_items) if filtered_items else 0

        return Response({
            'success': True,
            'items': filtered_items,
            'summary': {
                'total_items': len(filtered_items),
                'total_revenue': total_revenue,
                'total_profit': total_profit,
                'average_margin': avg_margin,
                'high_profit_count': len([i for i in filtered_items if i['profit_margin'] >= 40]),
                'low_profit_count': len([i for i in filtered_items if i['profit_margin'] < 20]),
                'loss_makers': len([i for i in filtered_items if i['profit_margin'] <= 0])
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def profit_trend(request):
    """
    Get profit trend over time
    """
    try:
        days = int(request.query_params.get('days', 30))
        trend = ProfitCalculator.calculate_profit_trend(days)
        return Response({
            'success': True,
            **trend
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def daily_profit(request):
    """
    Get profit for a specific date or date range
    """
    try:
        date_str = request.query_params.get('date')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if start_date_str and end_date_str:
            # Date range
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            daily_data = []
            current_date = start_date
            while current_date <= end_date:
                profit_data = ProfitCalculator.calculate_daily_profit(
                    current_date)
                daily_data.append(profit_data)
                current_date += timedelta(days=1)

            # Calculate range summary
            total_revenue = sum(day['summary']['total_revenue']
                                for day in daily_data)
            total_profit = sum(day['summary']['gross_profit']
                               for day in daily_data)
            total_orders = sum(day['summary']['order_count']
                               for day in daily_data)

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

        elif date_str:
            # Single date
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            profit_data = ProfitCalculator.calculate_daily_profit(date)

            return Response({
                'success': True,
                'date': date_str,
                **profit_data
            })

        else:
            # Today
            profit_data = ProfitCalculator.calculate_daily_profit()
            return Response({
                'success': True,
                'date': timezone.now().date().isoformat(),
                **profit_data
            })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def profit_issues(request):
    """
    Identify profit issues and get suggestions
    """
    try:
        issues = ProfitCalculator.identify_profit_issues()
        return Response({
            'success': True,
            **issues
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def waste_analysis_detailed(request):
    """
    Get detailed waste analysis
    """
    try:
        days = int(request.query_params.get('days', 30))
        waste_data = WasteAnalyzer.analyze_waste_period(days)
        return Response({
            'success': True,
            **waste_data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def record_waste(request):
    """
    Record waste manually
    """
    try:
        from .models import StockItem, StockTransaction

        stock_item_id = request.data.get('stock_item_id')
        quantity = Decimal(request.data.get('quantity', 0))
        reason = request.data.get('reason', '')
        unit_cost = Decimal(request.data.get('unit_cost', 0))

        if not stock_item_id or quantity <= 0:
            return Response({
                'success': False,
                'error': 'Valid stock item ID and quantity required'
            }, status=status.HTTP_400_BAD_REQUEST)

        stock_item = StockItem.objects.get(id=stock_item_id)

        # Check if user has permission for this restaurant/branch
        if request.user.restaurant != stock_item.restaurant:
            return Response({
                'success': False,
                'error': 'Unauthorized access to this stock item'
            }, status=status.HTTP_403_FORBIDDEN)

        if request.user.branch and stock_item.branch != request.user.branch:
            return Response({
                'success': False,
                'error': 'Unauthorized access to this stock item'
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if sufficient stock
        if quantity > stock_item.current_quantity:
            return Response({
                'success': False,
                'error': f'Insufficient stock. Available: {stock_item.current_quantity}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use the actual cost if not provided
        if unit_cost <= 0:
            unit_cost = stock_item.cost_per_unit

        total_cost = quantity * unit_cost

        # Create waste transaction
        transaction = StockTransaction.objects.create(
            stock_item=stock_item,
            transaction_type='waste',
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            reason=reason,
            user=request.user,
            restaurant=stock_item.restaurant,
            branch=stock_item.branch
        )

        # Update stock quantity
        stock_item.current_quantity -= quantity
        stock_item.save()

        return Response({
            'success': True,
            'message': 'Waste recorded successfully',
            'transaction_id': transaction.id,
            'stock_item': stock_item.name,
            'quantity': float(quantity),
            'total_cost': float(total_cost),
            'new_stock_level': float(stock_item.current_quantity)
        })

    except StockItem.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Stock item not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
