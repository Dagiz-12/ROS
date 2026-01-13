# waste_tracker/template_views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.decorators import role_required
from .business_logic import EnhancedWasteAnalyzer, WasteAlertManager


@login_required
@role_required(['chef', 'waiter', 'kitchen_staff', 'manager', 'admin'])
def employee_waste_entry(request):
    """
    Employee interface for recording waste
    """
    context = {
        'user': request.user,
        'restaurant': request.user.restaurant,
        'branch': request.user.branch,
        'page_title': 'Record Waste',
        'page_subtitle': 'Kitchen waste recording system'
    }
    return render(request, 'waste_tracker/employee_waste_entry.html', context)


@login_required
@role_required(['manager', 'admin'])
def waste_dashboard(request):
    """
    Manager dashboard for waste analytics
    """
    # Get basic stats
    try:
        analyzer = EnhancedWasteAnalyzer()
        period = request.GET.get('period', '30')
        branch_id = request.GET.get('branch_id')

        if branch_id and request.user.role == 'manager':
            # Managers can only view their branch
            if request.user.branch and str(request.user.branch.id) != branch_id:
                messages.error(request, 'Unauthorized access to this branch')
                return redirect('waste-dashboard')

        analytics = analyzer.analyze_detailed_waste_period(
            days=int(period),
            branch_id=branch_id
        )

        # Get reduction potential
        reduction_potential = analyzer.calculate_waste_reduction_potential(
            branch_id=branch_id
        )

        # Get recurring issues
        recurring_issues = analyzer.detect_recurring_issues(
            days=min(int(period), 7)
        )

    except Exception as e:
        analytics = {}
        reduction_potential = {}
        recurring_issues = {}
        messages.warning(request, f'Could not load analytics: {str(e)}')

    context = {
        'user': request.user,
        'restaurant': request.user.restaurant,
        'branch': request.user.branch,
        'page_title': 'Waste Analytics Dashboard',
        'page_subtitle': 'Monitor and reduce food waste',
        'analytics': analytics,
        'reduction_potential': reduction_potential,
        'recurring_issues': recurring_issues,
        'period': period,
        'branch_id': branch_id
    }
    return render(request, 'waste_tracker/waste_dashboard.html', context)


@login_required
@role_required(['manager', 'admin'])
def waste_reports(request):
    """
    Generate waste reports
    """
    context = {
        'user': request.user,
        'restaurant': request.user.restaurant,
        'branch': request.user.branch,
        'page_title': 'Waste Reports',
        'page_subtitle': 'Generate and download waste reports'
    }
    return render(request, 'waste_tracker/waste_reports.html', context)


@login_required
@role_required(['manager', 'admin'])
def waste_alerts(request):
    """
    View and manage waste alerts
    """
    context = {
        'user': request.user,
        'restaurant': request.user.restaurant,
        'branch': request.user.branch,
        'page_title': 'Waste Alerts',
        'page_subtitle': 'Monitor waste-related notifications'
    }
    return render(request, 'waste_tracker/waste_alerts.html', context)


@login_required
@role_required(['manager', 'admin'])
def waste_targets(request):
    """
    Manage waste reduction targets
    """
    context = {
        'user': request.user,
        'restaurant': request.user.restaurant,
        'branch': request.user.branch,
        'page_title': 'Waste Targets',
        'page_subtitle': 'Set and track waste reduction goals'
    }
    return render(request, 'waste_tracker/waste_targets.html', context)


@login_required
@role_required(['chef', 'waiter', 'kitchen_staff', 'manager', 'admin'])
def my_waste_records(request):
    """
    View personal waste records
    """
    context = {
        'user': request.user,
        'restaurant': request.user.restaurant,
        'branch': request.user.branch,
        'page_title': 'My Waste Records',
        'page_subtitle': 'View your waste recording history'
    }
    return render(request, 'waste_tracker/my_waste_records.html', context)
