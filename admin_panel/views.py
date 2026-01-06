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
from menu.business_logic import MenuBusinessLogic
from decimal import Decimal


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


from accounts.permissions import IsManagerOrAdmin  # Use your existing permissions
from rest_framework.response import Response
from rest_framework import status


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
        'days_of_week': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
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


# Business Intelligence Features


@login_required
def api_business_metrics(request):
    """API endpoint for business metrics including profit"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return JsonResponse({'error': 'No restaurant found'}, status=404)

    period = request.GET.get('period', 'today')
    today = timezone.now().date()

    # Calculate date ranges based on period
    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == 'month':
        start_date = today.replace(day=1)
        end_date = today

    # Get orders for period
    orders = Order.objects.filter(
        table__branch__restaurant=restaurant,
        placed_at__date__gte=start_date,
        placed_at__date__lte=end_date,
        status='completed'
    )

    # Calculate metrics
    total_orders = orders.count()
    total_revenue = orders.aggregate(Sum('total_amount'))[
        'total_amount__sum'] or 0

    # Calculate profit (this requires MenuItem cost_price field)
    total_cost = 0
    total_profit = 0

    for order in orders:
        for order_item in order.items.all():
            menu_item = order_item.menu_item
            if hasattr(menu_item, 'cost_price') and menu_item.cost_price:
                total_cost += menu_item.cost_price * order_item.quantity
            else:
                # Estimate cost at 40% of price if cost_price not set
                total_cost += (order_item.unit_price *
                               Decimal('0.4')) * order_item.quantity

    total_profit = total_revenue - total_cost
    profit_margin = (total_profit / total_revenue *
                     100) if total_revenue > 0 else 0

    # Get best seller
    from django.db.models import Count
    best_seller = MenuItem.objects.filter(
        category__restaurant=restaurant,
        orderitem__order__in=orders
    ).annotate(
        sold_count=Count('orderitem')
    ).order_by('-sold_count').first()

    # Get comparison data (vs previous period)
    if period == 'today':
        prev_start = today - timedelta(days=1)
        prev_end = today - timedelta(days=1)
    elif period == 'week':
        prev_start = start_date - timedelta(days=7)
        prev_end = start_date - timedelta(days=1)
    elif period == 'month':
        prev_month = today.replace(day=1) - timedelta(days=1)
        prev_start = prev_month.replace(day=1)
        prev_end = prev_month

    prev_orders = Order.objects.filter(
        table__branch__restaurant=restaurant,
        placed_at__date__gte=prev_start,
        placed_at__date__lte=prev_end,
        status='completed'
    )

    prev_revenue = prev_orders.aggregate(Sum('total_amount'))[
        'total_amount__sum'] or 0
    revenue_change = ((total_revenue - prev_revenue) /
                      prev_revenue * 100) if prev_revenue > 0 else 0

    prev_orders_count = prev_orders.count()
    orders_change = ((total_orders - prev_orders_count) /
                     prev_orders_count * 100) if prev_orders_count > 0 else 0

    return JsonResponse({
        'success': True,
        'metrics': {
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'revenue_change': float(revenue_change),
            'orders_change': float(orders_change),
            'average_order_value': float(total_revenue / total_orders) if total_orders > 0 else 0,
            'active_staff': CustomUser.objects.filter(restaurant=restaurant, is_active=True).exclude(role='admin').count(),
            'active_branches': Branch.objects.filter(restaurant=restaurant, is_active=True).count(),
        },
        'profit': {
            'total_profit': float(total_profit),
            'total_cost': float(total_cost),
            'profit_margin': float(profit_margin),
            'best_seller': {
                'name': best_seller.name if best_seller else 'No sales',
                'sold': best_seller.sold_count if best_seller else 0,
                'revenue': float(best_seller.sold_count * best_seller.price) if best_seller else 0,
                'image': best_seller.image.url if best_seller and best_seller.image else None
            } if best_seller else None
        },
        'period': period,
        'date_range': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        }
    })


@login_required
def api_profit_table(request):
    """API endpoint for profitability table"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return JsonResponse({'error': 'No restaurant found'}, status=404)

    period = request.GET.get('period', 'week')
    today = timezone.now().date()

    # Calculate date range
    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == 'month':
        start_date = today.replace(day=1)
        end_date = today

    # Get orders for period
    orders = Order.objects.filter(
        table__branch__restaurant=restaurant,
        placed_at__date__gte=start_date,
        placed_at__date__lte=end_date,
        status='completed'
    )

    # Get menu items with sales data
    from django.db.models import Sum, F

    items = MenuItem.objects.filter(
        category__restaurant=restaurant,
        orderitem__order__in=orders
    ).annotate(
        sold=Sum('orderitem__quantity'),
        revenue=Sum(F('orderitem__unit_price') * F('orderitem__quantity'))
    ).filter(sold__gt=0).order_by('-revenue')

    # Calculate profit for each item
    profit_items = []
    for item in items:
        # Calculate cost
        if hasattr(item, 'cost_price') and item.cost_price:
            cost = item.cost_price * item.sold
        else:
            cost = (item.price * Decimal('0.4')) * item.sold  # Estimate

        profit = item.revenue - cost
        margin = (profit / item.revenue * 100) if item.revenue > 0 else 0

        profit_items.append({
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else '',
            'image': item.image.url if item.image else None,
            'sold': item.sold,
            'revenue': float(item.revenue),
            'cost': float(cost),
            'profit': float(profit),
            'margin': float(margin)
        })

    return JsonResponse({
        'success': True,
        'items': profit_items,
        'period': period,
        'total_items': len(profit_items)
    })


