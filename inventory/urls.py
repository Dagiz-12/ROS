# inventory/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, profit_views
# REMOVE: from . import template_views

router = DefaultRouter()
router.register(r'stock-items', views.StockItemViewSet, basename='stock-item')
router.register(r'transactions', views.StockTransactionViewSet,
                basename='stock-transaction')
router.register(r'alerts', views.StockAlertViewSet, basename='stock-alert')
router.register(r'recipes', views.RecipeViewSet, basename='recipe')
router.register(r'reports', views.InventoryReportViewSet,
                basename='inventory-report')

urlpatterns = [
    # API endpoints only
    path('', include(router.urls)),

    # Inventory management endpoints
    path('low-stock/', views.low_stock_items, name='low-stock-items'),
    path('stock-value/', views.total_stock_value, name='total-stock-value'),
    path('waste-analysis/', views.waste_analysis, name='waste-analysis'),
    path('generate-report/', views.generate_report, name='generate-report'),
    path('auto-deduct-order/<int:order_id>/',
         views.auto_deduct_from_order, name='auto-deduct-order'),

    # Profit API endpoints
    path('profit/dashboard/', profit_views.profit_dashboard,
         name='profit-dashboard-api'),
    path('profit/menu-items/', profit_views.menu_item_profitability,
         name='menu-item-profitability'),
    path('profit/trend/', profit_views.profit_trend, name='profit-trend'),
    path('profit/daily/', profit_views.daily_profit, name='daily-profit'),
    path('profit/issues/', profit_views.profit_issues, name='profit-issues'),
    path('waste/detailed-analysis/', profit_views.waste_analysis_detailed,
         name='waste-analysis-detailed'),
    path('waste/record/', profit_views.record_waste, name='record-waste'),

    # REMOVED TEMPLATE VIEWS FROM HERE
    # They are now in the main urls.py
]
