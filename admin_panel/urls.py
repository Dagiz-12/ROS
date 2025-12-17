from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.admin_dashboard, name='admin-dashboard'),

    # Management Pages
    path('restaurant/', views.admin_restaurant_management, name='admin-restaurant'),
    path('menu/', views.admin_menu_management, name='admin-menu'),
    path('staff/', views.admin_staff_management, name='admin-staff'),
    path('tables/', views.admin_table_management, name='admin-tables'),

    # Analytics & Reports
    path('analytics/', views.admin_analytics, name='admin-analytics'),
    path('reports/', views.admin_reports, name='admin-reports'),

    # API Endpoints
    path('api/sales-data/', views.api_sales_data, name='admin-api-sales-data'),
    path('api/order-analytics/', views.api_order_analytics,
         name='admin-api-order-analytics'),
]
