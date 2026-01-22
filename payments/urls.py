# payments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'payments', views.PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),

    # Industry standard endpoints
    path('cashier/dashboard/', views.PaymentViewSet.as_view(
        {'get': 'cashier_dashboard'}), name='cashier-dashboard'),
    path('cashier/pending-orders/',
         views.PaymentViewSet.as_view({'get': 'pending_orders'}), name='pending-orders'),
    path('cashier/print-receipt/<uuid:payment_id>/',
         views.print_receipt, name='print-receipt'),

    # Quick payment processing
    path('payments/<uuid:pk>/quick-pay/', views.PaymentViewSet.as_view(
        {'post': 'process_quick_payment'}), name='quick-payment'),
    path('payments/<uuid:pk>/detailed-receipt/', views.PaymentViewSet.as_view(
        {'post': 'generate_detailed_receipt'}), name='detailed-receipt'),
]
