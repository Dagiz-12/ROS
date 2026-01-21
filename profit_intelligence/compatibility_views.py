# profit_intelligence/compatibility_views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .api_views import ProfitDashboardAPIView


@csrf_exempt
def compatibility_profit_dashboard(request):
    """Handle old /api/inventory/profit/dashboard/ calls

    Return a plain JsonResponse so legacy callers receive standard JSON.
    """
    view = ProfitDashboardAPIView()
    view.request = request
    response = view.get(request)
    # DRF Response has .data and .status_code
    return JsonResponse(response.data, status=getattr(response, 'status_code', 200), safe=False)
