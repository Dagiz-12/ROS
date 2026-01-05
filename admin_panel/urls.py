from django.urls import path
from . import views

urlpatterns = [
    # Template views
    path('dashboard/', views.admin_dashboard, name='admin-dashboard'),
    path('restaurant/', views.admin_restaurant_management, name='admin-restaurant'),
    path('menu/', views.admin_menu_management, name='admin-menu'),
    path('staff/', views.admin_staff_management, name='admin-staff'),
    path('analytics/', views.admin_analytics, name='admin-analytics'),
    path('tables/', views.admin_table_management, name='admin-tables'),
    path('reports/', views.admin_reports, name='admin-reports'),

    # API endpoints
    path('api/sales-data/', views.api_sales_data, name='api-sales-data'),
    path('api/order-analytics/', views.api_order_analytics,
         name='api-order-analytics'),
    path('api/business-metrics/', views.api_business_metrics,
         name='api-business-metrics'),
    path('api/profit-table/', views.api_profit_table, name='api-profit-table'),

    # Menu API endpoints
    path('api/menu/categories/', views.api_menu_categories,
         name='api-menu-categories'),
    path('api/menu/categories/<int:category_id>/',
         views.api_menu_category_detail, name='api-menu-category-detail'),
    path('api/menu/items/', views.api_menu_items, name='api-menu-items'),
    path('api/menu/items/<int:item_id>/',
         views.api_menu_item_detail, name='api-menu-item-detail'),
    path('api/menu/export/', views.api_menu_export, name='api-menu-export'),
    path('api/menu/import/', views.api_menu_import, name='api-menu-import'),
    path('api/menu/bulk-update/', views.api_menu_bulk_update,
         name='api-menu-bulk-update'),
]
