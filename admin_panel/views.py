"""
Admin Panel Views for Restaurant Owners/Managers
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from datetime import datetime, timedelta
import json

from restaurants.models import Restaurant, Branch
from tables.models import Order, Table
from menu.models import MenuItem, Category
from accounts.models import CustomUser


@login_required
def admin_dashboard(request):
    """Main admin dashboard for restaurant owners"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return redirect('waiter-dashboard')

    # Get user's restaurant
    restaurant = None
    if user.restaurant:
        restaurant = user.restaurant
    elif user.role == 'admin':
        # Admin can see first restaurant or all
        restaurant = Restaurant.objects.first()

    context = {
        'user': user,
        'restaurant': restaurant,
        'user_role': user.role,
    }

    # If restaurant exists, add analytics
    if restaurant:
        # Today's date
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)

        # Today's orders
        today_orders = Order.objects.filter(
            table__branch__restaurant=restaurant,
            placed_at__date=today
        )

        # This week's orders
        week_orders = Order.objects.filter(
            table__branch__restaurant=restaurant,
            placed_at__date__gte=start_of_week
        )

        # This month's orders
        month_orders = Order.objects.filter(
            table__branch__restaurant=restaurant,
            placed_at__date__gte=start_of_month
        )

        # Calculate metrics
        today_revenue = today_orders.aggregate(Sum('total_amount'))[
            'total_amount__sum'] or 0
        week_revenue = week_orders.aggregate(Sum('total_amount'))[
            'total_amount__sum'] or 0
        month_revenue = month_orders.aggregate(Sum('total_amount'))[
            'total_amount__sum'] or 0

        # Active staff count
        active_staff = CustomUser.objects.filter(
            restaurant=restaurant,
            is_active=True
        ).exclude(role='admin').count()

        # Active branches
        active_branches = Branch.objects.filter(
            restaurant=restaurant, is_active=True).count()

        # Popular items
        popular_items = MenuItem.objects.filter(
            category__restaurant=restaurant,
            orderitem__order__in=today_orders
        ).annotate(
            order_count=Count('orderitem')
        ).order_by('-order_count')[:5]

        context.update({
            'today_orders_count': today_orders.count(),
            'today_revenue': today_revenue,
            'week_revenue': week_revenue,
            'month_revenue': month_revenue,
            'active_staff': active_staff,
            'active_branches': active_branches,
            'popular_items': popular_items,
            'today': today,
        })

    return render(request, 'admin_panel/dashboard.html', context)


@login_required
def admin_restaurant_management(request):
    """Restaurant settings and management"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return redirect('waiter-dashboard')

    restaurant = None
    if user.restaurant:
        restaurant = user.restaurant
    elif user.role == 'admin':
        restaurant = Restaurant.objects.first()

    branches = Branch.objects.filter(
        restaurant=restaurant) if restaurant else []

    context = {
        'user': user,
        'restaurant': restaurant,
        'branches': branches,
        'user_role': user.role,
    }

    return render(request, 'admin_panel/restaurant_management.html', context)


@login_required
def admin_menu_management(request):
    """Menu management interface"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return redirect('waiter-dashboard')

    restaurant = None
    if user.restaurant:
        restaurant = user.restaurant
    elif user.role == 'admin':
        restaurant = Restaurant.objects.first()

    categories = Category.objects.filter(
        restaurant=restaurant) if restaurant else []
    menu_items = MenuItem.objects.filter(
        category__restaurant=restaurant) if restaurant else []

    context = {
        'user': user,
        'restaurant': restaurant,
        'categories': categories,
        'menu_items': menu_items,
        'user_role': user.role,
    }

    return render(request, 'admin_panel/menu_management.html', context)


@login_required
def admin_staff_management(request):
    """Staff management interface"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return redirect('waiter-dashboard')

    restaurant = None
    if user.restaurant:
        restaurant = user.restaurant
    elif user.role == 'admin':
        restaurant = Restaurant.objects.first()

    staff_members = CustomUser.objects.filter(
        restaurant=restaurant) if restaurant else []

    # Group by role
    waiters = staff_members.filter(role='waiter')
    chefs = staff_members.filter(role='chef')
    cashiers = staff_members.filter(role='cashier')
    managers = staff_members.filter(role='manager')

    context = {
        'user': user,
        'restaurant': restaurant,
        'waiters': waiters,
        'chefs': chefs,
        'cashiers': cashiers,
        'managers': managers,
        'all_staff': staff_members,
        'user_role': user.role,
    }

    return render(request, 'admin_panel/staff_management.html', context)


@login_required
def admin_analytics(request):
    """Analytics and reporting interface"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return redirect('waiter-dashboard')

    restaurant = None
    if user.restaurant:
        restaurant = user.restaurant
    elif user.role == 'admin':
        restaurant = Restaurant.objects.first()

    # Date ranges
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)

    # Sales data
    daily_sales = []
    if restaurant:
        for i in range(7):
            date = today - timedelta(days=i)
            orders = Order.objects.filter(
                table__branch__restaurant=restaurant,
                placed_at__date=date
            )
            total = orders.aggregate(Sum('total_amount'))[
                'total_amount__sum'] or 0
            daily_sales.append({
                'date': date,
                'total': float(total),
                'orders': orders.count()
            })

    daily_sales.reverse()  # Oldest to newest

    context = {
        'user': user,
        'restaurant': restaurant,
        'daily_sales': daily_sales,
        'today': today,
        'last_week': last_week,
        'last_month': last_month,
        'user_role': user.role,
    }

    return render(request, 'admin_panel/analytics.html', context)


