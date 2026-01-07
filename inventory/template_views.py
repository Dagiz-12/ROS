from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from accounts.decorators import role_required


@login_required
def profit_dashboard_view(request):
    """Render the profit dashboard HTML template"""
    user = request.user

    if user.role not in ['admin', 'manager']:
        return HttpResponseForbidden("Permission denied")

    return render(request, 'profit/dashboard.html', {
        'user': request.user,
        'restaurant': request.user.restaurant if hasattr(request.user, 'restaurant') else None,
        'page_title': 'Profit Dashboard',
        'page_subtitle': 'Business intelligence and profit analytics'
    })


@role_required(['manager', 'admin'])
def menu_item_analysis_view(request):
    """Render detailed menu item analysis"""
    return render(request, 'profit/menu_analysis.html', {
        'user': request.user,
        'restaurant': request.user.restaurant if hasattr(request.user, 'restaurant') else None,
        'page_title': 'Menu Item Analysis',
        'page_subtitle': 'Detailed profitability analysis'
    })


@role_required(['manager', 'admin'])
def waste_analysis_view(request):
    """Render waste analysis dashboard"""
    return render(request, 'profit/waste_analysis.html', {
        'user': request.user,
        'restaurant': request.user.restaurant if hasattr(request.user, 'restaurant') else None,
        'page_title': 'Waste Analysis',
        'page_subtitle': 'Track and reduce food waste'
    })