# Menu Management API Endpoints

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def api_menu_categories(request):
    """API endpoint for menu categories CRUD"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return Response({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return Response({'error': 'No restaurant found'}, status=404)

    if request.method == 'GET':
        categories = Category.objects.filter(
            restaurant=restaurant).order_by('order_index')
        data = [{
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'order_index': cat.order_index,
            'is_active': cat.is_active,
            'items_count': cat.items.count()
        } for cat in categories]
        return Response({'success': True, 'categories': data})

    elif request.method == 'POST':
        try:
            category = Category.objects.create(
                restaurant=restaurant,
                name=request.data['name'],
                description=request.data.get('description', ''),
                order_index=request.data.get('order_index', 0),
                is_active=request.data.get('is_active', True)
            )
            return Response({
                'success': True,
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'order_index': category.order_index,
                    'is_active': category.is_active,
                    'items_count': 0
                }
            })
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def api_menu_category_detail(request, category_id):
    """API endpoint for individual category CRUD"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return Response({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return Response({'error': 'No restaurant found'}, status=404)

    try:
        category = Category.objects.get(id=category_id, restaurant=restaurant)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status=404)

    if request.method == 'GET':
        data = {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'order_index': category.order_index,
            'is_active': category.is_active,
            'items_count': category.items.count()
        }
        return Response({'success': True, 'category': data})

    elif request.method == 'PUT':
        try:
            category.name = request.data['name']
            category.description = request.data.get('description', '')
            category.order_index = request.data.get('order_index', 0)
            category.is_active = request.data.get('is_active', True)
            category.save()
            return Response({
                'success': True,
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'order_index': category.order_index,
                    'is_active': category.is_active,
                    'items_count': category.items.count()
                }
            })
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)

    elif request.method == 'DELETE':
        category.delete()
        return Response({'success': True})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def api_menu_items(request):
    """API endpoint for menu items CRUD"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return Response({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return Response({'error': 'No restaurant found'}, status=404)

    if request.method == 'GET':
        items = MenuItem.objects.filter(
            category__restaurant=restaurant).select_related('category')
        data = [{
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'price': float(item.price),
            'cost_price': float(item.cost_price) if item.cost_price else 0,
            'profit_margin': float(item.profit_margin) if item.profit_margin else 0,
            'sold_count': item.sold_count,
            'preparation_time': item.preparation_time,
            'is_available': item.is_available,
            'image': item.image.url if item.image else None,
            'category': item.category.id,
            'category_name': item.category.name
        } for item in items]
        return Response({'success': True, 'items': data})

    elif request.method == 'POST':
        try:
            category_id = request.data.get('category')
            if not category_id:
                raise ValueError("Category is required")

            price_str = request.data.get('price')
            if not price_str:
                raise ValueError("Price is required")

            cost_price_str = request.data.get('cost_price', '0')
            cost_price = Decimal(
                cost_price_str) if cost_price_str else Decimal('0')

            prep_time_str = request.data.get('preparation_time', '0')
            prep_time = int(prep_time_str) if prep_time_str else 0

            item = MenuItem.objects.create(
                category_id=int(category_id),
                name=request.data.get('name'),
                description=request.data.get('description', ''),
                price=Decimal(price_str),
                cost_price=cost_price,
                preparation_time=prep_time,
                is_available=request.data.get('is_available') == 'true',
                image=request.FILES.get(
                    'image') if 'image' in request.FILES else None
            )
            return Response({
                'success': True,
                'item': {
                    'id': item.id,
                    'name': item.name,
                    'description': item.description,
                    'price': float(item.price),
                    'cost_price': float(item.cost_price) if item.cost_price else 0,
                    'profit_margin': float(item.profit_margin) if item.profit_margin else 0,
                    'sold_count': item.sold_count,
                    'preparation_time': item.preparation_time,
                    'is_available': item.is_available,
                    'image': item.image.url if item.image else None,
                    'category': item.category.id,
                    'category_name': item.category.name
                }
            })
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def api_menu_item_detail(request, item_id):
    """API endpoint for individual menu item CRUD"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return Response({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return Response({'error': 'No restaurant found'}, status=404)

    try:
        item = MenuItem.objects.get(
            id=item_id, category__restaurant=restaurant)
    except MenuItem.DoesNotExist:
        return Response({'error': 'Item not found'}, status=404)

    if request.method == 'GET':
        data = {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'price': float(item.price),
            'cost_price': float(item.cost_price) if item.cost_price else 0,
            'profit_margin': float(item.profit_margin) if item.profit_margin else 0,
            'sold_count': item.sold_count,
            'preparation_time': item.preparation_time,
            'is_available': item.is_available,
            'image': item.image.url if item.image else None,
            'category': item.category.id,
            'category_name': item.category.name
        }
        return Response({'success': True, 'item': data})

    elif request.method == 'PUT':
        try:
            category_id = request.data.get('category', item.category_id)
            if not category_id:
                raise ValueError("Category is required")

            price_str = request.data.get('price', item.price)
            if not price_str:
                raise ValueError("Price is required")

            cost_price_str = request.data.get(
                'cost_price', item.cost_price or '0')
            cost_price = Decimal(
                cost_price_str) if cost_price_str else Decimal('0')

            prep_time_str = request.data.get(
                'preparation_time', item.preparation_time)
            prep_time = int(prep_time_str) if prep_time_str else 0

            item.category_id = int(category_id)
            item.name = request.data.get('name', item.name)
            item.description = request.data.get('description', '')
            item.price = Decimal(price_str)
            item.cost_price = cost_price
            item.preparation_time = prep_time
            item.is_available = request.data.get('is_available') == 'true'
            if 'image' in request.FILES:
                item.image = request.FILES['image']
            item.save()
            return Response({
                'success': True,
                'item': {
                    'id': item.id,
                    'name': item.name,
                    'description': item.description,
                    'price': float(item.price),
                    'cost_price': float(item.cost_price) if item.cost_price else 0,
                    'profit_margin': float(item.profit_margin) if item.profit_margin else 0,
                    'sold_count': item.sold_count,
                    'preparation_time': item.preparation_time,
                    'is_available': item.is_available,
                    'image': item.image.url if item.image else None,
                    'category': item.category.id,
                    'category_name': item.category.name
                }
            })
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)

    elif request.method == 'DELETE':
        item.delete()
        return Response({'success': True})