@login_required
def admin_table_management(request):
    """Table management interface"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return redirect('waiter-dashboard')

    restaurant = None
    if user.restaurant:
        restaurant = user.restaurant
    elif user.role == 'admin':
        restaurant = Restaurant.objects.first()

    branches = Branch.objects.filter(
        restaurant=restaurant) if restaurant else []
    tables = Table.objects.filter(
        branch__restaurant=restaurant) if restaurant else []

    # Group tables by branch
    tables_by_branch = {}
    for branch in branches:
        branch_tables = tables.filter(branch=branch)
        tables_by_branch[branch] = branch_tables

    context = {
        'user': user,
        'restaurant': restaurant,
        'branches': branches,
        'tables': tables,
        'tables_by_branch': tables_by_branch,
        'user_role': user.role,
    }

    return render(request, 'admin_panel/table_management.html', context)


@login_required
def admin_reports(request):
    """Reports generation interface"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return redirect('waiter-dashboard')

    restaurant = None
    if user.restaurant:
        restaurant = user.restaurant
    elif user.role == 'admin':
        restaurant = Restaurant.objects.first()

    context = {
        'user': user,
        'restaurant': restaurant,
        'user_role': user.role,
    }

    return render(request, 'admin_panel/reports.html', context)

# API endpoints for admin panel


@login_required
def api_sales_data(request):
    """API endpoint for sales chart data"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return JsonResponse({'error': 'No restaurant found'}, status=404)

    # Get date range from request
    days = int(request.GET.get('days', 7))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)

    # Get sales data
    sales_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        orders = Order.objects.filter(
            table__branch__restaurant=restaurant,
            placed_at__date=date
        )
        total = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        sales_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'total': float(total),
            'orders': orders.count(),
            'day_name': date.strftime('%a')
        })

    return JsonResponse({
        'success': True,
        'data': sales_data,
        'restaurant': restaurant.name,
        'period': f'{start_date} to {end_date}'
    })


@login_required
def api_order_analytics(request):
    """API endpoint for order analytics"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return JsonResponse({'error': 'No restaurant found'}, status=404)

    # Time periods
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    last_week_start = today - timedelta(days=7)

    # Get data
    today_orders = Order.objects.filter(
        table__branch__restaurant=restaurant,
        placed_at__date=today
    )

    yesterday_orders = Order.objects.filter(
        table__branch__restaurant=restaurant,
        placed_at__date=yesterday
    )

    week_orders = Order.objects.filter(
        table__branch__restaurant=restaurant,
        placed_at__date__gte=last_week_start
    )

    # Calculate metrics
    today_revenue = today_orders.aggregate(Sum('total_amount'))[
        'total_amount__sum'] or 0
    yesterday_revenue = yesterday_orders.aggregate(
        Sum('total_amount'))['total_amount__sum'] or 0
    week_revenue = week_orders.aggregate(Sum('total_amount'))[
        'total_amount__sum'] or 0

    # Revenue change
    revenue_change = 0
    if yesterday_revenue > 0:
        revenue_change = (
            (today_revenue - yesterday_revenue) / yesterday_revenue) * 100

    # Average order value
    today_avg = today_revenue / today_orders.count() if today_orders.count() > 0 else 0

    # Popular items
    popular_items = MenuItem.objects.filter(
        category__restaurant=restaurant,
        orderitem__order__in=today_orders
    ).annotate(
        order_count=Count('orderitem')
    ).order_by('-order_count')[:10]

    popular_items_data = [
        {
            'name': item.name,
            'count': item.order_count,
            'revenue': float(item.order_count * item.price)
        }
        for item in popular_items
    ]

    return JsonResponse({
        'success': True,
        'today': {
            'orders': today_orders.count(),
            'revenue': float(today_revenue),
            'average_order_value': float(today_avg)
        },
        'yesterday': {
            'revenue': float(yesterday_revenue)
        },
        'revenue_change': float(revenue_change),
        'week_revenue': float(week_revenue),
        'popular_items': popular_items_data
    })
