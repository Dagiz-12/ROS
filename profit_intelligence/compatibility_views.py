# profit_intelligence/compatibility_views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .api_views import ProfitDashboardAPIView


@csrf_exempt
def compatibility_profit_dashboard(request):
    """Handle old /api/inventory/profit/dashboard/ calls"""
    view = ProfitDashboardAPIView()
    view.request = request
    return view.get(request)
