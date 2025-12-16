from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tables', views.TableViewSet, basename='table')
router.register(r'orders', views.OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),

    # Public endpoints (no auth required for customers)
    path('validate-qr/', views.validate_qr_token, name='validate-qr'),
    path('submit-qr-order/', views.submit_qr_order, name='submit-qr-order'),

    # Cart endpoints
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.add_to_cart, name='add-to-cart'),
    path('cart/item/<int:cart_item_id>/',
         views.update_cart_item, name='update-cart-item'),
]
