# tables/urls.py - API ENDPOINTS ONLY
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for API views
router = DefaultRouter()
router.register(r'tables', views.TableViewSet, basename='table')
router.register(r'orders', views.OrderViewSet, basename='order')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Cart endpoints
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.add_to_cart, name='add-to-cart'),
    path('cart/item/<int:cart_item_id>/',
         views.update_cart_item, name='update-cart-item'),

    # QR validation
    path('validate-qr/', views.validate_qr_token, name='validate-qr'),
    path('submit-qr-order/', views.submit_qr_order, name='submit-qr-order'),

    # Additional order endpoints
    path('orders/pending_confirmation/', views.OrderViewSet.as_view(
        {'get': 'pending_confirmation'}), name='orders-pending-confirmation'),
    path('orders/kitchen_orders/',
         views.OrderViewSet.as_view({'get': 'kitchen_orders'}), name='kitchen-orders'),
    path('orders/by_table/<int:table_id>/',
         views.OrderViewSet.as_view({'get': 'by_table'}), name='orders-by-table'),
]

# REMOVE ALL TEMPLATE VIEWS FROM THIS FILE!
# Template views are now in main urls.py at root level