@login_required
def api_menu_export(request):
    """Export menu data as JSON"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return JsonResponse({'error': 'No restaurant found'}, status=404)

    categories = Category.objects.filter(
        restaurant=restaurant).order_by('order_index')
    data = {
        'restaurant': restaurant.name,
        'exported_at': timezone.now().isoformat(),
        'categories': []
    }

    for category in categories:
        cat_data = {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'order_index': category.order_index,
            'is_active': category.is_active,
            'items': []
        }

        items = MenuItem.objects.filter(category=category)
        for item in items:
            item_data = {
                'id': item.id,
                'name': item.name,
                'description': item.description,
                'price': float(item.price),
                'cost_price': float(item.cost_price) if item.cost_price else 0,
                'preparation_time': item.preparation_time,
                'is_available': item.is_available,
                'image': item.image.url if item.image else None
            }
            cat_data['items'].append(item_data)

        data['categories'].append(cat_data)

    response = JsonResponse(data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="{restaurant.name}_menu_export.json"'
    return response


@login_required
def api_menu_import(request):
    """Import menu data from JSON"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return JsonResponse({'error': 'No restaurant found'}, status=404)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        imported_count = 0

        for cat_data in data.get('categories', []):
            category, created = Category.objects.get_or_create(
                restaurant=restaurant,
                name=cat_data['name'],
                defaults={
                    'description': cat_data.get('description', ''),
                    'order_index': cat_data.get('order_index', 0),
                    'is_active': cat_data.get('is_active', True)
                }
            )

            for item_data in cat_data.get('items', []):
                MenuItem.objects.get_or_create(
                    category=category,
                    name=item_data['name'],
                    defaults={
                        'description': item_data.get('description', ''),
                        'price': item_data['price'],
                        'cost_price': item_data.get('cost_price', 0),
                        'preparation_time': item_data.get('preparation_time', 0),
                        'is_available': item_data.get('is_available', True)
                    }
                )
                imported_count += 1

        return JsonResponse({
            'success': True,
            'message': f'Successfully imported {imported_count} items'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# Add to your admin_panel/views.py

@login_required
def api_menu_bulk_update(request):
    """Bulk update menu items"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    restaurant = user.restaurant
    if not restaurant:
        return JsonResponse({'error': 'No restaurant found'}, status=404)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            item_ids = data.get('item_ids', [])
            percentage = data.get('percentage', 0)

            items = MenuItem.objects.filter(
                id__in=item_ids,
                category__restaurant=restaurant
            )

            if action == 'adjust_prices':
                for item in items:
                    adjustment = 1 + (percentage / 100)
                    item.price = item.price * Decimal(str(adjustment))
                    item.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Updated prices for {items.count()} items'
                })

            elif action == 'toggle_availability':
                new_status = data.get('status', True)
                items.update(is_available=new_status)

                return JsonResponse({
                    'success': True,
                    'message': f'Updated availability for {items.count()} items'
                })

            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)
