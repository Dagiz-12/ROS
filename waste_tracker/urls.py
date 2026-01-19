# waste_tracker/urls.py
from django.urls import path, include
from . import views, template_views
from .views import (
    WasteCategoryViewSet, WasteReasonViewSet, WasteRecordViewSet,
    WasteTargetViewSet, WasteAlertViewSet,
    waste_dashboard, detailed_waste_analytics, waste_reduction_potential,
    waste_forecast, quick_waste_entry, run_waste_alerts
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'categories', WasteCategoryViewSet, basename='waste-category')
router.register(r'reasons', WasteReasonViewSet, basename='waste-reason')
router.register(r'records', WasteRecordViewSet, basename='waste-record')
router.register(r'targets', WasteTargetViewSet, basename='waste-target')
router.register(r'alerts', WasteAlertViewSet, basename='waste-alert')

# API endpoints
api_patterns = [
    # Dashboard data
    path('dashboard/', waste_dashboard, name='waste-dashboard-api'),

    # Analytics
    path('detailed-analytics/', detailed_waste_analytics,
         name='waste-analytics-detailed'),
    path('reduction-potential/', waste_reduction_potential,
         name='waste-reduction-potential'),
    path('forecast/', waste_forecast, name='waste-forecast'),

    # Quick entry
    path('quick-entry/', quick_waste_entry, name='waste-quick-entry'),

    # Alert management
    path('alerts/run-checks/', run_waste_alerts, name='waste-alert-checks'),

    # Include router URLs
    path('', include(router.urls)),
]

# Template views (HTML pages)
template_patterns = [
    path('entry/', template_views.employee_waste_entry, name='waste-entry'),
    path('dashboard/', template_views.waste_dashboard, name='waste-dashboard'),
    path('reports/', template_views.waste_reports, name='waste-reports'),
    path('alerts/', template_views.waste_alerts, name='waste-alerts'),
    path('targets/', template_views.waste_targets, name='waste-targets'),
    path('my-records/', template_views.my_waste_records, name='my-waste-records'),
]

# Main URL patterns
urlpatterns = [
    # API endpoints under /api/waste/
    path('api/', include(api_patterns)),

    # Template views under /waste/
    path('', include(template_patterns)),
]
