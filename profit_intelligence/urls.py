# profit_intelligence/urls.py
from django.urls import path, include
from . import template_views, api_views

app_name = 'profit_intelligence'

# Template Views (HTML)
urlpatterns = [
    path('dashboard/', template_views.profit_dashboard_view, name='dashboard'),
    path('menu-analysis/', template_views.menu_item_analysis_view,
         name='menu-analysis'),
    path('alerts/', template_views.profit_alerts_view, name='alerts'),
    path('price-optimization/', template_views.price_optimization_view,
         name='price-optimization'),
    path('historical/', template_views.historical_analysis_view, name='historical'),
]

# API Views (JSON) - Direct paths without extra namespace
urlpatterns += [
    # Dashboard API
    path('api/dashboard/', api_views.ProfitDashboardAPIView.as_view(),
         name='api-dashboard'),
    path('api/daily/', api_views.DailyProfitAPIView.as_view(), name='api-daily'),
    path('api/menu-items/', api_views.MenuItemProfitAPIView.as_view(),
         name='api-menu-items'),
    path('api/alerts/', api_views.ProfitAlertsAPIView.as_view(), name='api-alerts'),
    path('api/issues/', api_views.ProfitIssuesAPIView.as_view(), name='api-issues'),

    # ======== ADD THESE MISSING ENDPOINTS ========
    path('api/profit-table/', api_views.ProfitTableAPIView.as_view(),
         name='api-profit-table'),
    path('api/business-metrics/', api_views.BusinessMetricsAPIView.as_view(),
         name='api-business-metrics'),
    path('api/sales-data/', api_views.SalesDataAPIView.as_view(),
         name='api-sales-data'),
    path('api/popular-items/', api_views.PopularItemsAPIView.as_view(),
         name='api-popular-items'),
    path('api/recent-activity/', api_views.RecentActivityAPIView.as_view(),
         name='api-recent-activity'),
]
