# tables/urls_template.py
from django.urls import path
from . import views

urlpatterns = [
    # Staff Interface Templates
    path('waiter/dashboard/', views.waiter_dashboard, name='waiter-dashboard'),
    path('waiter/tables/', views.waiter_tables, name='waiter-tables'),
    path('waiter/orders/', views.waiter_orders, name='waiter-orders'),
    path('waiter/new-order/', views.waiter_new_order, name='waiter-new-order'),
    path('waiter/new-order/<int:table_id>/', views.waiter_new_order,
         name='waiter-new-order-with-table'),

    path('chef/dashboard/', views.chef_dashboard, name='chef-dashboard'),
    path('cashier/dashboard/', views.cashier_dashboard, name='cashier-dashboard'),

    # QR Menu Interface (public)
    path('qr-menu/<int:restaurant_id>/<int:table_id>/',
         views.qr_menu_view, name='qr-menu'),
    path('qr-menu/', views.qr_menu_view, name='qr-menu-default'),
]
