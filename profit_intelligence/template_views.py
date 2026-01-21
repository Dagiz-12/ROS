# profit_intelligence/template_views.py
from django.shortcuts import render
import json
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from accounts.decorators import role_required


@login_required
@role_required(['manager', 'admin'])
def profit_dashboard_view(request):
    """
    Main profit dashboard template view
    """
    user = request.user

    # Check if user has restaurant
    if not hasattr(user, 'restaurant') or not user.restaurant:
        return HttpResponseForbidden("You are not assigned to a restaurant.")

    # Get accessible branches for dropdown
    accessible_branches = []
    if user.role in ['admin', 'manager']:
        if user.manager_scope == 'restaurant':
            # Can see all branches in restaurant
            accessible_branches = user.restaurant.branches.filter(
                is_active=True)
        else:
            # Can only see assigned branches
            if user.branch:
                accessible_branches = [user.branch]

    # Serialize branches for safe insertion into JavaScript
    try:
        # Convert queryset or list of Branch objects into simple dicts
        branches_serializable = []
        for b in accessible_branches:
            try:
                branches_serializable.append({'id': b.id, 'name': str(b.name)})
            except Exception:
                continue
        accessible_branches_json = json.dumps(branches_serializable)
    except Exception:
        accessible_branches_json = '[]'

    return render(request, 'profit_intelligence/dashboard.html', {
        'user': user,
        'restaurant': user.restaurant,
        'user_role': user.role,
        'manager_scope': user.manager_scope if user.role == 'manager' else 'restaurant',
        'accessible_branches': accessible_branches,
        'accessible_branches_json': accessible_branches_json,
        'page_title': 'Profit Intelligence Dashboard',
        'page_subtitle': 'Advanced business intelligence and profit analytics'
    })


@login_required
@role_required(['manager', 'admin'])
def menu_item_analysis_view(request):
    """
    Detailed menu item profitability analysis
    """
    user = request.user

    return render(request, 'profit_intelligence/menu_analysis.html', {
        'user': user,
        'restaurant': user.restaurant,
        'page_title': 'Menu Item Analysis',
        'page_subtitle': 'Detailed profitability by menu item'
    })


@login_required
@role_required(['manager', 'admin'])
def profit_alerts_view(request):
    """
    Profit alerts dashboard
    """
    user = request.user

    return render(request, 'profit_intelligence/alerts.html', {
        'user': user,
        'restaurant': user.restaurant,
        'page_title': 'Profit Alerts',
        'page_subtitle': 'Monitor and resolve profit-related issues'
    })


@login_required
@role_required(['manager', 'admin'])
def price_optimization_view(request):
    """
    Price optimization suggestions
    """
    user = request.user

    return render(request, 'profit_intelligence/price_optimization.html', {
        'user': user,
        'restaurant': user.restaurant,
        'page_title': 'Price Optimization',
        'page_subtitle': 'AI-powered pricing suggestions'
    })


@login_required
@role_required(['manager', 'admin'])
def historical_analysis_view(request):
    """
    Historical profit analysis and trends
    """
    user = request.user

    return render(request, 'profit_intelligence/historical.html', {
        'user': user,
        'restaurant': user.restaurant,
        'page_title': 'Historical Analysis',
        'page_subtitle': 'Long-term profit trends and patterns'
    })
