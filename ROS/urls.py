# ROS/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from core.views import landing_page, login_page
from tables.views import (
    qr_menu_view,
    waiter_dashboard, waiter_tables, waiter_orders, waiter_new_order,
    chef_dashboard, cashier_dashboard
)


urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # ============ PUBLIC PAGES ============
    path('', landing_page, name='landing'),
    path('login/', login_page, name='login'),
    path('logout/', TemplateView.as_view(template_name='auth/logout.html'), name='logout'),

    # ============ STAFF INTERFACES ============
    path('waiter/dashboard/', waiter_dashboard, name='waiter-dashboard'),
    path('waiter/tables/', waiter_tables, name='waiter-tables'),
    path('waiter/orders/', waiter_orders, name='waiter-orders'),
    path('waiter/new-order/', waiter_new_order, name='waiter-new-order'),
    path('chef/dashboard/', chef_dashboard, name='chef-dashboard'),
    path('cashier/dashboard/', cashier_dashboard, name='cashier-dashboard'),
    path('qr-menu/<int:restaurant_id>/<int:table_id>/',
         qr_menu_view, name='qr-menu'),

    # ============ ADMIN PANELS ============
    path('restaurant-admin/', include('admin_panel.urls')),

    # ============ PROFIT INTELLIGENCE ============
    path('profit-intelligence/', include('profit_intelligence.urls')),



    # Redirect old profit-dashboard to new profit intelligence
    # Redirect old admin panel endpoints to profit intelligence
    path('profit-intelligence/api/profit-table/', RedirectView.as_view(
        url='/profit-intelligence/api/profit-table/', permanent=True
    )),
    path('profit-intelligence/api/business-metrics/', RedirectView.as_view(
        url='/profit-intelligence/api/business-metrics/', permanent=True
    )),
    path('profit-intelligence/api/sales-data/', RedirectView.as_view(
        url='/profit-intelligence/api/sales-data/', permanent=True
    )),
    path('profit-intelligence/api/popular-items/', RedirectView.as_view(
        url='/profit-intelligence/api/popular-items/', permanent=True
    )),
    path('profit-intelligence/api/recent-activity/', RedirectView.as_view(
        url='/profit-intelligence/api/recent-activity/', permanent=True
    )),

    # ============ INVENTORY MANAGEMENT ============
    # ============ Waste MANAGEMENT ============
    path('waste/', include('waste_tracker.urls')),  # Template views only

    path('api/inventory/profit/dashboard/', RedirectView.as_view(
        url='/profit-intelligence/api/dashboard/', permanent=False
    )),
    path('api/inventory/profit/menu-items/', RedirectView.as_view(
        url='/profit-intelligence/api/menu-items/', permanent=False
    )),


    # ============ API ENDPOINTS ============
    path('api/auth/', include('accounts.urls')),
    path('api/restaurants/', include('restaurants.urls')),
    path('api/menu/', include('menu.urls')),
    path('api/tables/', include('tables.urls')),
    path('api/inventory/', include('inventory.urls')),  # Inventory API
    path('api/', include('core.urls')),
    path('api/waste/', include('waste_tracker.urls')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "Restaurant Ordering System Admin"
admin.site.site_title = "Restaurant Admin"
admin.site.index_title = "Welcome to Restaurant Ordering System"
