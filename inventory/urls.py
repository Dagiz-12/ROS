# inventory/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
# REMOVE: from . import profit_views  # <-- DELETE THIS LINE

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

    # REMOVE ALL PROFIT ENDPOINTS:
    # path('profit/dashboard/', profit_views.profit_dashboard, ...), <-- DELETE
    # path('profit/menu-items/', profit_views.menu_item_profitability, ...), <-- DELETE
    # ... etc

    # Keep only waste endpoints if they're truly waste-specific
    # But consider moving to waste_tracker app
]
