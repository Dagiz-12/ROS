# accounts/staff_analytics_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Avg, Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser
from tables.models import Order


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_performance_dashboard(request):
    """
    Get staff performance dashboard data
    """
    user = request.user
    period = request.GET.get('period', 'today')
    role_filter = request.GET.get('role', 'all')

    # Get accessible branches
    branches = user.get_accessible_branches()

    # Date range
    now = timezone.now()
    if period == 'today':
        start_date = now.date()
        end_date = now.date()
    elif period == 'week':
        start_date = now.date() - timedelta(days=7)
        end_date = now.date()
    elif period == 'month':
        start_date = now.date() - timedelta(days=30)
        end_date = now.date()
    else:
        start_date = now.date() - timedelta(days=7)
        end_date = now.date()

    # Get staff performance metrics
    staff_data = []

    # Filter by role if specified
    roles = ['waiter', 'chef', 'cashier']
    if role_filter != 'all':
        roles = [role_filter]

    for staff in CustomUser.objects.filter(
        restaurant=user.restaurant,
        is_active=True,
        role__in=roles
    ):
        # Get orders for this period
        orders = Order.objects.filter(
            Q(waiter=staff) | Q(chef=staff),
            placed_at__date__gte=start_date,
            placed_at__date__lte=end_date,
            status='completed'
        )

        staff_info = {
            'id': staff.id,
            'username': staff.username,
            'full_name': staff.get_full_name(),
            'role': staff.role,
            'performance_score': staff.performance_score,
            'rating': float(staff.rating),
            'orders_handled': staff.orders_handled,
            'sales_value': float(staff.sales_value),
            'orders_prepared': staff.orders_prepared,
            'avg_prep_time': staff.avg_prep_time,
            'period_stats': {
                'orders': orders.count(),
                'revenue': float(orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
            },
            'current_shift': staff.current_shift,
            'is_active': staff.is_active
        }
        staff_data.append(staff_info)

    # Sort by performance score
    staff_data.sort(key=lambda x: x['performance_score'], reverse=True)

    # Get top performers
    top_performers = staff_data[:5]

    return Response({
        'success': True,
        'staff': staff_data,
        'top_performers': top_performers,
        'period': period,
        'role_filter': role_filter,
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        },
        'summary': {
            'total_staff': len(staff_data),
            'waiters': len([s for s in staff_data if s['role'] == 'waiter']),
            'chefs': len([s for s in staff_data if s['role'] == 'chef']),
            'cashiers': len([s for s in staff_data if s['role'] == 'cashier']),
            'avg_performance': sum(s['performance_score'] for s in staff_data) / len(staff_data) if staff_data else 0
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_performance_detail(request, staff_id):
    """
    Get detailed performance data for a specific staff member
    """
    try:
        staff = CustomUser.objects.get(
            id=staff_id, restaurant=request.user.restaurant)
    except CustomUser.DoesNotExist:
        return Response({'success': False, 'error': 'Staff not found'}, status=404)

    # Get performance history
    history = staff.performance_history or []

    # Get recent orders
    recent_orders = Order.objects.filter(
        Q(waiter=staff) | Q(chef=staff),
        status='completed'
    ).order_by('-placed_at')[:10]

    orders_data = [{
        'order_number': order.order_number,
        'table': order.table.table_number if order.table else None,
        'total_amount': float(order.total_amount),
        'placed_at': order.placed_at.isoformat(),
        'status': order.status
    } for order in recent_orders]

    return Response({
        'success': True,
        'staff': {
            'id': staff.id,
            'username': staff.username,
            'full_name': staff.get_full_name(),
            'role': staff.role,
            'performance_score': staff.performance_score,
            'rating': float(staff.rating),
            'orders_handled': staff.orders_handled,
            'sales_value': float(staff.sales_value),
            'orders_prepared': staff.orders_prepared,
            'avg_prep_time': staff.avg_prep_time,
            'history': history[-30:],  # Last 30 entries
            'recent_orders': orders_data,
            'current_shift': staff.current_shift,
            'is_active': staff.is_active
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_leaderboard(request):
    """
    Get staff leaderboard by performance
    """
    role = request.GET.get('role', 'all')
    limit = int(request.GET.get('limit', 10))

    # Filter by role
    staff_query = CustomUser.objects.filter(
        restaurant=request.user.restaurant,
        is_active=True
    )

    if role != 'all':
        staff_query = staff_query.filter(role=role)

    # Exclude admins and managers from leaderboard
    staff_query = staff_query.exclude(role__in=['admin', 'manager'])

    # Order by performance score
    staff_query = staff_query.order_by('-performance_score')[:limit]

    data = [{
        'id': staff.id,
        'username': staff.username,
        'full_name': staff.get_full_name(),
        'role': staff.role,
        'performance_score': staff.performance_score,
        'orders_handled': staff.orders_handled,
        'sales_value': float(staff.sales_value),
        'rating': float(staff.rating)
    } for staff in staff_query]

    return Response({
        'success': True,
        'leaderboard': data,
        'role': role,
        'limit': limit
    })
