# waste_tracker/urls.py - CORRECTED VERSION
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import template_views

router = DefaultRouter()
router.register(r'categories', views.WasteCategoryViewSet,
                basename='waste-category')
router.register(r'reasons', views.WasteReasonViewSet, basename='waste-reason')
router.register(r'records', views.WasteRecordViewSet, basename='waste-record')
router.register(r'targets', views.WasteTargetViewSet, basename='waste-target')
router.register(r'alerts', views.WasteAlertViewSet, basename='waste-alert')

# API endpoints under /api/waste/
api_patterns = [
    path('', include(router.urls)),
    path('dashboard-data/', views.waste_dashboard, name='waste-dashboard-api'),
    path('analytics/detailed/', views.detailed_waste_analytics,
         name='detailed-waste-analytics'),
    path('analytics/reduction-potential/',
         views.waste_reduction_potential, name='waste-reduction-potential'),
    path('analytics/forecast/', views.waste_forecast, name='waste-forecast'),
    path('quick-entry/', views.quick_waste_entry, name='quick-waste-entry'),
    path('alerts/run-checks/', views.run_waste_alerts, name='run-waste-alerts'),
    path('health/',
         lambda request: {'status': 'waste_tracker_ok'}, name='waste-health'),
]

# Template views
template_patterns = [
    path('entry/', template_views.employee_waste_entry,
         name='employee-waste-entry'),
    path('my-records/', template_views.my_waste_records, name='my-waste-records'),
    path('dashboard/', template_views.waste_dashboard, name='waste-dashboard'),
    path('reports/', template_views.waste_reports, name='waste-reports'),
    path('alerts/', template_views.waste_alerts, name='waste-alerts'),
    path('targets/', template_views.waste_targets, name='waste-targets'),
]

# Main URL configuration
urlpatterns = [
    path('api/', include(api_patterns)),
    path('', include(template_patterns)),
]
